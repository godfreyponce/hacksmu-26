"""
EchoMap — FastAPI Server
=========================
Serves pipeline output to the frontend.

Frontend expects:
  GET /calls                         → list of all processed calls
  GET /calls/{id}                    → single call detail
  GET /calls/{id}/audio/{stage}      → WAV audio (stage: hpss, gated, clean)
  GET /calls/{id}/spectrogram/{stage}→ spectrogram PNG
  GET /stats                         → aggregate statistics
  POST /query                        → Gemini NL query

To run:
  source backend/venv/bin/activate
  uvicorn backend.main:app --reload --port 8000
"""

import json
import os
import shutil
import uuid

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "summary.json")

# Map frontend "stage" names to our pipeline output filenames.
# The pipeline now saves REAL intermediate audio + spectrograms for every stage,
# so the 3-way stage toggle in the UI is no longer cosmetic.
STAGE_AUDIO = {
    "hpss":  "harmonic.wav",   # after HPSS (harmonic component), pre-gate
    "gated": "gated.wav",      # after spectral subtraction, pre-bandpass
    "clean": "cleaned.wav",    # final (bandpassed) output
}
STAGE_IMAGE = {
    "hpss":  "spectrogram_harmonic.png",
    "gated": "spectrogram_gated.png",
    "clean": "spectrogram_cleaned.png",
}

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="EchoMap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_summary() -> list:
    if not os.path.isfile(SUMMARY_PATH):
        return []
    with open(SUMMARY_PATH) as f:
        return [r for r in json.load(f) if "error" not in r]


def _resolve_file(call_id: str, filename: str) -> str:
    path = os.path.abspath(os.path.join(OUTPUT_DIR, call_id, filename))
    if not os.path.isfile(path):
        raise HTTPException(404, f"Not found: {call_id}/{filename}")
    return path


def _call_to_frontend_shape(r: dict) -> dict:
    """Convert our results.json format to the shape the frontend expects."""
    stem = os.path.splitext(r["filename"])[0]
    calls_detected = r.get("calls_detected", [])

    # Use first call's info as representative for the recording
    first_call = calls_detected[0] if calls_detected else {}

    return {
        "id": stem,
        "call_id_csv": r["filename"],
        "call_type": first_call.get("call_type", "rumble"),
        # snr_* keys are actually an in-call/out-of-call energy ratio (proxy for cleanup),
        # NOT true SNR. Frontend labels them honestly. See r["metric_note"].
        "snr_before_db": r.get("snr_before_db"),
        "snr_after_db": r.get("snr_after_db"),
        "snr_improvement_db": r.get("snr_improvement_db"),
        "metric_note": r.get("metric_note"),
        "duration_seconds": r.get("duration_seconds"),
        "detection_method": r.get("detection_method", "labeled"),
        "call_count": len(calls_detected),
        "calls": calls_detected,
    }


# ---------------------------------------------------------------------------
# Call list & detail (what the Dashboard fetches)
# ---------------------------------------------------------------------------

@app.get("/calls")
def list_calls():
    """All processed recordings, sorted by SNR improvement."""
    raw = _load_summary()
    calls = [_call_to_frontend_shape(r) for r in raw]
    calls.sort(key=lambda x: x["snr_improvement_db"] or 0, reverse=True)
    return calls


@app.get("/calls/{call_id}")
def get_call(call_id: str):
    """Single recording detail."""
    results_path = os.path.join(OUTPUT_DIR, call_id, "results.json")
    if not os.path.isfile(results_path):
        raise HTTPException(404, f"No results for: {call_id}")
    with open(results_path) as f:
        r = json.load(f)
    return _call_to_frontend_shape(r)


# ---------------------------------------------------------------------------
# Audio & spectrogram serving (stage-based for frontend)
# ---------------------------------------------------------------------------

