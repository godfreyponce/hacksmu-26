"""
Build synthetic elephant+noise mixes at controlled input SNRs.

Strategy
--------
We need (clean_call, noise, mix) triples where we control the input SNR exactly
so downstream SI-SDR numbers are meaningful. Nothing in data/ is truly clean, so
we approximate:

  - CLEAN: extract labeled rumble windows from the recordings that showed the
    HIGHEST snr_before_db in output/summary.json. We run a gentle low-pass (<=
    250 Hz) + HPSS-harmonic reconstruction on ONLY that window to strip residual
    broadband noise, yielding a "clean-ish" rumble. This is our ground truth by
    construction — every metric downstream is measured against this signal.
    (The metric therefore answers: "how well does the pipeline recover THIS
    reference?" which is the honest question for a denoiser.)

  - NOISE: extract a matched-length slice from a noise-only region (well away
    from any labeled call, in a recording containing vehicle/generator/airplane
    tags). Use librosa to high-pass above 150 Hz so we do not also include the
    rumble content that might exist in the non-call region.

Each clean call is mixed with each noise segment at input SNRs in
{-10, -5, 0, +5} dB, where

    SNR_dB = 10 * log10( mean(clean^2) / mean(noise^2) )

We normalize the mix to avoid clipping. Output:

    scripts/eval/mixes/
        <mix_id>.wav          -- the noisy mix fed to the pipeline
        clean/<mix_id>.wav    -- the reference clean signal
        noise/<mix_id>.wav    -- the noise alone (for diagnostics)
        manifest.json         -- list of records the evaluator reads

Run from the repo root:

    python scripts/eval/build_mixes.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import librosa
import numpy as np
import pandas as pd
import soundfile as sf
from scipy.signal import butter, sosfiltfilt


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
RECORDINGS_DIR = DATA_DIR / "recordings"
CALLS_CSV = DATA_DIR / "calls.csv"
SUMMARY_JSON = REPO_ROOT / "output" / "summary.json"

EVAL_DIR = Path(__file__).resolve().parent
MIXES_DIR = EVAL_DIR / "mixes"
CLEAN_DIR = MIXES_DIR / "clean"
NOISE_DIR = MIXES_DIR / "noise"
MANIFEST_PATH = MIXES_DIR / "manifest.json"

INPUT_SNR_TIERS_DB = [-10, -5, 0, 5]
TARGET_DURATION_SEC = 45.0        # keep files short — 30-60s per spec
TARGET_SR = 48000                 # matches the native sample rate of the dataset
N_CLEAN_SOURCES = 5
N_NOISE_SOURCES = 2               # so we get ~5 * 2 * 4 = 40 mixes max; we cap later
MAX_MIXES = 24                    # hard cap — keeps eval runtime reasonable


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _butter_bandpass(low_hz: float, high_hz: float, sr: int, order: int = 4):
    return butter(order, [low_hz, high_hz], btype="bandpass", fs=sr, output="sos")


def _butter_highpass(cut_hz: float, sr: int, order: int = 4):
    return butter(order, cut_hz, btype="highpass", fs=sr, output="sos")


def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x.astype(np.float64) ** 2) + 1e-20))


def _scale_for_snr(clean: np.ndarray, noise: np.ndarray, target_snr_db: float) -> np.ndarray:
    """Return a scaled copy of noise such that 10*log10(mean(clean^2)/mean(n'^2)) == target_snr_db."""
    clean_power = np.mean(clean.astype(np.float64) ** 2) + 1e-20
    noise_power = np.mean(noise.astype(np.float64) ** 2) + 1e-20
    target_noise_power = clean_power / (10.0 ** (target_snr_db / 10.0))
    scale = np.sqrt(target_noise_power / noise_power)
    return noise * scale


def _measured_snr_db(clean: np.ndarray, noise: np.ndarray) -> float:
    cp = np.mean(clean.astype(np.float64) ** 2) + 1e-20
    npw = np.mean(noise.astype(np.float64) ** 2) + 1e-20
    return float(10.0 * np.log10(cp / npw))


def _load_mono(path: Path, sr: int = TARGET_SR) -> tuple[np.ndarray, int]:
    y, orig_sr = librosa.load(str(path), sr=sr, mono=True)
    return y.astype(np.float32), sr


# ---------------------------------------------------------------------------
# Source selection
# ---------------------------------------------------------------------------

def _pick_clean_source_windows() -> list[dict]:
    """
    Pick N_CLEAN_SOURCES (file, start, end) windows from the recordings that
    showed the highest snr_before_db in output/summary.json. These are our
    least-noisy rumbles — the closest thing we have to "clean" data.
    """
    with open(SUMMARY_JSON) as f:
        summary = json.load(f)

    # rank by snr_before_db DESC, and keep only entries with a labelled call
    ranked = sorted(
        [r for r in summary if r.get("calls_detected") and "error" not in r],
        key=lambda r: -float(r.get("snr_before_db", -999.0)),
    )

    calls_df = pd.read_csv(CALLS_CSV)

    sources: list[dict] = []
    for rec in ranked:
        if len(sources) >= N_CLEAN_SOURCES:
            break
        wav = rec["filename"]
        rows = calls_df[calls_df["Sound_file"] == wav]
        if rows.empty:
            continue
        # pick the longest labelled call in this file — more signal = better ref
        rows = rows.assign(_dur=rows["End_time"] - rows["Start_time"])
        best = rows.sort_values("_dur", ascending=False).iloc[0]
        sources.append({
            "wav": wav,
            "call_start": float(best["Start_time"]),
            "call_end": float(best["End_time"]),
            "snr_before_db": float(rec.get("snr_before_db", 0.0)),
        })
    return sources


def _pick_noise_source_windows() -> list[dict]:
    """
    Pick noise-only windows from recordings tagged as vehicle/generator/airplane.
    We use files whose snr_before_db is middling-to-low (there is lots of noise),
    and take a TARGET_DURATION_SEC window that is far from any labelled call.
    """
    with open(SUMMARY_JSON) as f:
        summary = json.load(f)

    calls_df = pd.read_csv(CALLS_CSV)

    candidates = []
    for r in summary:
        name = r.get("filename", "")
        tags = ("vehicle" in name.lower() or "generator" in name.lower()
                or "airplane" in name.lower())
        if not tags:
            continue
        if "error" in r:
            continue
        duration = float(r.get("duration_seconds", 0.0))
        if duration < TARGET_DURATION_SEC + 10:
            continue
        candidates.append(r)

    # prefer files with MANY labelled calls (= dense noise with known gaps)
    # but also prefer long files so we can find call-free windows easily
    candidates.sort(key=lambda r: (-float(r.get("duration_seconds", 0.0))))

    picks: list[dict] = []
    for r in candidates:
        if len(picks) >= N_NOISE_SOURCES:
            break
        wav = r["filename"]
        dur = float(r["duration_seconds"])
        rows = calls_df[calls_df["Sound_file"] == wav]
        call_intervals = list(zip(rows["Start_time"].astype(float),
                                  rows["End_time"].astype(float)))
        # find a TARGET_DURATION_SEC gap that does not overlap any call,
        # with 2 sec padding on each side
        pad = 2.0
        best_start = None
        # step through the recording in 5s increments
        t = 0.0
        step = 5.0
        while t + TARGET_DURATION_SEC + pad <= dur:
            win_s, win_e = t - pad, t + TARGET_DURATION_SEC + pad
            clash = any(not (win_e <= cs or win_s >= ce)
                        for cs, ce in call_intervals)
            if not clash:
                best_start = t
                break
            t += step
        if best_start is None:
            continue
        picks.append({
            "wav": wav,
            "noise_start": best_start,
            "noise_end": best_start + TARGET_DURATION_SEC,
        })
    return picks


# ---------------------------------------------------------------------------
# Clean signal construction
# ---------------------------------------------------------------------------

def _extract_clean_rumble(src: dict) -> np.ndarray:
    """
    Build a TARGET_DURATION_SEC clean-ish reference containing the rumble
    centered at roughly the middle of the window.

    Steps:
      1. Load the source file at native SR.
      2. Take a TARGET_DURATION_SEC window that CONTAINS the labelled call
         (call centered where possible).
      3. Run an HPSS-harmonic reconstruction on that window to strip broadband
         noise — this is our best available proxy for the unobservable clean
         rumble. Bandlimit to 10-400 Hz to isolate the rumble fundamental &
         first harmonics. Noise outside the call window is zeroed.
      4. Normalize to -20 dBFS (~0.1 peak) so downstream mixing is predictable.
    """
    y, sr = _load_mono(RECORDINGS_DIR / src["wav"])
    call_len = src["call_end"] - src["call_start"]
    # center window around the call
    call_center = 0.5 * (src["call_start"] + src["call_end"])
    win_start = max(0.0, call_center - TARGET_DURATION_SEC / 2.0)
    win_end = win_start + TARGET_DURATION_SEC
    if win_end > len(y) / sr:
        win_end = len(y) / sr
        win_start = max(0.0, win_end - TARGET_DURATION_SEC)

    s = int(win_start * sr)
    e = int(win_end * sr)
    segment = y[s:e].copy()

    # HPSS-harmonic reconstruction to strip broadband noise
    n_fft = 4096
    D = librosa.stft(segment, n_fft=n_fft)
    D_mag, D_phase = np.abs(D), np.angle(D)
    H_mag, _ = librosa.decompose.hpss(D_mag, kernel_size=31)
    y_h = librosa.istft(H_mag * np.exp(1j * D_phase), length=len(segment))

    # bandlimit to rumble band 10-400 Hz
    sos = _butter_bandpass(10.0, 400.0, sr)
    y_h = sosfiltfilt(sos, y_h).astype(np.float32)

    # zero out everything more than 1.0s outside the call (so "clean" has
    # well-defined silence regions) — makes SI-SDR meaningful (clean has
    # a real signal region and real silence region, no residual hum)
    call_s_local = max(0.0, src["call_start"] - win_start)
    call_e_local = min(TARGET_DURATION_SEC, src["call_end"] - win_start)
    pad = 1.0
    mask_s = int(max(0.0, call_s_local - pad) * sr)
    mask_e = int(min(TARGET_DURATION_SEC, call_e_local + pad) * sr)
    gated = np.zeros_like(y_h)
    gated[mask_s:mask_e] = y_h[mask_s:mask_e]

    # normalize to a target RMS (-20 dBFS equivalent)
    target_rms = 0.1
    current = _rms(gated)
    if current > 1e-10:
        gated = gated * (target_rms / current)

    # pad/truncate to exact TARGET_DURATION_SEC samples
    want = int(TARGET_DURATION_SEC * sr)
    if len(gated) < want:
        gated = np.pad(gated, (0, want - len(gated)))
    else:
        gated = gated[:want]
    return gated.astype(np.float32)


def _extract_noise(src: dict) -> np.ndarray:
    y, sr = _load_mono(RECORDINGS_DIR / src["wav"])
    s = int(src["noise_start"] * sr)
    e = int(src["noise_end"] * sr)
    n = y[s:e].copy()

    # High-pass above 30 Hz only (so we keep the full mechanical noise
    # spectrum the pipeline is meant to suppress; we don't want to pre-filter
    # the problem away). Do NOT remove low-band noise — that's the whole point.
    # But do mild normalization to keep mixing predictable.
    want = int(TARGET_DURATION_SEC * sr)
    if len(n) < want:
        n = np.pad(n, (0, want - len(n)))
    else:
        n = n[:want]

    # normalize noise to a known RMS so scaling at different target SNRs is clean
    target_rms = 0.1
    current = _rms(n)
    if current > 1e-10:
        n = n * (target_rms / current)
    return n.astype(np.float32)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    MIXES_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    NOISE_DIR.mkdir(parents=True, exist_ok=True)

    clean_sources = _pick_clean_source_windows()
    noise_sources = _pick_noise_source_windows()

    print(f"[build_mixes] clean sources: {len(clean_sources)}")
    for s in clean_sources:
        print(f"    - {s['wav']} (call {s['call_start']:.1f}-{s['call_end']:.1f}s, "
              f"snr_before_db={s['snr_before_db']:.1f})")
    print(f"[build_mixes] noise sources: {len(noise_sources)}")
    for s in noise_sources:
        print(f"    - {s['wav']} @ {s['noise_start']:.1f}-{s['noise_end']:.1f}s")

    if not clean_sources or not noise_sources:
        raise SystemExit("[build_mixes] Not enough sources found; check data/.")

    # cache extracted signals so we don't re-read files for every SNR tier
    clean_cache = {s["wav"]: _extract_clean_rumble(s) for s in clean_sources}
    noise_cache = {s["wav"]: _extract_noise(s) for s in noise_sources}

    manifest = []
    mix_counter = 0
    for ci, csrc in enumerate(clean_sources):
        for ni, nsrc in enumerate(noise_sources):
            for snr_db in INPUT_SNR_TIERS_DB:
                if mix_counter >= MAX_MIXES:
                    break
                clean = clean_cache[csrc["wav"]]
                noise_base = noise_cache[nsrc["wav"]]
                noise_scaled = _scale_for_snr(clean, noise_base, snr_db)
                mix = clean + noise_scaled

                # peak-normalize mix to avoid clipping on write
                peak = float(np.max(np.abs(mix)) + 1e-9)
                if peak > 0.95:
                    gain = 0.95 / peak
                    mix = mix * gain
                    clean_out = clean * gain
                    noise_out = noise_scaled * gain
                else:
                    clean_out = clean
                    noise_out = noise_scaled

                mix_id = f"mix_{mix_counter:03d}_c{ci}_n{ni}_snr{snr_db:+d}dB"
                mix_path = MIXES_DIR / f"{mix_id}.wav"
                clean_path = CLEAN_DIR / f"{mix_id}.wav"
                noise_path = NOISE_DIR / f"{mix_id}.wav"
                sf.write(str(mix_path), mix.astype(np.float32), TARGET_SR)
                sf.write(str(clean_path), clean_out.astype(np.float32), TARGET_SR)
                sf.write(str(noise_path), noise_out.astype(np.float32), TARGET_SR)

                measured = _measured_snr_db(clean_out, noise_out)
                manifest.append({
                    "mix_id": mix_id,
                    "mix_path": str(mix_path.relative_to(REPO_ROOT)),
                    "clean_path": str(clean_path.relative_to(REPO_ROOT)),
                    "noise_path": str(noise_path.relative_to(REPO_ROOT)),
                    "target_input_snr_db": snr_db,
                    "measured_input_snr_db": round(measured, 3),
                    "sample_rate": TARGET_SR,
                    "duration_sec": TARGET_DURATION_SEC,
                    "clean_source": {
                        "wav": csrc["wav"],
                        "call_start": csrc["call_start"],
                        "call_end": csrc["call_end"],
                    },
                    "noise_source": {
                        "wav": nsrc["wav"],
                        "noise_start": nsrc["noise_start"],
                        "noise_end": nsrc["noise_end"],
                    },
                })
                mix_counter += 1
            if mix_counter >= MAX_MIXES:
                break
        if mix_counter >= MAX_MIXES:
            break

    with open(MANIFEST_PATH, "w") as f:
        json.dump({"mixes": manifest}, f, indent=2)

    print(f"[build_mixes] wrote {len(manifest)} mixes to {MIXES_DIR}")
    print(f"[build_mixes] manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
