from pathlib import Path
from typing import Iterable

from backend.config import DATA_DIR
from backend.db.database import upsert_call
from backend.pipeline.classifier import classify_spectrogram
from backend.pipeline.denoiser import stage2_spectral_gate, stage3_residual_cleanup
from backend.pipeline.spectrogram import generate_spectrogram



def process_call(call_id: str, start_sec: float, end_sec: float) -> int:
    hpss_path = DATA_DIR / "hpss" / f"{call_id}_hpss.wav"
    if not hpss_path.exists():
        raise FileNotFoundError(f"HPSS file not found: {hpss_path}")

    gated_path = stage2_spectral_gate(hpss_path, call_id, start_sec, DATA_DIR / "gated")
    clean_path = stage3_residual_cleanup(gated_path, call_id, DATA_DIR / "cleaned")

    spec_hpss = generate_spectrogram(hpss_path, call_id, "hpss", DATA_DIR / "spectrograms")
    spec_gated = generate_spectrogram(gated_path, call_id, "gated", DATA_DIR / "spectrograms")
    spec_clean = generate_spectrogram(clean_path, call_id, "clean", DATA_DIR / "spectrograms")

    prediction = classify_spectrogram(spec_clean)

    record = {
        "call_id_csv": call_id,
        "start_sec": start_sec,
        "end_sec": end_sec,
        "hpss_path": str(hpss_path),
        "gated_path": str(gated_path),
        "clean_path": str(clean_path),
        "spec_hpss": str(spec_hpss),
        "spec_gated": str(spec_gated),
        "spec_clean": str(spec_clean),
        "call_type": prediction["call_type"],
        "fundamental_hz": prediction["fundamental_hz"],
        "num_callers": prediction["num_callers"],
        "harmonics_visible": prediction["harmonics_visible"],
        "confidence": prediction["confidence"],
        "notes": prediction["notes"],
    }
    return upsert_call(record)



def process_batch(metadata: Iterable[dict]) -> list[int]:
    processed_ids = []
    for item in metadata:
        processed_ids.append(
            process_call(
                call_id=item["call_id"],
                start_sec=float(item["start_sec"]),
                end_sec=float(item["end_sec"]),
            )
        )
    return processed_ids
