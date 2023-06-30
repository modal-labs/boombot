from pathlib import Path

from modal import Image, Stub, method, gpu, asgi_app
import io


stub = Stub("boombot")


def download_model():
    from audiocraft.models import MusicGen

    MusicGen.get_pretrained("large")


image = (
    Image.debian_slim()
    .apt_install("git", "ffmpeg")
    .pip_install(
        "pynacl",
        "torch",
        "soundfile",
        "pydub",
        "git+https://github.com/facebookresearch/audiocraft.git",
    )
    .run_function(download_model, gpu="any")
)
stub.image = image

if stub.is_inside():
    import torch


@stub.cls(gpu=gpu.A10G(), keep_warm=1)
class Audiocraft:
    def __enter__(self):
        from audiocraft.models import MusicGen

        self.model = MusicGen.get_pretrained("large")

    # modified audiocraft.audio_write() to return bytes
    def audio_write_to_bytes(
        self,
        wav,
        sample_rate: int,
        format: str = "wav",
        normalize: bool = True,
        strategy: str = "peak",
        peak_clip_headroom_db: float = 1,
        rms_headroom_db: float = 18,
        loudness_headroom_db: float = 14,
        log_clipping: bool = True,
    ) -> io.BytesIO:
        from audiocraft.data.audio_utils import i16_pcm, normalize_audio
        import soundfile as sf
        from pydub import AudioSegment

        assert wav.dtype.is_floating_point, "wav is not floating point"
        if wav.dim() == 1:
            wav = wav[None]
        elif wav.dim() > 2:
            raise ValueError("Input wav should be at most 2 dimension.")
        assert wav.isfinite().all()

        wav = normalize_audio(
            wav,
            normalize,
            strategy,
            peak_clip_headroom_db,
            rms_headroom_db,
            loudness_headroom_db,
            log_clipping=log_clipping,
            sample_rate=sample_rate,
        )

        wav = i16_pcm(wav)
        wav_np = wav.numpy()
        audio = AudioSegment(
            data=wav_np.tobytes(),
            sample_width=wav_np.dtype.itemsize,
            frame_rate=sample_rate,
            channels=1,
        )

        audio_bytes = io.BytesIO()

        audio.export(audio_bytes, format=format)
        audio_bytes.seek(0)
        return audio_bytes

    @method()
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        overlap: int = 5,
        format: str = "wav",
    ):
        output = None
        segment_duration = duration

        # looping to generate duration longer than model max limit of 30 secs
        while duration > 0:
            if output is None:
                if segment_duration > self.model.lm.cfg.dataset.segment_duration:
                    segment_duration = self.model.lm.cfg.dataset.segment_duration
                else:
                    segment_duration = duration
            else:
                if duration + overlap < self.model.lm.cfg.dataset.segment_duration:
                    segment_duration = duration + overlap
                else:
                    segment_duration = self.model.lm.cfg.dataset.segment_duration

            self.model.set_generation_params(duration=min(segment_duration, 30))

            if output is None:  # generate first chunk
                next_segment = self.model.generate(descriptions=[prompt])
                duration -= segment_duration
            else:
                last_chunk = output[:, :, -overlap * self.model.sample_rate :]
                next_segment = self.model.generate_continuation(
                    last_chunk, self.model.sample_rate, descriptions=[prompt]
                )
                duration -= segment_duration - overlap

            if output is None:
                output = next_segment
            else:
                output = torch.cat(
                    [
                        output[:, :, : -overlap * self.model.sample_rate],
                        next_segment,
                    ],
                    2,
                )

        output = output.detach().cpu().float()[0]
        clip = self.audio_write_to_bytes(
            output, self.model.sample_rate, strategy="loudness", format=format
        )

        return clip


@stub.local_entrypoint()
def main(prompt: str, duration: int = 10, format: str = "wav"):
    dir = Path("/tmp/audiocraft")
    if not dir.exists():
        dir.mkdir(exist_ok=True, parents=True)

    audiocraft = Audiocraft()
    clip = audiocraft.generate.call(prompt, duration, format)

    output_path = dir / f"output.{format}"
    print(f"Saving to {output_path}")
    with open(output_path, "wb") as f:
        f.write(clip.read())
