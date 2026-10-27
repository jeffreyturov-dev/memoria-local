#!/usr/bin/env python3
"""Generate the explicitly synthetic demo narration (not needed for normal use)."""
import asyncio
from pathlib import Path
import edge_tts

BASE = Path(__file__).resolve().parent

async def main():
    script = (BASE / "demo" / "story_script.txt").read_text(encoding="utf-8")
    output = BASE / "demo" / "memoria_demo.mp3"
    voice = edge_tts.Communicate(script, voice="en-US-JennyNeural", rate="-10%")
    await voice.save(str(output))
    print(f"Created {output} ({output.stat().st_size} bytes)")

asyncio.run(main())
