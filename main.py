from pathlib import Path

from modal import Image, Stub, method, gpu

stub = Stub("musicgen")

def download_model():
    from audiocraft.models import MusicGen

    MusicGen.get_pretrained('large')


image = (
    Image.debian_slim()
    .apt_install("git", "ffmpeg")
    .pip_install(
        "torch",
        "git+https://github.com/facebookresearch/audiocraft.git"
    )
    .run_function(download_model, gpu="any")
)
stub.image = image

@stub.cls(gpu=gpu.A100())
class Audiocraft:
    def __enter__(self):
        import torchaudio
        from audiocraft.models import MusicGen

        self.model = MusicGen.get_pretrained('large')

    @method()
    def generate(self):
        from audiocraft.data.audio import audio_write
        descriptions = ['happy rock', 'energetic EDM', 'sad jazz']

        wav = self.model.generate(descriptions)  # generates 3 samples.

        clips = []
        for idx, one_wav in enumerate(wav):
            # Will save under {idx}.wav, with loudness normalization at -14 db LUFS.
            clips.append(audio_write(f'{idx}', one_wav.cpu(), self.model.sample_rate, strategy="loudness"))
            print(clips)
        return clips

@stub.local_entrypoint()
def main():
    import wave

    dir = Path("/tmp/audiocraft")
    if not dir.exists():
        dir.mkdir(exist_ok=True, parents=True)

    audiocraft = Audiocraft()
    print("Generating clips")
    clips = audiocraft.generate.call()
    print(clips)
