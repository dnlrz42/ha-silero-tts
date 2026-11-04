# Silero TTS

Russian text-to-speech for Home Assistant voice assistants, using
[Silero](https://github.com/snakers4/silero-models) voices.

## Setup

1. Start the app. The first start downloads the voice model (~140 MB).
2. Home Assistant discovers it: go to **Settings → Devices & services** and
   add the discovered **Wyoming Protocol** entry.
3. In **Settings → Voice assistants**, pick your assistant and set
   Text-to-speech to **silero**, language Russian, and a voice.

## Voices

| Voice   | Gender |
| ------- | ------ |
| xenia   | female |
| baya    | female |
| kseniya | female |
| aidar   | male   |
| eugene  | male   |

## Options

- **model**: `v5_ru` (newer, default) or `v4_ru`.
- **speaker**: voice used when Home Assistant doesn't ask for a specific one.
- **sample_rate**: 48000 (best), 24000 or 8000 Hz.
- **debug**: more detailed logs.

## Text handling

Silero skips digits and Latin letters, so the app rewrites text first: numbers,
times (18:30), signs (-5, +3), °, % and English words are spelled out in
Russian. Gender and case agreement with numbers isn't handled ("два лампы").

## License

The voice models are © Silero and licensed
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/): personal and
other non-commercial use only. They are downloaded from Silero's servers and
are not part of this app.