@app.get("/calls/{call_id}/audio/{stage}")
def serve_audio(call_id: str, stage: str):
    """Serve WAV audio for a given processing stage."""
    if stage not in STAGE_AUDIO:
        raise HTTPException(400, f"Unknown stage '{stage}'. Use: hpss, gated, clean")
    path = _resolve_file(call_id, STAGE_AUDIO[stage])
    return FileResponse(path, media_type="audio/wav")


@app.get("/calls/{call_id}/spectrogram/{stage}")
def serve_spectrogram(call_id: str, stage: str):
    """Serve spectrogram PNG for a given processing stage."""
    if stage not in STAGE_IMAGE:
        raise HTTPException(400, f"Unknown stage '{stage}'. Use: hpss, gated, clean")
    path = _resolve_file(call_id, STAGE_IMAGE[stage])
    return FileResponse(path, media_type="image/png")


# ---------------------------------------------------------------------------
# Stats (what the Dashboard header fetches)
# ---------------------------------------------------------------------------

@app.get("/stats")
def get_stats():
    """Aggregate stats in the shape the frontend Dashboard expects."""
    raw = _load_summary()

    # Count by call type
    by_type = {}
    total_calls = 0
    for r in raw:
        for c in r.get("calls_detected", []):
            ct = c.get("call_type", "unknown")
            by_type[ct] = by_type.get(ct, 0) + 1
            total_calls += 1

    # Compute real stats from data
    improvements = [r.get("snr_improvement_db", 0) for r in raw if r.get("snr_improvement_db") is not None]
    avg_improvement = sum(improvements) / len(improvements) if improvements else 0
    improved_count = sum(1 for v in improvements if v > 0)

    return {
        "total_calls": total_calls,
        "total_recordings": len(raw),
        "improved_count": improved_count,
        "avg_snr_improvement_db": round(avg_improvement, 1),
        "by_call_type": by_type,
    }


# ---------------------------------------------------------------------------
# Gemini NL query (POST /query)
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    text: str


@app.post("/query")
async def natural_language_query(req: QueryRequest):
    """
    Natural language question about the elephant call data.
    Uses Gemini if GEMINI_API_KEY is set, otherwise returns a stats-based answer.
    """
    raw = _load_summary()
    total = sum(len(r.get("calls_detected", [])) for r in raw)
    improved = sum(1 for r in raw if r.get("snr_improvement_db", 0) > 0)
    best = max(raw, key=lambda r: r.get("snr_improvement_db", 0)) if raw else {}

    # Build context from our processed data
    calls_context = []
    for r in raw[:20]:
        stem = os.path.splitext(r["filename"])[0]
        for c in r.get("calls_detected", []):
            calls_context.append(
                f"- {stem}: {c.get('call_type','unknown')} call, "
                f"fundamental {c.get('estimated_fundamental_hz','?')} Hz, "
                f"SNR improvement {r.get('snr_improvement_db',0):+.1f} dB"
            )

    api_key = os.getenv("GEMINI_API_KEY", "")

    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)

            prompt = f"""You are EchoMap, an AI assistant for elephant vocalization research.
You have access to data from {len(raw)} processed recordings containing {total} detected elephant calls.
{improved} recordings showed SNR improvement after noise removal.
Best result: {best.get('filename','')} with +{best.get('snr_improvement_db',0):.1f} dB improvement.

Sample call data:
{chr(10).join(calls_context[:15])}

User question: {req.text}

Provide a helpful, scientifically accurate response. Keep it concise."""

            model = genai.GenerativeModel("gemini-2.0-flash")
            response = model.generate_content(prompt)
            return {"answer": response.text}
        except Exception as e:
            return {"answer": f"Gemini query failed ({e}). Falling back to local stats."}

    # Fallback without Gemini
    return {
        "answer": f"EchoMap has processed {len(raw)} recordings containing {total} elephant calls. "
                  f"{improved} recordings showed noise improvement. "
                  f"Best result: {best.get('filename','')} at +{best.get('snr_improvement_db',0):.1f} dB. "
                  f"Set GEMINI_API_KEY for detailed AI-powered answers."
    }


# ---------------------------------------------------------------------------
# Real-time processing (upload a .wav, run pipeline, return results)
# ---------------------------------------------------------------------------

