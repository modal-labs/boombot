from pathlib import Path

from fastapi import FastAPI
from modal import Image, Stub, method, gpu, Mount, asgi_app

MODEL_DIR = "/model"

stub = Stub("musicgen")
web_app = FastAPI()


def download_model():
    from audiocraft.models import MusicGen

    MusicGen.get_pretrained("melody")
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


@stub.cls(
    gpu=gpu.A100(),
    mounts=[
        Mount.from_local_dir(
            "/Users/rachelpark/musicmaker/assets", remote_path="/root/app/assets"
        )
    ],
)
class Audiocraft:
    def __enter__(self):
        from audiocraft.models import MusicGen

        self.model_melody = MusicGen.get_pretrained("melody")
        self.model_large = MusicGen.get_pretrained("large")

    @method()
    def generate(self, prompt: str, melody_path: str = ""):
        from audiocraft.data.audio_utils import i16_pcm, normalize_audio
        import soundfile as sf
        import io
        import torch
        import torchaudio
        from pydub import AudioSegment

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

        self.model_melody.set_generation_params(duration=8)
        self.model_large.set_generation_params(duration=10)

        if len(melody_path) == 0:
            wav = self.model_large.generate([prompt])
        else:
            melody_waveform, sr = torchaudio.load(melody_path)
            melody_waveform = melody_waveform.unsqueeze(0).repeat(2, 1, 1)
            # wav = self.model_melody.generate_with_chroma(
            #     descriptions=[prompt],
            #     melody_wavs=melody_waveform,
            #     melody_sample_rate=sr,
            #     progress=True,
            # )
            wav = self.model_melody.generate_continuation(
                prompt=melody_waveform, prompt_sample_rate=sr
            )

        clips = []
        for one_wav in wav:
            clips.append(
                audio_write_to_bytes(
                    one_wav.cpu(), self.model_large.sample_rate, strategy="loudness"
                )
            )
        return clips


@stub.function()
@asgi_app()
def web():
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    import io

    web_app = FastAPI()
    audiocraft = Audiocraft()

    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @web_app.post("/generate")
    async def generate(request: Request):
        body = await request.json()
        prompt = body["prompt"]

        clips = audiocraft.generate.call(prompt)

        clip = clips[0]
        response = StreamingResponse(
            io.BytesIO(clip.getvalue()), media_type="audio/wav"
        )

        return response

    return web_app


@stub.local_entrypoint()
def main(prompt: str, melody_path: str = ""):
    dir = Path("/tmp/audiocraft")
    if not dir.exists():
        dir.mkdir(exist_ok=True, parents=True)

    audiocraft = Audiocraft()
    print("Generating clips")
    clips = audiocraft.generate.call(prompt, melody_path)
    for idx, clip in enumerate(clips):
        output_path = dir / f"field_{idx}.wav"
        print(f"Saving to {output_path}")
        with open(output_path, "wb") as f:
            f.write(clip.read())
