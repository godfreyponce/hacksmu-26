from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.db.database import get_stats, list_calls
from backend.middleware.auth import require_m2m_token

router = APIRouter(tags=["protected"])


class QueryRequest(BaseModel):
    text: str


@router.post("/query")
def query(payload: QueryRequest, claims=Depends(require_m2m_token)):
    stats = get_stats()
    prompt = payload.text.lower()

    if "rumble" in prompt:
        value = stats["by_call_type"].get("rumble", 0)
        answer = f"Detected {value} rumble calls in the current dataset."
    elif "total" in prompt or "how many" in prompt:
        answer = f"There are {stats['total_calls']} processed calls in EchoMap."
    else:
        answer = "Query received. Ask about totals, confidence, or call-type counts for dataset insights."

    return {
        "answer": answer,
        "requested_by": claims.get("sub", "unknown"),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


@router.post("/report")
def report(claims=Depends(require_m2m_token)):
    calls = list_calls()
    stats = get_stats()

    top_harmonics = []
    for call in calls:
        for hz in call.get("harmonics", []):
            if isinstance(hz, (int, float)):
                top_harmonics.append(hz)

    return {
        "summary": stats,
        "harmonic_samples": top_harmonics[:20],
        "generated_for": claims.get("sub", "unknown"),
    }
