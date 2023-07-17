from pathlib import Path
import io

from modal import Image, Stub, method, gpu, asgi_app

MAX_SEGMENT_DURATION = 30

stub = Stub("boombot")


def download_models():
    from audiocraft.models import MusicGen

    MusicGen.get_pretrained("large")
    MusicGen.get_pretrained("melody")


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
    .run_function(download_models, gpu="any")
)
stub.image = image

if stub.is_inside():
    import torch
    import torchaudio


@stub.cls(gpu=gpu.A10G())
class Audiocraft:
    def __enter__(self):
        from audiocraft.models import MusicGen

        self.model_large = MusicGen.get_pretrained("large")
        self.model_melody = MusicGen.get_pretrained("melody")

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

    def load_and_clip_melody(self, url: str):
        import requests

        # check file format
        _, file_extension = url.rsplit(".", 1)
        if file_extension.lower() not in ["mp3", "wav"]:
            raise ValueError(f"Invalid file format. Only .mp3 and .wav are supported.")

        _, filepath = url.rsplit("/", 1)
        response = requests.get(url)

        # checking if the request was successful (status code 200)
        if response.status_code == 200:
            with open(filepath, "wb") as file:
                file.write(response.content)
            print("File downloaded successfully.")
        else:
            raise Exception(f"Error: {response.status_code} - {response.reason}")
        melody_waveform, sr = torchaudio.load(filepath)

        # checking duration of audio and clipping to first 30 secs if too long
        melody_duration = melody_waveform.size(1) / sr
        if melody_duration > MAX_SEGMENT_DURATION:
            melody_waveform = melody_waveform[:, : MAX_SEGMENT_DURATION * sr]

        return melody_waveform, sr

    @method()
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        format: str = "wav",
        melody_url: str = "",
    ):
        output = None
        segment_duration = (
            MAX_SEGMENT_DURATION if duration > MAX_SEGMENT_DURATION else duration
        )
        overlap = 10

        if len(melody_url) != 0:
            model = self.model_melody
            melody_waveform, sr = self.load_and_clip_melody(melody_url)
            self.model_melody.set_generation_params(
                duration=min(segment_duration, MAX_SEGMENT_DURATION)
            )
            output = self.model_melody.generate_with_chroma(
                descriptions=[prompt],
                melody_wavs=melody_waveform.unsqueeze(0),
                melody_sample_rate=sr,
                progress=True,
            )
            duration -= segment_duration
        else:
            model = self.model_large
            sr = self.model_large.sample_rate

        # looping to generate duration longer than model max of 30 secs
        while duration > 0:
            if output is not None:
                if (duration + overlap) < MAX_SEGMENT_DURATION:
                    segment_duration = duration + overlap
                else:
                    segment_duration = MAX_SEGMENT_DURATION

            model.set_generation_params(
                duration=min(segment_duration, MAX_SEGMENT_DURATION)
            )

            if output is None:  # generate first chunk
                next_segment = model.generate(descriptions=[prompt])
                duration -= segment_duration
            else:
                last_chunk = output[:, :, -overlap * sr :]
                next_segment = model.generate_continuation(
                    last_chunk, sr, descriptions=[prompt]
                )
                duration -= segment_duration - overlap

            if output is None:
                output = next_segment
            else:
                output = torch.cat(
                    [
                        output[:, :, : -overlap * sr],
                        next_segment,
                    ],
                    2,
                )

        output = output.detach().cpu().float()[0]
        clip = self.audio_write_to_bytes(
            output, model.sample_rate, strategy="loudness", format=format
        )
        melody_clip = (
            self.audio_write_to_bytes(
                melody_waveform[0], sr, strategy="loudness", format=format
            )
            if len(melody_url) > 0
            else None
        )

        return melody_clip, clip


@stub.local_entrypoint()
def main(prompt: str, duration: int = 10, format: str = "wav", melody: str = ""):
    dir = Path("/tmp/audiocraft")
    if not dir.exists():
        dir.mkdir(exist_ok=True, parents=True)

    audiocraft = Audiocraft()
    melody_clip, clip = audiocraft.generate.call(
        prompt, duration=duration, format=format, melody_url=melody
    )

    if melody_clip:
        output_path = dir / f"melody_clip.{format}"
        print(f"Saving to {output_path}")
        with open(output_path, "wb") as f:
            f.write(melody_clip.read())

    output_path = dir / f"output.{format}"
    print(f"Saving to {output_path}")
    with open(output_path, "wb") as f:
        f.write(clip.read())
