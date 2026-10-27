#!/usr/bin/env python3
"""Memoria live demo: a bundled, clearly synthetic story plus local audio upload."""
from pathlib import Path
import tempfile
import threading
import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from memoria import BASE, process_audio, render_html_card

app = FastAPI(title="Memoria — local oral-history archivist")
app.mount("/demo", StaticFiles(directory=BASE / "demo"), name="demo")
run_lock = threading.Lock()

PAGE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Memoria — keep a voice, keep a story</title>
<style>:root{color-scheme:dark;--gold:#f2b84b;--paper:#17151b;--ink:#f8efe0;--muted:#bcb0a6}*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 75% 0,#4a271f 0,transparent 36%),var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}main{max-width:850px;margin:auto;padding:48px 20px}h1,h2{font-family:Georgia,serif}h1{font-size:clamp(2.4rem,7vw,4.8rem);line-height:1.02;margin:.2em 0}.eyebrow{color:var(--gold);letter-spacing:.18em;text-transform:uppercase}.lede{font-size:1.15rem;max-width:680px;color:var(--muted)}.panel,.memory{background:#211e25e8;border:1px solid #5c4637;border-radius:18px;padding:24px;margin:24px 0;box-shadow:0 20px 70px #0005}button{background:var(--gold);color:#21150a;border:0;border-radius:999px;padding:13px 22px;font-weight:750;cursor:pointer}button:disabled{opacity:.45}audio{width:100%;margin:16px 0}.privacy{border-left:3px solid var(--gold);padding-left:14px}.status{min-height:1.8em;color:var(--gold)}.memory h1{font-size:2.2rem}.memory section{border-top:1px solid #493a32;padding-top:10px}.memory h2{font-size:1.15rem;color:var(--gold)}blockquote{font:italic 1.15rem Georgia,serif;border-left:3px solid var(--gold);margin:14px 0;padding:8px 16px}.summary{font-size:1.12rem}.memory footer,footer{color:var(--muted);font-size:.85rem;margin-top:24px}details{margin-top:20px}#result:empty{display:none}.fine{font-size:.85rem;color:var(--muted)}</style></head><body><main>
<div class="eyebrow">Día de los Muertos · local open AI</div><h1>Memoria</h1><p class="lede">A voice memo becomes a searchable family memory: transcript, people, places, dates, themes, exact quotes, and questions for the next conversation.</p>
<p class="privacy"><strong>No cloud AI.</strong> Whisper and Gemma 3 run on this machine. The audio and transcript never leave it.</p>
<div class="panel"><h2>Hear the demo story</h2><p>This 58-second recording is <strong>synthetic and fictional</strong>, created with TTS so no private family recording is exposed. The processing is real.</p><audio controls preload="none" src="/demo/memoria_demo.mp3"></audio><br><button id="demo" onclick="runDemo()">Archive this memory →</button><div id="status" class="status" role="status"></div><p class="fine">Real local CPU inference: allow about a minute. Every displayed quote is checked against the transcript.</p></div>
<div id="result"></div><footer>Open weights: faster-whisper + Gemma 3 4B IT QAT via llama.cpp. No tracking, account, or API key.</footer></main>
<script>async function runDemo(){const b=document.getElementById('demo'),s=document.getElementById('status'),out=document.getElementById('result');b.disabled=true;s.textContent='Listening and archiving locally…';out.innerHTML='';try{const r=await fetch('/api/demo',{method:'POST'});const j=await r.json();if(!r.ok)throw new Error(j.detail||'Run failed');out.innerHTML=j.html;s.textContent='Archived in '+j.elapsed_seconds+'s — entirely on local open models.'}catch(e){s.textContent='Error: '+e.message}finally{b.disabled=false}}</script></body></html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.get("/api/health")
def health():
    return {"ok": True, "busy": run_lock.locked(), "cloud_ai": False}


def execute(audio: Path, output_dir: Path | None = None):
    if not run_lock.acquire(blocking=False):
        raise HTTPException(429, "Another story is being archived; retry shortly")
    try:
        result = process_audio(audio, output_dir)
        result["html"] = render_html_card(result["card"], result["transcription"], result["elapsed_seconds"])
        return JSONResponse(result)
    finally:
        run_lock.release()


@app.post("/api/demo")
def demo():
    return execute(BASE / "demo" / "memoria_demo.mp3")


@app.post("/api/archive")
async def archive(audio: UploadFile = File(...)):
    """Local deployments may upload a recording; the public page intentionally exposes only the demo."""
    suffix = Path(audio.filename or "recording.wav").suffix[:12] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        size = 0
        while chunk := await audio.read(1024 * 1024):
            size += len(chunk)
            if size > 25 * 1024 * 1024:
                raise HTTPException(413, "Recording exceeds the 25 MB demo limit")
            tmp.write(chunk)
        tmp.flush()
        return execute(Path(tmp.name), BASE / "archive")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8890)
