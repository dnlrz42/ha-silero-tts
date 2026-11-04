"""Wyoming TTS server for Silero Russian voices."""
import argparse
import asyncio
import json
import logging
import os
import re
import socket
import urllib.request
from functools import partial
from pathlib import Path

import torch
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Attribution, Describe, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncEventHandler, AsyncServer
from wyoming.tts import (
    Synthesize,
    SynthesizeChunk,
    SynthesizeStart,
    SynthesizeStop,
    SynthesizeStopped,
)

from normalize import normalize, split_sentences

_LOG = logging.getLogger("silero")
MODEL_URL = "https://models.silero.ai/models/tts/ru/{name}.pt"
SAMPLES_PER_CHUNK = 2048
SENTENCE_END = re.compile(r"[.!?…]\s")


class Silero:
    def __init__(self, model_path: Path, sample_rate: int, default_speaker: str):
        torch.set_num_threads(max(1, os.cpu_count() or 1))
        imp = torch.package.PackageImporter(str(model_path))
        self.model = imp.load_pickle("tts_models", "model")
        self.model.to(torch.device("cpu"))
        self.sample_rate = sample_rate
        self.speakers = [s for s in self.model.speakers if s != "random"]
        self.default_speaker = (
            default_speaker if default_speaker in self.speakers else self.speakers[0]
        )
        self.lock = asyncio.Lock()

    def _synth(self, text: str, speaker: str) -> bytes:
        audio = self.model.apply_tts(
            text=text,
            speaker=speaker,
            sample_rate=self.sample_rate,
            put_accent=True,
            put_yo=True,
        )
        return (audio.clamp(-1, 1) * 32767).to(torch.int16).numpy().tobytes()

    async def synth(self, text: str, speaker: str | None) -> list[bytes]:
        """Return PCM for each sentence; skips text Silero can't read."""
        speaker = speaker if speaker in self.speakers else self.default_speaker
        out = []
        loop = asyncio.get_running_loop()
        for sentence in split_sentences(normalize(text)):
            if not re.search(r"[а-яё]", sentence, re.IGNORECASE):
                continue
            async with self.lock:
                try:
                    out.append(
                        await loop.run_in_executor(
                            None, partial(self._synth, sentence, speaker)
                        )
                    )
                except Exception:  # noqa: BLE001
                    _LOG.exception("Failed to synthesize: %s", sentence)
        return out


class Handler(AsyncEventHandler):
    def __init__(self, info: Info, tts: Silero, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.info = info
        self.tts = tts
        self.streaming = False
        self.stream_voice: str | None = None
        self.buffer = ""
        self.audio_started = False

    async def handle_event(self, event: Event) -> bool:
        if Describe.is_type(event.type):
            await self.write_event(self.info.event())
            return True

        if SynthesizeStart.is_type(event.type):
            start = SynthesizeStart.from_event(event)
            self.streaming = True
            self.stream_voice = start.voice.name if start.voice else None
            self.buffer = ""
            self.audio_started = False
            return True

        if SynthesizeChunk.is_type(event.type) and self.streaming:
            self.buffer += SynthesizeChunk.from_event(event).text
            # Speak every finished sentence right away
            last = None
            for last in SENTENCE_END.finditer(self.buffer):
                pass
            if last:
                ready, self.buffer = self.buffer[: last.end()], self.buffer[last.end():]
                await self._speak(ready, self.stream_voice)
            return True

        if SynthesizeStop.is_type(event.type) and self.streaming:
            await self._speak(self.buffer, self.stream_voice)
            await self._finish()
            await self.write_event(SynthesizeStopped().event())
            self.streaming = False
            return True

        if Synthesize.is_type(event.type):
            if self.streaming:
                return True  # full text also arrives during streaming; ignore it
            synth = Synthesize.from_event(event)
            self.audio_started = False
            await self._speak(synth.text, synth.voice.name if synth.voice else None)
            await self._finish()
            return True

        return True

    async def _speak(self, text: str, voice: str | None) -> None:
        if not text.strip():
            return
        for pcm in await self.tts.synth(text, voice):
            await self._start()
            for i in range(0, len(pcm), SAMPLES_PER_CHUNK * 2):
                await self.write_event(
                    AudioChunk(
                        audio=pcm[i : i + SAMPLES_PER_CHUNK * 2],
                        rate=self.tts.sample_rate,
                        width=2,
                        channels=1,
                    ).event()
                )

    async def _start(self) -> None:
        if not self.audio_started:
            await self.write_event(
                AudioStart(rate=self.tts.sample_rate, width=2, channels=1).event()
            )
            self.audio_started = True

    async def _finish(self) -> None:
        await self._start()  # HA expects start/stop even for empty audio
        await self.write_event(AudioStop().event())
        self.audio_started = False


def ensure_model(name: str, data_dir: Path) -> Path:
    bundled = Path(__file__).parent / "models" / f"{name}.pt"
    if bundled.exists():
        return bundled
    path = data_dir / f"{name}.pt"
    if not path.exists():
        _LOG.info("Downloading %s", name)
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(MODEL_URL.format(name=name), tmp)
        tmp.rename(path)
    return path


def announce_to_home_assistant(port: int) -> None:
    """Let HA auto-discover this server (only works as a HA add-on)."""
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return
    body = json.dumps(
        {"service": "wyoming", "config": {"uri": f"tcp://{socket.gethostname()}:{port}"}}
    ).encode()
    req = urllib.request.Request(
        "http://supervisor/discovery",
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        _LOG.info("Announced to Home Assistant")
    except Exception:  # noqa: BLE001
        _LOG.exception("Discovery announcement failed")


async def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--uri", default="tcp://0.0.0.0:10200")
    p.add_argument("--model", default="v5_ru")
    p.add_argument("--speaker", default="xenia")
    p.add_argument("--sample-rate", type=int, default=48000)
    p.add_argument("--data-dir", default="/data")
    p.add_argument("--debug", action="store_true")
    p.add_argument("--options", help="HA add-on options.json (overrides flags)")
    a = p.parse_args()
    if a.options and Path(a.options).exists():
        opts = json.loads(Path(a.options).read_text())
        a.model = opts.get("model", a.model)
        a.speaker = opts.get("speaker", a.speaker)
        a.sample_rate = int(opts.get("sample_rate", a.sample_rate))
        a.debug = opts.get("debug", a.debug)
    logging.basicConfig(level=logging.DEBUG if a.debug else logging.INFO)

    data_dir = Path(a.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    tts = Silero(ensure_model(a.model, data_dir), a.sample_rate, a.speaker)
    await tts.synth("Готово.", None)  # warm up so the first request is fast

    attribution = Attribution(name="Silero", url="https://github.com/snakers4/silero-models")
    voices = [
        TtsVoice(
            name=s,
            description=s,
            attribution=attribution,
            installed=True,
            version=a.model,
            languages=["ru"],
        )
        for s in tts.speakers
    ]
    info = Info(
        tts=[
            TtsProgram(
                name="silero",
                description="Silero Russian TTS",
                attribution=attribution,
                installed=True,
                version=a.model,
                voices=voices,
                supports_synthesize_streaming=True,
            )
        ]
    )

    server = AsyncServer.from_uri(a.uri)
    _LOG.info("Ready on %s (model %s, voices %s)", a.uri, a.model, tts.speakers)
    announce_to_home_assistant(int(a.uri.rsplit(":", 1)[1]))
    await server.run(partial(Handler, info, tts))


if __name__ == "__main__":
    asyncio.run(main())
