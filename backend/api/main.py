import os
import shutil
import threading
from pathlib import Path

import librosa
import soundfile as sf
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.protected import router as protected_router
from backend.api.routes.public import router as public_router
from backend.config import DATA_DIR, FRONTEND_ORIGIN
from backend.db.database import init_db, list_calls
from backend.pipeline.process_calls import process_call

app = FastAPI(title="EchoMap API", version="0.1.0")

AUTO_PROCESS_ON_STARTUP = os.getenv("AUTO_PROCESS_ON_STARTUP", "true").lower() == "true"


def _discover_call_ids() -> list[str]:
    """Find call IDs from data/hpss and data/recordings.

    If only raw recordings exist, mirror them into data/hpss as *_hpss.wav so the
    stage 2/3 pipeline can run without a separate pre-processing step.
    """
    hpss_dir = DATA_DIR / "hpss"
    recordings_dir = DATA_DIR / "recordings"

    hpss_dir.mkdir(parents=True, exist_ok=True)
    call_ids: set[str] = set()

    # Prefer already prepared HPSS files.
    for wav in hpss_dir.glob("*_hpss.wav"):
        call_ids.add(wav.stem[:-5])

    # Fallback: mirror raw recordings into HPSS filenames.
    if recordings_dir.exists():
        for wav in recordings_dir.glob("*.wav"):
            call_id = wav.stem.strip()
            if not call_id:
                continue
            target = hpss_dir / f"{call_id}_hpss.wav"
            if not target.exists():
                shutil.copy2(wav, target)
            call_ids.add(call_id)

    return sorted(call_ids)


def _default_call_window(call_id: str) -> tuple[float, float]:
    """Use a conservative pre-call noise region and full-file end for startup runs."""
    hpss_path = DATA_DIR / "hpss" / f"{call_id}_hpss.wav"
    if not hpss_path.exists():
        return (0.0, 0.0)

    try:
        duration = float(sf.info(str(hpss_path)).duration or 0.0)
    except Exception:
        duration = float(librosa.get_duration(path=str(hpss_path)) or 0.0)
    if duration <= 0:
        return (0.0, 0.0)

    # Keep at least 0.5s and at most 3s for noise estimation, but never past file end.
    start_sec = min(3.0, max(0.5, duration * 0.12))
    if start_sec >= duration:
        start_sec = max(0.0, duration * 0.1)

    return (start_sec, duration)


def _bootstrap_calls() -> None:
    if not AUTO_PROCESS_ON_STARTUP:
        return

    existing = {str(item.get("call_id_csv", "")) for item in list_calls()}
    call_ids = _discover_call_ids()
    if not call_ids:
        print("[startup] No recordings found in data/recordings or data/hpss")
        return

    pending = [call_id for call_id in call_ids if call_id not in existing]
    if not pending:
        print(f"[startup] Calls already processed ({len(existing)} total)")
        return

    print(f"[startup] Processing {len(pending)} recordings...")
    processed = 0
    for call_id in pending:
        try:
            start_sec, end_sec = _default_call_window(call_id)
            process_call(call_id=call_id, start_sec=start_sec, end_sec=end_sec)
            processed += 1
        except Exception as exc:
            print(f"[startup] Failed processing {call_id}: {exc}")

    print(f"[startup] Finished. Processed {processed}/{len(pending)} recordings")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    if AUTO_PROCESS_ON_STARTUP:
        threading.Thread(target=_bootstrap_calls, daemon=True).start()


app.include_router(public_router)
app.include_router(protected_router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
