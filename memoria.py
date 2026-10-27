#!/usr/bin/env python3
"""Memoria: turn an oral-history recording into a private, structured keepsake.

Speech-to-text uses faster-whisper. Story structure uses an open-weight model
served by llama.cpp. No recording or transcript is sent to a cloud AI API.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
from pathlib import Path
import re
import time
import unicodedata
import urllib.request

LLAMA_URL = os.environ.get("MEMORIA_LLAMA_URL", "http://127.0.0.1:8801/v1/chat/completions")
WHISPER_MODEL = os.environ.get("MEMORIA_WHISPER_MODEL", "small")
BASE = Path(__file__).resolve().parent

SYSTEM_PROMPT = """You are an exacting oral-history archivist. Create a memory card using ONLY the supplied transcript.
Return one valid JSON object and nothing else, with exactly these keys:
- title: a short, specific title in the transcript's language
- summary: 2-3 faithful sentences in the transcript's language; never add facts
- people: array of people explicitly mentioned, with their relationship only if stated
- places: array of explicitly mentioned places
- time_references: array of dates, years, ages, or periods explicitly mentioned
- themes: array of 2-5 short themes grounded in the story
- quotes: array of up to 3 short VERBATIM passages copied exactly from the transcript
- follow_up_questions: array of 3 respectful questions that would help preserve more detail
Use empty arrays where evidence is absent. Do not invent names, dates, places, emotions, or events. Do not use Markdown fences."""


def transcribe(audio_path: Path) -> dict:
    """Transcribe locally and preserve segment timestamps."""
    from faster_whisper import WhisperModel

    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments_iter, info = model.transcribe(str(audio_path), beam_size=5, vad_filter=True)
    segments = []
    for segment in segments_iter:
        text = segment.text.strip()
        if text:
            segments.append({"start": round(segment.start, 2), "end": round(segment.end, 2), "text": text})
    transcript = " ".join(item["text"] for item in segments)
    if not transcript:
        raise RuntimeError("Whisper returned an empty transcript")
    return {
        "text": transcript,
        "segments": segments,
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
        "duration_seconds": round(info.duration, 2),
        "model": f"faster-whisper/{WHISPER_MODEL} (CPU int8)",
    }


def extract_json(text: str) -> dict:
    """Accept a raw object or an accidental Markdown fence, then validate its shape."""
    candidate = text.strip()
    candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.I | re.S).strip()
    if not candidate.startswith("{"):
        start, end = candidate.find("{"), candidate.rfind("}")
        if start >= 0 and end > start:
            candidate = candidate[start : end + 1]
    card = json.loads(candidate)
    required = ("title", "summary", "people", "places", "time_references", "themes", "quotes", "follow_up_questions")
    missing = [key for key in required if key not in card]
    if missing:
        raise ValueError(f"Model omitted required keys: {missing}")
    if not isinstance(card["title"], str) or not isinstance(card["summary"], str):
        raise ValueError("title and summary must be strings")
    for key in required[2:]:
        if not isinstance(card[key], list):
            raise ValueError(f"{key} must be an array")
    return {key: card[key] for key in required}


def normalize_words(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def verify_quotes(card: dict, transcript: str) -> list[str]:
    """Deterministically discard any purported quote absent from the source."""
    normalized_transcript = normalize_words(transcript)
    verified = []
    for quote in card["quotes"]:
        if isinstance(quote, str) and normalize_words(quote) in normalized_transcript:
            verified.append(quote.strip())
    return verified


def structure_story(transcript: str) -> dict:
    payload = json.dumps({
        "model": "local",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": "TRANSCRIPT:\n\"\"\"\n" + transcript[:12000] + "\n\"\"\""},
        ],
        "temperature": 0.0,
        "max_tokens": 700,
    }).encode()
    request = urllib.request.Request(LLAMA_URL, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=240) as response:
        result = json.load(response)
    raw = result["choices"][0]["message"]["content"]
    card = extract_json(raw)
    card["quotes"] = verify_quotes(card, transcript)
    card["title"] = card["title"].strip() or "Untitled memory"
    card["summary"] = card["summary"].strip()
    return card


def slugify(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-") or "memory"


def display_item(item) -> str:
    if isinstance(item, dict):
        name = str(item.get("name", "")).strip()
        relationship = str(item.get("relationship", "")).strip()
        if name and relationship:
            return f"{name} — {relationship}"
        return " — ".join(str(value) for value in item.values() if str(value).strip())
    return str(item)


def bullet_list(values: list) -> str:
    return "\n".join(f"- {display_item(item)}" for item in values) if values else "- Not stated in the recording"


def render_markdown(card: dict, transcription: dict, elapsed: float) -> str:
    quotes = "\n".join(f"> {quote}" for quote in card["quotes"]) or "> No verbatim quote passed source validation."
    questions = "\n".join(f"{index}. {question}" for index, question in enumerate(card["follow_up_questions"], 1))
    return f"""# {card['title']}

