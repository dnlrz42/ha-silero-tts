# Silero TTS for Home Assistant (unofficial)

Russian text-to-speech for Home Assistant voice assistants, using
[Silero](https://github.com/snakers4/silero-models) voices. Runs as a Home
Assistant app (add-on) and talks to Home Assistant over the Wyoming protocol,
like Piper.

- 5 Russian voices: xenia, baya, kseniya, aidar, eugene
- Fast on CPU: a 6-second reply takes well under a second on an x86 mini PC
- Streams long assistant replies sentence by sentence
- Spells out numbers, times, °, % and English words, which Silero would
  otherwise skip

## Install

[![Add repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fdnlrz42%2Fha-silero-tts)

Or in Home Assistant: **Settings → Apps → App store → ⋮ → Repositories**, add
`https://github.com/dnlrz42/ha-silero-tts`, then install **Silero TTS**.
See [the app's docs](silero_tts/DOCS.md) for setup.

## Repository layout

- `silero_tts/`: the app (`server.py` Wyoming server, `normalize.py` text cleanup)
- `tools/test_client.py`: send text to a running server and save `reply.wav`
- `tools/speak.py`: generate speech locally without a server
- `.github/workflows/build.yaml`: builds and publishes images to ghcr.io when
  the version in `silero_tts/config.yaml` changes

## Licenses

- Code in this repository: [MIT](LICENSE).
- Silero voice models: © Silero, [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/),
  non-commercial use only. The models are not included in this repository or
  its images; the app downloads them from Silero's servers on first start.
- The image contains third-party packages under their own licenses (PyTorch,
  NumPy, SciPy: BSD-style; Wyoming: MIT; num2words: LGPL-2.1, unmodified).

This project is not affiliated with or endorsed by the Silero team.
