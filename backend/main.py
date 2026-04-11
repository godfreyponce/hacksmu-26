from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from api.routes import audio, classify, query, report
from pipeline.loader import load_calls_csv
from pipeline.slicer import slice_all_clips
from pipeline.denoiser import denoise_all_clips
from pipeline.spectrogram import generate_all_spectrograms
from db.store import init_db

DATA_DIR = Path(__file__).parent.parent / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run pipeline on first start if data exists
    init_db()

    csv_path = DATA_DIR / "calls.csv"
    if csv_path.exists():
        print("Loading calls.csv...")
        load_calls_csv(str(csv_path))

        raw_dir = DATA_DIR / "raw"
        if raw_dir.exists() and any(raw_dir.glob("*.wav")):
            print("Slicing clips...")
            slice_all_clips(str(raw_dir), str(DATA_DIR / "clips"))

            print("Denoising clips (HPSS + spectral gate)...")
            denoise_all_clips(str(DATA_DIR / "clips"), str(DATA_DIR / "cleaned"))

            print("Generating spectrograms...")
            generate_all_spectrograms(
                str(DATA_DIR / "clips"),
                str(DATA_DIR / "cleaned"),
                str(DATA_DIR / "spectrograms")
            )
            print("Pipeline complete.")

    yield


app = FastAPI(title="EchoMap API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static directories
for dir_name in ["clips", "cleaned", "spectrograms"]:
    dir_path = DATA_DIR / dir_name
    dir_path.mkdir(parents=True, exist_ok=True)
    app.mount(f"/{dir_name}", StaticFiles(directory=str(dir_path)), name=dir_name)

# Include routers
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])
app.include_router(classify.router, prefix="/api/classify", tags=["classify"])
app.include_router(query.router, prefix="/api/query", tags=["query"])
app.include_router(report.router, prefix="/api/report", tags=["report"])


@app.get("/")
def root():
    return {"message": "EchoMap API", "status": "running"}


@app.get("/calls")
def list_calls():
    from db.store import get_db
    db = get_db()
    rows = db.execute("SELECT * FROM calls ORDER BY id").fetchall()
    columns = ["id", "call_id_csv", "file", "start_time", "end_time", "call_type",
               "caller_id", "date", "location", "lat", "lon", "notes",
               "clip_path", "spectrogram_path", "classification", "confidence",
               "fundamental_hz", "harmonics"]
    return [dict(zip(columns, row)) for row in rows]


@app.get("/calls/{call_id}")
def get_call(call_id: int):
    from db.store import get_db
    db = get_db()
    row = db.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
    if not row:
        return {"error": "Call not found"}
    columns = ["id", "call_id_csv", "file", "start_time", "end_time", "call_type",
               "caller_id", "date", "location", "lat", "lon", "notes",
               "clip_path", "spectrogram_path", "classification", "confidence",
               "fundamental_hz", "harmonics"]
    return dict(zip(columns, row))


@app.get("/calls/{call_id}/audio/{stage}")
def get_call_audio(call_id: int, stage: str):
    from fastapi.responses import FileResponse
    from db.store import get_db
    db = get_db()
    row = db.execute("SELECT call_id_csv FROM calls WHERE id = ?", (call_id,)).fetchone()
    if not row:
        return {"error": "Call not found"}

    call_id_csv = row[0]
    if stage == "hpss":
        path = DATA_DIR / "clips" / f"{call_id_csv}_hpss.wav"
    elif stage == "gated":
        path = DATA_DIR / "cleaned" / f"{call_id_csv}_gated.wav"
    else:
        path = DATA_DIR / "cleaned" / f"{call_id_csv}_clean.wav"

    if not path.exists():
        # Fallback
        path = DATA_DIR / "clips" / f"{call_id_csv}_noisy.wav"

    if path.exists():
        return FileResponse(path, media_type="audio/wav")
    return {"error": "Audio not found"}


@app.get("/calls/{call_id}/spectrogram/{stage}")
def get_call_spectrogram(call_id: int, stage: str):
    from fastapi.responses import FileResponse
    from db.store import get_db
    db = get_db()
    row = db.execute("SELECT call_id_csv FROM calls WHERE id = ?", (call_id,)).fetchone()
    if not row:
        return {"error": "Call not found"}

    call_id_csv = row[0]
    path = DATA_DIR / "spectrograms" / f"{call_id_csv}_{stage}.png"

    if path.exists():
        return FileResponse(path, media_type="image/png")
    return {"error": "Spectrogram not found"}


@app.get("/stats")
def get_stats():
    from db.store import get_db
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
    avg_conf = db.execute("SELECT AVG(confidence) FROM calls WHERE confidence IS NOT NULL").fetchone()[0]
    by_type = db.execute("SELECT call_type, COUNT(*) FROM calls GROUP BY call_type").fetchall()
    return {
        "total_calls": total,
        "avg_confidence": avg_conf or 0,
        "by_call_type": {t: c for t, c in by_type if t}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