{card['summary']}

## People
{bullet_list(card['people'])}

## Places
{bullet_list(card['places'])}

## Time references
{bullet_list(card['time_references'])}

## Themes
{bullet_list(card['themes'])}

## Voices worth keeping
{quotes}

## Questions for the next conversation
{questions}

## Original transcript
{transcription['text']}

---
_Private local archive · {transcription['model']} + Gemma 3 4B via llama.cpp · {elapsed:.1f}s · quotes checked against the transcript._
"""


def render_html_card(card: dict, transcription: dict, elapsed: float) -> str:
    """Small dependency-free HTML rendering used by the demo and archive exports."""
    esc = html.escape
    section = lambda title, values: f"<section><h2>{esc(title)}</h2><ul>{''.join(f'<li>{esc(display_item(v))}</li>' for v in values) or '<li>Not stated</li>'}</ul></section>"
    quotes = "".join(f"<blockquote>{esc(q)}</blockquote>" for q in card["quotes"]) or "<p>No quote passed source validation.</p>"
    questions = "".join(f"<li>{esc(str(q))}</li>" for q in card["follow_up_questions"])
    return f"""<article class="memory"><h1>{esc(card['title'])}</h1><p class="summary">{esc(card['summary'])}</p>
{section('People', card['people'])}{section('Places', card['places'])}{section('Time references', card['time_references'])}{section('Themes', card['themes'])}
<section><h2>Voices worth keeping</h2>{quotes}</section><section><h2>Questions for the next conversation</h2><ol>{questions}</ol></section>
<details><summary>Original transcript ({esc(transcription['language'])})</summary><p>{esc(transcription['text'])}</p></details>
<footer>Local only · {elapsed:.1f}s · {transcription['duration_seconds']}s audio · verbatim quotes verified</footer></article>"""


def process_audio(audio_path: Path, output_dir: Path | None = None) -> dict:
    started = time.monotonic()
    transcription = transcribe(audio_path)
    card = structure_story(transcription["text"])
    elapsed = time.monotonic() - started
    result = {"card": card, "transcription": transcription, "elapsed_seconds": round(elapsed, 2)}
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = slugify(card["title"])
        (output_dir / f"{stem}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        (output_dir / f"{stem}.md").write_text(render_markdown(card, transcription, elapsed), encoding="utf-8")
        result["archive_stem"] = stem
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="Path to a WAV, MP3, M4A, or other ffmpeg-readable recording")
    parser.add_argument("--output-dir", type=Path, default=BASE / "archive")
    args = parser.parse_args()
    if not args.audio.is_file():
        parser.error(f"Audio file not found: {args.audio}")
    result = process_audio(args.audio, args.output_dir)
    print(render_markdown(result["card"], result["transcription"], result["elapsed_seconds"]))
    print(f"\nArchive written to {args.output_dir} ({result['archive_stem']}.json/.md)")


if __name__ == "__main__":
    main()
