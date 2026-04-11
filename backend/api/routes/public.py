from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.db.database import get_call, get_stats, list_calls

router = APIRouter(tags=["public"])
VALID_STAGES = {"hpss", "gated", "clean"}


@router.get("/calls")
def calls() -> list[dict]:
    return list_calls()


@router.get("/calls/{id}")
def call(id: int) -> dict:
    item = get_call(id)
    if not item:
        raise HTTPException(status_code=404, detail="Call not found")
    return item


@router.get("/calls/{id}/audio/{stage}")
def call_audio(id: int, stage: str):
    if stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail="stage must be hpss|gated|clean")

    item = get_call(id)
    if not item:
        raise HTTPException(status_code=404, detail="Call not found")

    path_key = f"{stage}_path" if stage != "clean" else "clean_path"
    file_path = Path(item[path_key])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    return FileResponse(file_path, media_type="audio/wav")


@router.get("/calls/{id}/spectrogram/{stage}")
def call_spectrogram(id: int, stage: str):
    if stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail="stage must be hpss|gated|clean")

    item = get_call(id)
    if not item:
        raise HTTPException(status_code=404, detail="Call not found")

    path_key = f"spec_{stage}" if stage != "clean" else "spec_clean"
    file_path = Path(item[path_key])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Spectrogram not found")
    return FileResponse(file_path, media_type="image/png")


@router.get("/stats")
def stats() -> dict:
    return get_stats()
