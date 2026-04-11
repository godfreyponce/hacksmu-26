# Serve clips + spectrograms

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


@router.get("/clips")
async def list_clips():
    """List all available clips."""
    clips_dir = DATA_DIR / "clips"
    if not clips_dir.exists():
        return {"clips": []}
    clips = [f.stem for f in clips_dir.glob("*.wav")]
    return {"clips": sorted(clips)}


@router.get("/clips/{clip_id}")
async def get_clip(clip_id: str):
    """Serve an audio clip by ID."""
    clip_path = DATA_DIR / "clips" / f"{clip_id}.wav"
    if not clip_path.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(clip_path, media_type="audio/wav")


@router.get("/cleaned/{clip_id}")
async def get_cleaned_clip(clip_id: str):
    """Serve a cleaned/denoised audio clip."""
    clean_path = DATA_DIR / "cleaned" / f"{clip_id}_clean.wav"
    if not clean_path.exists():
        raise HTTPException(status_code=404, detail="Cleaned clip not found")
    return FileResponse(clean_path, media_type="audio/wav")


@router.get("/spectrograms/{clip_id}/{stage}")
async def get_spectrogram(clip_id: str, stage: str = "clean"):
    """Serve spectrogram PNG for a clip."""
    spec_path = DATA_DIR / "spectrograms" / f"{clip_id}_{stage}.png"
    if not spec_path.exists():
        raise HTTPException(status_code=404, detail=f"Spectrogram ({stage}) not found")
    return FileResponse(spec_path, media_type="image/png")
