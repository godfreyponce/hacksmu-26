# NL question → Gemini → answer (M2M auth)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import os
from db.store import get_db
from middleware.auth import verify_m2m_token

router = APIRouter()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))


class QueryRequest(BaseModel):
    text: str


@router.post("")
async def natural_language_query(req: QueryRequest, _: dict = Depends(verify_m2m_token)):
    """
    Process natural language query about elephant calls.
    Requires M2M authentication.
    """
    db = get_db()

    # Get call data for context
    calls = db.execute("""
        SELECT call_id_csv, call_type, date, location, confidence, fundamental_hz
        FROM calls
        ORDER BY date DESC
        LIMIT 50
    """).fetchall()

    calls_summary = "\n".join([
        f"- {c[0]}: {c[1] or 'unknown'} call on {c[3] or 'unknown date'} at {c[4] or 'unknown location'}, "
        f"confidence: {c[5] or 'N/A'}, fundamental: {c[6] or 'N/A'} Hz"
        for c in calls
    ])

    # Build prompt
    prompt = f"""You are EchoMap, an AI assistant for elephant vocalization research.
You have access to a database of {len(calls)} analyzed elephant calls.

Data summary:
{calls_summary}

User question: {req.text}

Provide a helpful, scientifically accurate response. If relevant data exists, cite specific calls.
Keep responses concise but informative."""

    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        return {"answer": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.post("/simple")
async def simple_query(req: QueryRequest):
    """Simple query endpoint without auth (limited functionality)."""
    db = get_db()

    total = db.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
    types = db.execute("SELECT DISTINCT call_type FROM calls WHERE call_type IS NOT NULL").fetchall()

    return {
        "answer": f"EchoMap contains {total} analyzed elephant calls. "
                  f"Call types include: {', '.join(t[0] for t in types if t[0])}. "
                  "For detailed queries, please authenticate with M2M token."
    }