TEMP_DIR = os.path.join(OUTPUT_DIR, "_temp")
CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "calls.csv")


@app.post("/process")
async def process_upload(file: UploadFile = File(...)):
    """Accept a .wav upload, run the full pipeline, return results."""
    if not file.filename.lower().endswith(".wav"):
        raise HTTPException(400, "Only .wav files are supported")

    session_id = uuid.uuid4().hex[:12]
    session_dir = os.path.join(TEMP_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # Save uploaded file
    wav_path = os.path.join(session_dir, file.filename)
    with open(wav_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Run pipeline — handle both `uvicorn backend.main:app` and direct run
    import sys
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from backend.pipeline.process import process_recording

    out_dir = os.path.join(session_dir, "output")
    os.makedirs(out_dir, exist_ok=True)

    try:
        results = process_recording(wav_path, CSV_PATH, out_dir)
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {e}")

    # Build response
    base_url = f"/temp/{session_id}"
    shaped = _call_to_frontend_shape(results)
    shaped["session_id"] = session_id
    shaped["spectrogram_before_url"] = f"{base_url}/output/spectrogram_before.png"
    shaped["spectrogram_after_url"] = f"{base_url}/output/spectrogram_after.png"
    shaped["audio_original_url"] = f"{base_url}/output/original.wav"
    shaped["audio_cleaned_url"] = f"{base_url}/output/cleaned.wav"
    return shaped


@app.get("/temp/{session_id}/{path:path}")
def serve_temp_file(session_id: str, path: str):
    """Serve files from a temporary processing session."""
    file_path = os.path.abspath(os.path.join(TEMP_DIR, session_id, path))
    # Prevent directory traversal
    if not file_path.startswith(os.path.abspath(TEMP_DIR)):
        raise HTTPException(403, "Forbidden")
    if not os.path.isfile(file_path):
        raise HTTPException(404, "File not found")
    ext = os.path.splitext(file_path)[1].lower()
    media = {".wav": "audio/wav", ".png": "image/png", ".json": "application/json"}
    return FileResponse(file_path, media_type=media.get(ext, "application/octet-stream"))


# ---------------------------------------------------------------------------
# Legacy endpoints (keep working for demo.html and direct access)
# ---------------------------------------------------------------------------

@app.get("/clips/{filename}")
def serve_clip_legacy(filename: str):
    """Legacy: /clips/{callId}_noisy.wav or /clips/{callId}_clean.wav"""
    stem = filename
    for ext in (".wav",):
        if filename.lower().endswith(ext):
            stem = filename[:-len(ext)]
    parts = stem.rsplit("_", 1)
    if len(parts) != 2 or parts[1] not in ("noisy", "clean"):
        raise HTTPException(400, "Use /calls/{id}/audio/{stage} instead")
    variant_map = {"noisy": "original.wav", "clean": "cleaned.wav"}
    path = _resolve_file(parts[0], variant_map[parts[1]])
    return FileResponse(path, media_type="audio/wav")


@app.get("/comparisons/{call_id}.png")
def serve_comparison(call_id: str):
    return FileResponse(_resolve_file(call_id, "comparison.png"), media_type="image/png")


@app.get("/waveforms/{call_id}.png")
def serve_waveform(call_id: str):
    return FileResponse(_resolve_file(call_id, "waveform.png"), media_type="image/png")


@app.get("/demo")
def serve_demo():
    demo_path = os.path.join(OUTPUT_DIR, "demo.html")
    if not os.path.isfile(demo_path):
        raise HTTPException(404, "demo.html not found")
    return FileResponse(demo_path, media_type="text/html")


@app.get("/health")
def health():
    output_exists = os.path.isdir(OUTPUT_DIR)
    summary_exists = os.path.isfile(SUMMARY_PATH)
    n = len([d for d in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, d))]) if output_exists else 0
    return {"status": "ok", "output_dir": output_exists, "summary_json": summary_exists, "recordings_available": n}
