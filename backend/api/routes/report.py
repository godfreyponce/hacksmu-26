# Field report + ElevenLabs TTS (M2M auth)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
import httpx
import os
from db.store import get_db
from middleware.auth import verify_m2m_token

router = APIRouter()

genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")


class ReportRequest(BaseModel):
    date: str | None = None
    location: str | None = None
    include_audio: bool = False


@router.post("/generate")
async def generate_report(req: ReportRequest, _: dict = Depends(verify_m2m_token)):
    """Generate a narrated field report based on recorded calls."""
    db = get_db()

    # Build query
    query = "SELECT * FROM calls WHERE 1=1"
    params = []
    if req.date:
        query += " AND date = ?"
        params.append(req.date)
    if req.location:
        query += " AND location LIKE ?"
        params.append(f"%{req.location}%")

    calls = db.execute(query, params).fetchall()

    if not calls:
        return {"report": "No calls found matching the criteria.", "call_count": 0}

    # Summarize for Gemini
    calls_text = "\n".join([
        f"Call {c[1]}: type={c[5]}, date={c[7]}, location={c[8]}, confidence={c[15]}, fundamental={c[16]}Hz"
        for c in calls
    ])

    prompt = f"""You are a wildlife researcher writing a field report about elephant vocalizations.
Generate a professional, engaging narrative report based on this data:

{calls_text}

Include:
- Executive summary (2-3 sentences)
- Call type distribution and notable patterns
- Acoustic characteristics observed (frequency ranges, harmonics)
- Behavioral implications
- Recommendations for further study

Write in a scientific but accessible style. Use specific data points."""

    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        report_text = response.text

        result = {
            "report": report_text,
            "call_count": len(calls),
            "audio_url": None
        }

        # Generate TTS if requested
        if req.include_audio and ELEVENLABS_API_KEY:
            audio_url = await generate_tts(report_text[:2000])  # Limit length
            result["audio_url"] = audio_url

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


async def generate_tts(text: str) -> str | None:
    """Generate TTS audio using ElevenLabs."""
    if not ELEVENLABS_API_KEY:
        return None

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}",
                headers={
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                },
                json={
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                },
                timeout=30.0
            )

            if response.status_code == 200:
                # Save audio and return URL
                from pathlib import Path
                import uuid
                audio_dir = Path(__file__).parent.parent.parent.parent / "data" / "reports"
                audio_dir.mkdir(exist_ok=True)
                filename = f"report_{uuid.uuid4().hex[:8]}.mp3"
                audio_path = audio_dir / filename
                audio_path.write_bytes(response.content)
                return f"/reports/{filename}"

    except Exception as e:
        print(f"TTS generation failed: {e}")

    return None


@router.get("/summary")
async def get_summary():
    """Get quick summary statistics."""
    db = get_db()

    total = db.execute("SELECT COUNT(*) FROM calls").fetchone()[0]
    by_type = db.execute(
        "SELECT call_type, COUNT(*) as count FROM calls WHERE call_type IS NOT NULL GROUP BY call_type"
    ).fetchall()
    avg_confidence = db.execute(
        "SELECT AVG(confidence) FROM calls WHERE confidence IS NOT NULL"
    ).fetchone()[0]

    return {
        "total_calls": total,
        "by_type": {row[0]: row[1] for row in by_type},
        "avg_confidence": round(avg_confidence, 2) if avg_confidence else None
    }
