import json
import re
from pathlib import Path

import google.generativeai as genai

from backend.config import GEMINI_API_KEY, GEMINI_MODEL

PROMPT = """This is a linear-scale spectrogram of an elephant vocalization, showing frequency
0–1200 Hz on the Y axis and time on the X axis. The call has been noise-cleaned
using HPSS and spectral gating. Analyze the visible harmonic band structure and
return only a JSON object with these fields — no explanation, no markdown:
{
call_type: 'rumble' | 'roar' | 'trumpet' | 'contact' | 'unknown',
fundamental_hz: ,
num_callers: <1 or 2>,
harmonics_visible: [],
confidence: <0.0 to 1.0>,
notes: ''
}"""



def _default_result() -> dict:
    return {
        "call_type": "unknown",
        "fundamental_hz": None,
        "num_callers": 1,
        "harmonics_visible": [],
        "confidence": 0.0,
        "notes": "Gemini unavailable or parse failure",
    }



def _extract_json(text: str) -> dict:
    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        raise ValueError("No JSON object found in Gemini output")
    payload = match.group(0)

    payload = re.sub(r"([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)", r'\1"\2"\3', payload)
    payload = payload.replace("'", '"')
    return json.loads(payload)



def classify_spectrogram(clean_spectrogram_path: Path) -> dict:
    if not GEMINI_API_KEY:
        return _default_result()

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)

    with clean_spectrogram_path.open("rb") as image_file:
        image_bytes = image_file.read()

    response = model.generate_content(
        [
            {"mime_type": "image/png", "data": image_bytes},
            PROMPT,
        ]
    )

    result = _default_result()
    try:
        data = _extract_json(response.text or "")
        result.update(
            {
                "call_type": data.get("call_type", "unknown"),
                "fundamental_hz": data.get("fundamental_hz"),
                "num_callers": int(data.get("num_callers", 1) or 1),
                "harmonics_visible": data.get("harmonics_visible", []),
                "confidence": float(data.get("confidence", 0.0) or 0.0),
                "notes": data.get("notes", ""),
            }
        )
    except Exception:
        return result

    return result
