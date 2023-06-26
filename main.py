from pathlib import Path

from modal import Image, Stub, method, gpu

stub = Stub("musicgen")


def download_model():
    from audiocraft.models import MusicGen

    MusicGen.get_pretrained("large")


image = (
    Image.debian_slim()
    .apt_install("git", "ffmpeg")
    .pip_install(
        "torch",
        "soundfile",
        "pydub",
        "git+https://github.com/facebookresearch/audiocraft.git",
    )
    .run_function(download_model, gpu="any")
)
stub.image = image


@stub.cls(gpu=gpu.A100())
class Audiocraft:
    def __enter__(self):
        from audiocraft.models import MusicGen

        self.model = MusicGen.get_pretrained("large")

    @method()
    def generate(self):
        from audiocraft.data.audio_utils import i16_pcm, normalize_audio
        import soundfile as sf
        import io
        import torch
        from pydub import AudioSegment

        descriptions = ["cheerful pop", "sad rock", "soft EDM", "happy jazz"]

        def audio_write_to_bytes(
            wav: torch.Tensor,
            sample_rate: int,
            format: str = "wav",
            mp3_rate: int = 320,
            normalize: bool = True,
            strategy: str = "peak",
            peak_clip_headroom_db: float = 1,
            rms_headroom_db: float = 18,
            loudness_headroom_db: float = 14,
            loudness_compressor: bool = False,
            log_clipping: bool = True,
        ) -> io.BytesIO:
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
            if format == "mp3":
                raise RuntimeError("MP3 format not supported with PyDub.")
            elif format == "wav":
                wav = i16_pcm(wav)
                wav_np = wav.numpy()
                audio = AudioSegment(
                    data=wav_np.tobytes(),
                    sample_width=wav_np.dtype.itemsize,
                    frame_rate=sample_rate,
                    channels=1,
                )
            else:
                raise RuntimeError(
                    f"Invalid format {format}. Only wav or mp3 are supported."
                )

            # Create BytesIO object
            audio_bytes = io.BytesIO()

            # Export PyDub audio to BytesIO object
            audio.export(audio_bytes, format=format)
            audio_bytes.seek(0)
            return audio_bytes

        self.model.set_generation_params(duration=8)
        wav = self.model.generate(descriptions)  # generates 3 samples.

        clips = []
        for one_wav in wav:
            # Will save under {idx}.wav, with loudness normalization at -14 db LUFS.
            clips.append(
                audio_write_to_bytes(
                    one_wav.cpu(), self.model.sample_rate, strategy="loudness"
                )
            )
        return clips


@stub.local_entrypoint()
def main():
    dir = Path("/tmp/musicgen")
    if not dir.exists():
        dir.mkdir(exist_ok=True, parents=True)

    audiocraft = Audiocraft()
    print("Generating clips")
    clips = audiocraft.generate.call()
    for idx, clip in enumerate(clips):
        output_path = dir / f"{idx}.wav"
        print(f"Saving to {output_path}")
        with open(output_path, "wb") as f:
            f.write(clip.read())
