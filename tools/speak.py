"""Generate Russian speech with Silero TTS.

Usage:
  python speak.py "Текст" [--model v5_ru] [--speaker xenia] [--out out.wav]
  python speak.py --samples   # one file per voice for both models
"""
import argparse
import time
import wave
from pathlib import Path

import torch

ROOT = Path(__file__).parent.parent
SAMPLE_RATE = 48000
SAMPLE_TEXT = (
    "Привет! Сегодня четвёртое ноября, на улице плюс пять градусов. "
    "Я включила свет в гостиной и поставила чайник. "
    "Напомню: в восемнадцать тридцать у тебя встреча."
)


def load(model_name):
    imp = torch.package.PackageImporter(str(ROOT / "models" / f"{model_name}.pt"))
    model = imp.load_pickle("tts_models", "model")
    model.to(torch.device("cpu"))
    return model


def synth(model, text, speaker, out):
    audio = model.apply_tts(
        text=text, speaker=speaker, sample_rate=SAMPLE_RATE,
        put_accent=True, put_yo=True,
    )
    pcm = (audio.clamp(-1, 1) * 32767).to(torch.int16).numpy()
    with wave.open(str(out), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(pcm.tobytes())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?", default=SAMPLE_TEXT)
    p.add_argument("--model", default="v5_ru")
    p.add_argument("--speaker", default="xenia")
    p.add_argument("--out", default="out.wav")
    p.add_argument("--samples", action="store_true")
    a = p.parse_args()

    if not a.samples:
        synth(load(a.model), a.text, a.speaker, a.out)
        print(a.out)
        return

    out_dir = ROOT / "samples"
    out_dir.mkdir(exist_ok=True)
    for name in ("v5_ru", "v4_ru"):
        model = load(name)
        for spk in model.speakers:
            if spk == "random":
                continue
            out = out_dir / f"{name}_{spk}.wav"
            t = time.time()
            synth(model, a.text, spk, out)
            print(f"{out.name}: {time.time() - t:.1f}s")


if __name__ == "__main__":
    main()
