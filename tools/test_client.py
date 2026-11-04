"""Send text to a Silero Wyoming server and save the reply as a WAV.

Usage: python test_client.py HOST PORT "Текст" [voice] [--stream]
"""
import asyncio
import sys
import wave

from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.client import AsyncTcpClient
from wyoming.info import Describe, Info
from wyoming.tts import (
    Synthesize, SynthesizeChunk, SynthesizeStart, SynthesizeStop, SynthesizeVoice,
)


async def main(host, port, text, voice=None, stream=False):
    async with AsyncTcpClient(host, int(port)) as c:
        await c.write_event(Describe().event())
        while not Info.is_type((ev := await c.read_event()).type):
            pass
        print("voices:", [v.name for v in Info.from_event(ev).tts[0].voices])

        v = SynthesizeVoice(name=voice) if voice else None
        if stream:
            await c.write_event(SynthesizeStart(voice=v).event())
            for word in text.split(" "):
                await c.write_event(SynthesizeChunk(text=word + " ").event())
            await c.write_event(Synthesize(text=text, voice=v).event())
            await c.write_event(SynthesizeStop().event())
        else:
            await c.write_event(Synthesize(text=text, voice=v).event())

        pcm, rate = b"", 48000
        while True:
            ev = await c.read_event()
            if AudioStart.is_type(ev.type):
                rate = AudioStart.from_event(ev).rate
            elif AudioChunk.is_type(ev.type):
                pcm += AudioChunk.from_event(ev).audio
            elif AudioStop.is_type(ev.type):
                break
        with wave.open("reply.wav", "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(rate)
            f.writeframes(pcm)
        print(f"reply.wav: {len(pcm) / 2 / rate:.1f}s")


args = [a for a in sys.argv[1:] if a != "--stream"]
asyncio.run(main(*args, stream="--stream" in sys.argv))
