# Memoria 🌼

**A private, local oral-history archivist.** Give it a family voice memo; it produces a faithful memory card with the original transcript, people, places, time references, themes, verified verbatim quotes, and thoughtful follow-up questions.

Built for DEV's Hacktoberfest 2026 **Ghost in the Machine** challenge. It honors the past without putting private family recordings on somebody else's server.

**Live demo:** https://collecting-arts-passed-demands.trycloudflare.com (temporary tunnel; local CPU inference can take about a minute).

**DEV challenge write-up:** https://dev.to/jeffreyturov/memoria-keeping-family-voices-alive-with-local-whisper-gemma-eap

## What makes it work

- **faster-whisper / Whisper small**, CPU int8: local speech-to-text with segment timestamps.
- **Gemma 3 4B IT QAT**, served by **llama.cpp**: local structured memory extraction.
- A deterministic guard rejects any generated quote that is not present in the transcript.
- JSON and Markdown archive exports, plus a small FastAPI web demo.
- No cloud AI key, account, tracking, or external inference API.

The bundled recording is **synthetic and fictional** (TTS narration of `demo/story_script.txt`) so the repository exposes no private family audio. The demo still runs the complete real audio → Whisper → Gemma pipeline.

## Run it

Requirements: Python 3.10+, ffmpeg, and a local llama.cpp OpenAI-compatible server. First use downloads the Whisper model; subsequent runs can be fully offline.

```bash
python -m pip install -r requirements.txt
# Start llama.cpp separately with an open-weight Gemma 3 model on port 8801.
python memoria.py path/to/family-story.mp3 --output-dir archive
```

Environment overrides: `MEMORIA_LLAMA_URL` and `MEMORIA_WHISPER_MODEL`.

```bash
python app.py  # http://127.0.0.1:8890
```

The public demo page exposes only the bundled recording. `POST /api/archive` is available for local deployments and limits uploads to 25 MB.

## Test

```bash
python -m unittest discover -s tests -v
# With the local models running:
python memoria.py demo/memoria_demo.mp3 --output-dir demo/output
```

## Verified on 27 October 2026

- 6/6 unit tests passed.
- The 57.79-second synthetic recording completed the full CLI pipeline in 33.36s with external proxy variables forced to a dead localhost address and only localhost excluded.
- The public web demo completed the same real pipeline in 29.47s; English detection confidence was 0.9993 and all three displayed quotes passed source validation.
- The generated example is included in `demo/output/`.

## Privacy and limitations

Only get consent before recording or archiving another person's story. Model-generated summaries and follow-up questions should be reviewed by the family; the original transcript is always preserved. Quotes receive an exact source check (whitespace-normalized). No semantic claim in a summary is presented as independently fact-checked.

## Open-source stack

- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (MIT)
- [Whisper](https://github.com/openai/whisper) (MIT model code; see model card for weights)
- [llama.cpp](https://github.com/ggml-org/llama.cpp) (MIT)
- [Gemma](https://ai.google.dev/gemma) open-weight model, used under the Gemma license
- FastAPI / Uvicorn for the optional demo

MIT-licensed project code; see `LICENSE`.
