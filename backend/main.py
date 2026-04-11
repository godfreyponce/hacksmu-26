"""
EchoMap — FastAPI Server
=========================
Bridges the pipeline output (output/{stem}/) to the frontend.

The frontend expects URLs like:
  /clips/{callId}_noisy.wav      → output/{callId}/original.wav
  /clips/{callId}_clean.wav      → output/{callId}/cleaned.wav
  /spectrograms/{callId}_noisy.png → output/{callId}/spectrogram_before.png
  /spectrograms/{callId}_clean.png → output/{callId}/spectrogram_after.png

To run:
  source backend/venv/bin/activate
  pip install -r backend/requirements.txt
  uvicorn backend.main:app --reload --port 8000
"""

import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# ---------------------------------------------------------------------------
# Paths — relative to repo root (where uvicorn is launched from)
# ---------------------------------------------------------------------------
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")
SUMMARY_PATH = os.path.join(OUTPUT_DIR, "summary.json")

# Maps the variant token in the URL to the actual filename on disk
VARIANT_AUDIO = {
    "noisy": "original.wav",
    "clean": "cleaned.wav",
}
VARIANT_IMAGE = {
    "noisy": "spectrogram_before.png",
    "clean": "spectrogram_after.png",
}

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="EchoMap API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend dev server on any port
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_call_id_and_variant(filename: str, extensions: tuple) -> tuple[str, str]:
    """
    Split a filename like "04-040920-02_vehicle_1_noisy.wav" into
    call_id = "04-040920-02_vehicle_1" and variant = "noisy".

    The variant is always the last underscore-delimited segment before the extension.
    """
    # Strip known extensions
    stem = filename
    for ext in extensions:
        if filename.lower().endswith(ext):
            stem = filename[: -len(ext)]
            break

    # Last segment after the final underscore is the variant
    parts = stem.rsplit("_", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail=f"Filename must be {{callId}}_{{variant}}.ext, got: {filename}",
        )
    call_id, variant = parts
    return call_id, variant


def _resolve_output_file(call_id: str, relative_filename: str) -> str:
    """Return the absolute path to a file inside output/{call_id}/."""
    path = os.path.abspath(os.path.join(OUTPUT_DIR, call_id, relative_filename))
    if not os.path.isfile(path):
        raise HTTPException(
            status_code=404,
            detail=f"File not found: output/{call_id}/{relative_filename}",
        )
    return path


# ---------------------------------------------------------------------------
# Audio endpoints
# ---------------------------------------------------------------------------

@app.get("/clips/{filename}")
def serve_clip(filename: str):
    """
    Serve a WAV audio file.
    URL pattern: /clips/{callId}_noisy.wav  or  /clips/{callId}_clean.wav
    """
    call_id, variant = _parse_call_id_and_variant(filename, (".wav",))

    if variant not in VARIANT_AUDIO:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown variant '{variant}'. Use 'noisy' or 'clean'.",
        )

    file_path = _resolve_output_file(call_id, VARIANT_AUDIO[variant])
    return FileResponse(file_path, media_type="audio/wav")


# ---------------------------------------------------------------------------
# Spectrogram endpoints
# ---------------------------------------------------------------------------

@app.get("/spectrograms/{filename}")
def serve_spectrogram(filename: str):
    """
    Serve a spectrogram PNG.
    URL pattern: /spectrograms/{callId}_noisy.png  or  /spectrograms/{callId}_clean.png
    """
    call_id, variant = _parse_call_id_and_variant(filename, (".png",))

    if variant not in VARIANT_IMAGE:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown variant '{variant}'. Use 'noisy' or 'clean'.",
        )

    file_path = _resolve_output_file(call_id, VARIANT_IMAGE[variant])
    return FileResponse(file_path, media_type="image/png")


# ---------------------------------------------------------------------------
# Call metadata endpoints
# ---------------------------------------------------------------------------

@app.get("/api/calls")
def list_calls():
    """
    Return metadata for all processed recordings, sorted by SNR improvement (best first).
    Built from output/summary.json which the batch pipeline writes automatically.
    """
    if not os.path.isfile(SUMMARY_PATH):
        raise HTTPException(
            status_code=503,
            detail="summary.json not found — has the pipeline been run?",
        )

    with open(SUMMARY_PATH) as f:
        raw = json.load(f)

    calls = []
    for r in raw:
        if "error" in r:
            continue
        stem = os.path.splitext(r["filename"])[0]
        calls.append({
            "id": stem,
            "filename": r["filename"],
            "snr_before_db": r.get("snr_before_db"),
            "snr_after_db": r.get("snr_after_db"),
            "snr_improvement_db": r.get("snr_improvement_db"),
            "duration_seconds": r.get("duration_seconds"),
            "call_count": len(r.get("calls_detected", [])),
            "calls": r.get("calls_detected", []),
            "processing_params": r.get("processing_params", {}),
        })

    # Sort best improvement first — useful for the dashboard to lead with the best demos
    calls.sort(key=lambda x: x["snr_improvement_db"] or 0, reverse=True)
    return calls


@app.get("/api/calls/{call_id}")
def get_call(call_id: str):
    """
    Return the full results.json for a single recording.
    """
    results_path = os.path.join(OUTPUT_DIR, call_id, "results.json")
    if not os.path.isfile(results_path):
        raise HTTPException(status_code=404, detail=f"No results for call_id: {call_id}")

    with open(results_path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    output_exists = os.path.isdir(OUTPUT_DIR)
    summary_exists = os.path.isfile(SUMMARY_PATH)
    n_recordings = len([
        d for d in os.listdir(OUTPUT_DIR)
        if os.path.isdir(os.path.join(OUTPUT_DIR, d))
    ]) if output_exists else 0

    return {
        "status": "ok",
        "output_dir": output_exists,
        "summary_json": summary_exists,
        "recordings_available": n_recordings,
    }
