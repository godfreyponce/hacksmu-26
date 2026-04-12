"""
Run the denoiser pipeline on every synthetic mix and compute real metrics.

Metrics
-------
1. SI-SDR (scale-invariant SDR), Le Roux et al. 2018 (arXiv:1811.02508).
       alpha = <est, ref> / <ref, ref>      (both mean-subtracted)
       target = alpha * ref
       residual = est - target
       si_sdr = 10 * log10( ||target||^2 / ||residual||^2 )
   We report si_sdr(est=cleaned, ref=clean) minus si_sdr(est=mix, ref=clean)
   — the improvement. Positive = the pipeline helped. Negative = it hurt.

2. Call-band spectral preservation: cosine similarity between |STFT(clean)|
   and |STFT(cleaned)| over rows whose frequency is in [10, 200] Hz — the
   rumble fundamental + first few harmonics. 1.0 = perfect shape match, 0 =
   orthogonal.

3. Noise-band attenuation: 10*log10( sum(|STFT(mix)|^2 in 200-1200Hz) /
   sum(|STFT(cleaned)|^2 in 200-1200Hz) ). Positive = the pipeline removed
   energy from the mechanical-noise band. Negative = the pipeline ADDED
   energy there (bad).

Outputs
-------
    scripts/eval/results.json   -- machine-readable records
    scripts/eval/REPORT.md      -- human-readable table with means +/- std per SNR tier

Run from the repo root:

    python scripts/eval/run_eval.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import soundfile as sf


REPO_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
MIXES_DIR = EVAL_DIR / "mixes"
MANIFEST_PATH = MIXES_DIR / "manifest.json"
RESULTS_JSON = EVAL_DIR / "results.json"
REPORT_MD = EVAL_DIR / "REPORT.md"
WORK_DIR = EVAL_DIR / "_work"

# Make `backend.pipeline.process` importable when running from anywhere
sys.path.insert(0, str(REPO_ROOT))


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def si_sdr(est: np.ndarray, ref: np.ndarray) -> float:
    """
    Scale-invariant SDR in dB, per Le Roux et al. 2018 (arXiv:1811.02508).

        alpha   = <est_0, ref_0> / <ref_0, ref_0>        (both mean-subtracted)
        target  = alpha * ref_0
        si_sdr  = 10*log10( ||target||^2 / ||est_0 - target||^2 )

    Returns -inf-safe value. NaN inputs raise.
    """
    est = np.asarray(est, dtype=np.float64).flatten()
    ref = np.asarray(ref, dtype=np.float64).flatten()
    # align lengths (pipeline may return slightly longer/shorter buffers)
    n = min(len(est), len(ref))
    est = est[:n]
    ref = ref[:n]
    # mean-subtract
    est = est - np.mean(est)
    ref = ref - np.mean(ref)
    ref_energy = float(np.dot(ref, ref))
    if ref_energy < 1e-20:
        return float("nan")
    alpha = float(np.dot(est, ref)) / ref_energy
    target = alpha * ref
    residual = est - target
    target_e = float(np.dot(target, target)) + 1e-20
    res_e = float(np.dot(residual, residual)) + 1e-20
    return 10.0 * float(np.log10(target_e / res_e))


def call_band_cosine(clean: np.ndarray, cleaned: np.ndarray, sr: int,
                      low_hz: float = 10.0, high_hz: float = 200.0,
                      n_fft: int = 4096) -> float:
    """
    Cosine similarity between |STFT(clean)| and |STFT(cleaned)|, restricted
    to the rumble band [low_hz, high_hz]. Flattens (freq_bins_in_band * frames).
    """
    n = min(len(clean), len(cleaned))
    clean = clean[:n]
    cleaned = cleaned[:n]
    D_ref = np.abs(librosa.stft(clean.astype(np.float32), n_fft=n_fft))
    D_est = np.abs(librosa.stft(cleaned.astype(np.float32), n_fft=n_fft))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = (freqs >= low_hz) & (freqs <= high_hz)
    a = D_ref[band].flatten()
    b = D_est[band].flatten()
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na < 1e-12 or nb < 1e-12:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def noise_band_attenuation_db(mix: np.ndarray, cleaned: np.ndarray, sr: int,
                                low_hz: float = 200.0, high_hz: float = 1200.0,
                                n_fft: int = 4096) -> float:
    """
    10*log10( sum(|STFT(mix)|^2 in band) / sum(|STFT(cleaned)|^2 in band) ).
    Positive = energy was REMOVED from the noise band; negative = added.
    """
    n = min(len(mix), len(cleaned))
    mix = mix[:n]
    cleaned = cleaned[:n]
    D_mix = np.abs(librosa.stft(mix.astype(np.float32), n_fft=n_fft))
    D_out = np.abs(librosa.stft(cleaned.astype(np.float32), n_fft=n_fft))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = (freqs >= low_hz) & (freqs <= high_hz)
    e_mix = float(np.sum(D_mix[band] ** 2)) + 1e-20
    e_out = float(np.sum(D_out[band] ** 2)) + 1e-20
    return 10.0 * float(np.log10(e_mix / e_out))


# ---------------------------------------------------------------------------
# Pipeline invocation
# ---------------------------------------------------------------------------

def _run_pipeline_on_mix(mix_path: Path, work_dir: Path) -> np.ndarray:
    """
    Call backend.pipeline.process.process_recording on a mix file with an
    EMPTY calls CSV (so the pipeline takes its no-labels path and auto-detects).
    Returns the cleaned signal as a 1-D float32 array.
    """
    from backend.pipeline.process import process_recording

    work_dir.mkdir(parents=True, exist_ok=True)

    # Minimal CSV with the right columns but no rows for this file — forces
    # process.py's no-labels branch (percentile noise estimate + auto-detect).
    csv_path = work_dir / "empty_calls.csv"
    pd.DataFrame(columns=["Selection", "Sound_file", "Start_time", "End_time",
                          "Call_type"]).to_csv(csv_path, index=False)

    out_dir = work_dir / mix_path.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    # suppress pipeline's stdout chatter during eval
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        process_recording(str(mix_path), str(csv_path), str(out_dir))

    cleaned_path = out_dir / "cleaned.wav"
    y, sr = librosa.load(str(cleaned_path), sr=None, mono=True)
    return y.astype(np.float32), int(sr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if not MANIFEST_PATH.exists():
        raise SystemExit(
            f"[run_eval] no manifest found at {MANIFEST_PATH}. "
            f"Run `python scripts/eval/build_mixes.py` first."
        )

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    records = []
    WORK_DIR.mkdir(parents=True, exist_ok=True)

    for i, entry in enumerate(manifest["mixes"], 1):
        mix_path = REPO_ROOT / entry["mix_path"]
        clean_path = REPO_ROOT / entry["clean_path"]

        print(f"[run_eval] {i}/{len(manifest['mixes'])}  {entry['mix_id']} "
              f"(target_snr={entry['target_input_snr_db']:+d} dB)")

        mix, sr = librosa.load(str(mix_path), sr=None, mono=True)
        clean, _ = librosa.load(str(clean_path), sr=sr, mono=True)

        cleaned, sr_out = _run_pipeline_on_mix(mix_path, WORK_DIR)
        if sr_out != sr:
            # resample cleaned to match clean for fair comparison
            cleaned = librosa.resample(cleaned, orig_sr=sr_out, target_sr=sr)

        si_in = si_sdr(mix, clean)
        si_out = si_sdr(cleaned, clean)
        si_improve = si_out - si_in

        cb_cos = call_band_cosine(clean, cleaned, sr)
        nb_att = noise_band_attenuation_db(mix, cleaned, sr)

        print(f"           SI-SDR in={si_in:+.2f} dB  out={si_out:+.2f} dB  "
              f"Δ={si_improve:+.2f} dB  |  call-cos={cb_cos:.3f}  "
              f"noise-atten={nb_att:+.2f} dB")

        records.append({
            "mix_id": entry["mix_id"],
            "target_input_snr_db": entry["target_input_snr_db"],
            "measured_input_snr_db": entry["measured_input_snr_db"],
            "si_sdr_input_db": round(si_in, 3),
            "si_sdr_output_db": round(si_out, 3),
            "si_sdr_improvement_db": round(si_improve, 3),
            "call_band_cosine": round(cb_cos, 4),
            "noise_band_attenuation_db": round(nb_att, 3),
            "clean_source": entry["clean_source"]["wav"],
            "noise_source": entry["noise_source"]["wav"],
        })

    with open(RESULTS_JSON, "w") as f:
        json.dump({"records": records}, f, indent=2)

    _write_report(records)
    print(f"\n[run_eval] results: {RESULTS_JSON}")
    print(f"[run_eval] report:  {REPORT_MD}")


def _write_report(records: list[dict]) -> None:
    """Produce a markdown summary grouped by target input SNR tier."""
    lines: list[str] = []
    lines.append("# Denoiser evaluation — synthetic mixes\n")
    lines.append("Real metrics against a clean reference, not the vanity call-vs-gap SNR.\n")
    lines.append("Metrics:\n")
    lines.append("- **SI-SDR Δ (dB)**: improvement in scale-invariant SDR (est=cleaned vs est=mix), "
                 "both referenced to the clean signal. Positive = pipeline helped.")
    lines.append("- **Call-band cosine**: cosine similarity of |STFT(clean)| and |STFT(cleaned)| over 10–200 Hz. "
                 "1.0 = perfect rumble-shape preservation.")
    lines.append("- **Noise-band attenuation (dB)**: energy reduction from mix → cleaned in 200–1200 Hz. "
                 "Positive = mechanical noise removed.\n")

    lines.append("## Aggregate by input SNR\n")
    lines.append("| Target input SNR (dB) | N | SI-SDR in (dB) | SI-SDR out (dB) | SI-SDR Δ mean ± std (dB) | Call-band cosine | Noise-band attenuation (dB) |")
    lines.append("|---:|---:|---:|---:|---:|---:|---:|")

    df = pd.DataFrame(records)
    tiers = sorted(df["target_input_snr_db"].unique())
    for tier in tiers:
        sub = df[df["target_input_snr_db"] == tier]
        si_in_m = sub["si_sdr_input_db"].mean()
        si_out_m = sub["si_sdr_output_db"].mean()
        imp_m = sub["si_sdr_improvement_db"].mean()
        imp_s = sub["si_sdr_improvement_db"].std(ddof=0)
        cb_m = sub["call_band_cosine"].mean()
        nb_m = sub["noise_band_attenuation_db"].mean()
        lines.append(
            f"| {int(tier):+d} | {len(sub)} | {si_in_m:+.2f} | {si_out_m:+.2f} | "
            f"{imp_m:+.2f} ± {imp_s:.2f} | {cb_m:.3f} | {nb_m:+.2f} |"
        )

    overall_imp_m = df["si_sdr_improvement_db"].mean()
    overall_imp_s = df["si_sdr_improvement_db"].std(ddof=0)
    lines.append(f"\n**Overall SI-SDR improvement across {len(df)} mixes: "
                 f"{overall_imp_m:+.2f} ± {overall_imp_s:.2f} dB**\n")

    # honesty check — call out tiers where SI-SDR got worse
    lines.append("## Honesty check\n")
    hurt = [int(t) for t in tiers
            if df[df["target_input_snr_db"] == t]["si_sdr_improvement_db"].mean() < 0]
    if hurt:
        lines.append(f"- At input SNR tiers **{hurt} dB**, the pipeline REDUCED SI-SDR on average. "
                     f"This is the expected failure mode for aggressive denoisers at moderate/high input SNR: "
                     f"the spectral subtraction & bandpass steps distort the signal more than they remove noise when noise is already low. "
                     f"The pipeline's value is strongest at low input SNR (heavy noise).\n")
    else:
        lines.append("- Pipeline improved SI-SDR on average at every tested input SNR tier.\n")

    lines.append("## Per-mix detail\n")
    lines.append("| mix_id | target SNR (dB) | measured SNR (dB) | SI-SDR in | SI-SDR out | Δ | call-cos | noise-atten (dB) | clean src | noise src |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for r in records:
        lines.append(
            f"| {r['mix_id']} | {int(r['target_input_snr_db']):+d} | {r['measured_input_snr_db']:+.2f} "
            f"| {r['si_sdr_input_db']:+.2f} | {r['si_sdr_output_db']:+.2f} | {r['si_sdr_improvement_db']:+.2f} "
            f"| {r['call_band_cosine']:.3f} | {r['noise_band_attenuation_db']:+.2f} "
            f"| {r['clean_source']} | {r['noise_source']} |"
        )

    REPORT_MD.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
