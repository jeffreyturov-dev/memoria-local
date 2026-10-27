---
title: "Memoria: Keeping Family Voices Alive with Local Whisper + Gemma"
published: true
tags: devchallenge, hf26challenge, gemma, opensource
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 4: Ghost in the Machine](https://dev.to/challenges/hacktoberfest-week4-2026-10-26).*

## What I Built

**Memoria** is a local oral-history archivist. You give it a family voice memo. It returns a structured keepsake containing:

- the complete transcript with timestamps;
- the people, places, and time references explicitly mentioned;
- themes and a short summary;
- verbatim quotes checked against the transcript;
- three thoughtful questions to ask during the next conversation.

The result is exported as JSON and Markdown. There is also a small web interface with a playable demo recording.

I built it for the **Ghost in the Machine** theme as a way to honor the past without surrendering it to a cloud service. A recording of a grandparent is not ordinary prompt data. It can contain names, addresses, health details, and stories that a family never intended to publish.

Memoria runs both speech recognition and language understanding locally. The recording and transcript never leave the machine for inference.

## Demo

**[Open the live Memoria demo](https://actors-pendant-packard-outlet.trycloudflare.com)**

Press **“Archive this memory”** to run the complete pipeline on local CPU models. Please allow about a minute.

The bundled 58-second story is **synthetic and fictional**, narrated with TTS specifically so that no private family recording is exposed. The processing is not mocked: the button runs Whisper and Gemma against that audio. The demo tunnel is temporary; the repository contains everything needed to run it locally.

## Code

**[github.com/jeffreyturov-dev/memoria-local](https://github.com/jeffreyturov-dev/memoria-local)**

The repository includes the CLI, FastAPI demo, synthetic demo audio, generated example output, tests, and setup instructions.

## How I Built It

The pipeline is deliberately small and inspectable:

```text
voice memo
    │
    ▼
faster-whisper / Whisper small (CPU int8)
    │  transcript + segment timestamps
    ▼
Gemma 3 4B IT QAT through llama.cpp
    │  strict JSON memory card
    ▼
deterministic quote validation
    │
    ├── JSON archive
    ├── Markdown keepsake
    └── local web result
```

Whisper handles the voice. Gemma receives only the resulting transcript and must produce eight fields: title, summary, people, places, time references, themes, quotes, and follow-up questions. Temperature is zero, missing evidence becomes an empty array, and the prompt explicitly forbids adding facts.

A small model can still produce a quotation that sounds plausible but does not occur in the recording. For an archive, that is unacceptable. I therefore added a deterministic guard after generation:

```python
def verify_quotes(card, transcript):
    normalized_transcript = normalize_words(transcript)
    verified = []
    for quote in card["quotes"]:
        if isinstance(quote, str) and normalize_words(quote) in normalized_transcript:
            verified.append(quote.strip())
    return verified
```

Only whitespace and letter case are normalized. If the passage is absent, Memoria drops it rather than presenting it as the speaker's words. The original transcript always remains beside the generated card, so a family can review the source rather than trusting the summary blindly.

The demo uses FastAPI, a concurrency lock, and a 25 MB limit for local audio uploads. No API key or account is required.

## The Moment It Landed

The fictional demo story describes a grandfather's radio repair shop, yellow marigolds, cinnamon tea, and a rebuilt red bicycle called *La Valiente*. Memoria recovered those details and preserved this passage verbatim:

> A broken thing is only a story waiting for patient hands.

It then suggested questions such as asking what the radios sounded like and why the bicycle had that name. That was the moment the project stopped feeling like a transcription wrapper: the useful output is not just what was said, but a gentle prompt to record the next chapter while you still can.

The recording is synthetic, and I have kept that distinction visible in the demo and repository. A real family archive should start with consent and human review, not an invented claim of authenticity.

## Verified Results

I ran the project rather than stopping at a screenshot or a plausible demo response:

| Check | Actual result |
|---|---|
| Unit tests | **6/6 passed** |
| Demo audio duration | **57.79 seconds** |
| Full CLI run, audio → archive | **33.36 seconds** |
| Public web run through the tunnel | **29.47 seconds** |
| Whisper language detection | **English, 0.9993 probability** |
| Displayed quotes | **3/3 found in the transcript** |

For the offline-mode run, I forced `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` to a dead localhost address, with only localhost excluded. The complete cached-model pipeline still produced the transcript and memory card. The generated example is committed under `demo/output/` for inspection.

The unit tests cover fenced JSON parsing, missing-field rejection, hallucinated-quote rejection, whitespace normalization, human-readable people fields, and preservation of the original transcript.

## Why Open Innovation Matters

Open weights and open-source inference are not decorative details here; they make the product possible.

**Privacy:** a closed transcription or LLM API would send intimate family material to infrastructure the family does not control. Memoria performs both stages locally.

**Longevity:** an oral-history archive should not become inaccessible because a vendor retired a model endpoint. The code is MIT-licensed, the archive is plain JSON and Markdown, and the inference components can be replaced.

**Offline use:** after the models are downloaded, the pipeline works without cloud AI access. That makes it usable in the places where families actually sit down together, not only where connectivity and a subscription are available.

**Zero marginal inference bill:** there is no per-minute or per-token charge for a longer conversation. The trade-off is CPU latency and the need to review a small model's work.

## Limitations

Memoria does not independently fact-check a summary, and a high language-detection score does not guarantee a perfect transcript. Names can be misheard; in the demo, the source script says “Mateo” while Whisper transcribes “Matteo,” and the card faithfully follows that transcript. This is exactly why the source text and human review remain essential. Only record and archive someone else's story with their consent.

## Prize Categories

- **Best Use of Gemma:** Gemma 3 4B IT QAT performs the local structured memory extraction through llama.cpp.
- **Overall:** a complete, tested, locally runnable oral-history tool with a real public demo.
