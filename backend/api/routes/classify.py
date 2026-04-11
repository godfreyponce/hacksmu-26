# Trigger Gemini Vision classification

from fastapi import APIRouter, HTTPException, Depends
from pathlib import Path
from pipeline.classifier import classify_spectrogram
from middleware.auth import verify_m2m_token

router = APIRouter()
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"


@router.post("/{call_id}")
async def classify_call(call_id: str):
    """Classify a call using Gemini Vision on its spectrogram."""
    spec_path = DATA_DIR / "spectrograms" / f"{call_id}_clean.png"
    if not spec_path.exists():
        raise HTTPException(status_code=404, detail="Spectrogram not found")

    result = await classify_spectrogram(str(spec_path))
    return result


@router.post("/batch")
async def classify_batch(call_ids: list[str], _: dict = Depends(verify_m2m_token)):
    """Classify multiple calls (M2M auth required)."""
    results = {}
    for call_id in call_ids:
        spec_path = DATA_DIR / "spectrograms" / f"{call_id}_clean.png"
        if spec_path.exists():
            results[call_id] = await classify_spectrogram(str(spec_path))
        else:
            results[call_id] = {"error": "Spectrogram not found"}
    return results
