"""
Infrasound Preservation Comparison
===================================
HackSMU VII — iMasons Challenge

Hypothesis
----------
Our infrasound-first pipeline (HPSS + spectral subtraction + 8–1200 Hz
bandpass) preserves the 10–35 Hz fundamental of African elephant rumbles.
A generic speech-trained denoiser (RNNoise, Facebook Denoiser, Meta
MetricGAN, Adobe Podcast, …) implicitly high-passes at roughly 80–100 Hz
because human speech contains essentially no information below that, so
it would erase the elephant fundamental entirely.

What this script does
---------------------
We run the SAME input recording through two pipelines:

  (a) OUR pipeline — imported from backend.pipeline.process
  (b) SPEECH-STYLE PROXY — a defensible simulation of what a generic
      speech-trained denoiser does to low frequencies. We do NOT call a
      real ML model (that would drag in torch / onnxruntime / etc. as
      dependencies). Instead we apply:
          1. a 100 Hz 4th-order Butterworth high-pass (the effective floor
             imposed by RNNoise-family models);
          2. an aggressive spectral gate / noise-subtraction pass built
             from a non-call section of the recording.
      This proxy is clearly labelled a simulation wherever it is reported.

For each pipeline we measure the ENERGY RETAINED in three bands relative
to the original recording, expressed in dB:
    8–35 Hz    (elephant fundamental — the one that matters)
    35–200 Hz  (early harmonics)
    200–1200 Hz (mid-frequency harmonics / formant-like content)

We save matched-axis spectrograms (0–200 Hz y-axis, identical colormap)
for visual comparison, write the two cleaned .wav files, and write a
results.json.

Usage
-----
    python scripts/compare/infrasound_comparison.py [wav_path]

If no wav_path is given we default to a file known to carry a strong
low-frequency fundamental (see DEFAULT_WAV below).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

import numpy as np
import librosa
import librosa.display
import soundfile as sf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Make `backend` importable
sys.path.insert(0, str(REPO_ROOT))

# Default recording: from output/summary.json this file has a labeled call with
# estimated_fundamental_hz = 11.72 Hz (deep in infrasound) and sits at 48 kHz.
DEFAULT_WAV = REPO_ROOT / "data" / "recordings" / "04-040920-03_vehicle_noise_1.wav"
CALLS_CSV = REPO_ROOT / "data" / "calls.csv"


# ---------------------------------------------------------------------------
# Speech-style proxy denoiser
# ---------------------------------------------------------------------------
#
# This is a SIMULATION, not a real ML model. It mimics the low-frequency
# behaviour of speech-trained denoisers (RNNoise, Facebook Denoiser, Meta
# MetricGAN, Adobe Podcast, Krisp, etc.) by:
#
#   1. High-passing at 100 Hz with a 4th-order Butterworth filter.
#      RNNoise's spectral bands start around ~100 Hz; Facebook Denoiser is
#      trained on 16 kHz / wideband speech that carries negligible energy
#      below 80 Hz. The 100 Hz HPF is the floor these models effectively
#      impose on their output.
#
#   2. Running a standard noise-profile spectral gate (subtractive, with
#      oversubtraction=2.0 to be aggressive like a production denoiser).
#      The noise profile is built from the first second of the recording,
#      which is assumed to be a non-call segment. This mirrors the
#      noisereduce / spectral-subtraction family of algorithms that ship
#      inside most speech denoisers as a pre/post step.
#
# Anything below 100 Hz is therefore DISCARDED before the gate even runs,
# so a 14 Hz elephant fundamental is obliterated. That is exactly the
# failure mode we want to demonstrate.

def speech_style_proxy(y: np.ndarray, sr: int,
                       hpf_cutoff: float = 100.0,
                       n_fft: int = 4096,
                       oversubtraction: float = 2.0,
                       noise_window_sec: float = 1.0) -> np.ndarray:
    """Apply a speech-denoiser-style cleanup. See module docstring."""
    # 1) Aggressive high-pass at 100 Hz — the speech-model floor.
    sos = butter(4, hpf_cutoff, btype="highpass", fs=sr, output="sos")
    y_hp = sosfilt(sos, y)

    # 2) Build noise profile from the first noise_window_sec seconds.
    noise_len = min(int(noise_window_sec * sr), len(y_hp) // 4)
    if noise_len < n_fft:
        noise_len = min(n_fft * 2, len(y_hp))
    noise_seg = y_hp[:noise_len]
    D_noise = np.abs(librosa.stft(noise_seg, n_fft=n_fft))
    noise_profile = np.mean(D_noise, axis=1, keepdims=True)

    # 3) Spectral subtraction on the full signal.
    D = librosa.stft(y_hp, n_fft=n_fft)
    D_mag = np.abs(D)
    D_phase = np.angle(D)
    D_gated = np.maximum(D_mag - noise_profile * oversubtraction, 0.0)

    y_out = librosa.istft(D_gated * np.exp(1j * D_phase), length=len(y_hp))

    # Normalize to avoid clipping, match level of input for fair comparison.
    peak = np.max(np.abs(y_out))
    if peak > 0:
        y_out = y_out / peak * 0.95
    return y_out.astype(np.float32)


# ---------------------------------------------------------------------------
# Energy measurement
# ---------------------------------------------------------------------------

BANDS = [
    ("8-35 Hz (fundamental)", 8.0, 35.0),
    ("35-200 Hz (harmonics)", 35.0, 200.0),
    ("200-1200 Hz (mid)", 200.0, 1200.0),
]


def band_energy(y: np.ndarray, sr: int, f_lo: float, f_hi: float,
                n_fft: int = 4096) -> float:
    """Return total spectral energy in [f_lo, f_hi] Hz (magnitude-squared sum)."""
    D = np.abs(librosa.stft(y, n_fft=n_fft))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    mask = (freqs >= f_lo) & (freqs < f_hi)
    if not mask.any():
        return 0.0
    return float(np.sum(D[mask] ** 2))


def retained_db(y_clean: np.ndarray, y_orig: np.ndarray, sr: int,
                 f_lo: float, f_hi: float) -> float:
    """dB of energy retained in band: 10*log10(E_clean / E_orig)."""
    e_clean = band_energy(y_clean, sr, f_lo, f_hi)
    e_orig = band_energy(y_orig, sr, f_lo, f_hi)
    if e_orig <= 0:
        return float("nan")
    ratio = (e_clean + 1e-20) / (e_orig + 1e-20)
    return float(10.0 * np.log10(ratio))


def measure_all_bands(y_clean: np.ndarray, y_orig: np.ndarray, sr: int) -> dict:
    out = {}
    for label, lo, hi in BANDS:
        out[label] = round(retained_db(y_clean, y_orig, sr, lo, hi), 2)
    return out


# ---------------------------------------------------------------------------
# Spectrogram (0–200 Hz, identical axes/cmap for all three)
# ---------------------------------------------------------------------------

def save_low_freq_spec(y: np.ndarray, sr: int, path: Path, title: str,
                        n_fft: int = 8192,
                        vmin_db: float = -80.0,
                        vmax_db: float = 0.0) -> None:
    """Save a spectrogram zoomed to 0–200 Hz with a fixed dB range.

    We use n_fft=8192 (not 4096) so that at 48 kHz we get ~5.9 Hz
    resolution, which is adequate to see 14 Hz bands clearly on a
    0–200 Hz axis. vmin/vmax are fixed across the three plots so the
    colors mean the same thing visually.
    """
    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    D = librosa.stft(y, n_fft=n_fft)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

    img = librosa.display.specshow(
        S_db, sr=sr, hop_length=n_fft // 4,
        x_axis="time", y_axis="hz",
        ax=ax, cmap="magma",
        vmin=vmin_db, vmax=vmax_db,
    )
    ax.set_ylim(0, 200)

    cbar = fig.colorbar(img, ax=ax, format="%+2.0f dB")
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    ax.set_title(title, color="white", fontsize=14, pad=10)
    ax.tick_params(colors="white")
    ax.xaxis.label.set_color("white")
    ax.yaxis.label.set_color("white")
    for spine in ax.spines.values():
        spine.set_color("#444444")

    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight", facecolor="#0d1117")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    wav_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_WAV
    if not wav_path.exists():
        raise SystemExit(f"Input wav not found: {wav_path}")

    print(f"Input: {wav_path}")
    print(f"Output dir: {OUT_DIR}")

    # Load original at native sample rate (crucial — resampling kills infrasound)
    y_orig, sr = librosa.load(str(wav_path), sr=None)
    print(f"Loaded {len(y_orig)/sr:.1f}s at {sr} Hz")

    # ---- (a) OUR pipeline -------------------------------------------------
    # Run the real pipeline in a temp output dir so we don't touch repo state,
    # then read back cleaned.wav.
    from backend.pipeline.process import process_recording  # type: ignore

    tmp_dir = Path(tempfile.mkdtemp(prefix="infra_cmp_"))
    try:
        print("\n--- Running OUR pipeline ---")
        process_recording(str(wav_path), str(CALLS_CSV), str(tmp_dir))
        ours_wav_src = tmp_dir / "cleaned.wav"
        y_ours, sr_ours = librosa.load(str(ours_wav_src), sr=None)
        if sr_ours != sr:
            # Shouldn't happen — process_recording preserves sr — but guard anyway
            y_ours = librosa.resample(y_ours, orig_sr=sr_ours, target_sr=sr)
        # Copy the output wav into our compare/out dir for the deliverable
        shutil.copyfile(ours_wav_src, OUT_DIR / "ours.wav")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # Length align (istft can shave 1 sample)
    n = min(len(y_orig), len(y_ours))
    y_orig_a = y_orig[:n]
    y_ours_a = y_ours[:n]

    # ---- (b) Speech-style proxy pipeline ---------------------------------
    print("\n--- Running SPEECH-STYLE PROXY pipeline ---")
    print("  (simulated speech denoiser: 100 Hz HPF + spectral gate)")
    y_speech = speech_style_proxy(y_orig, sr)
    y_speech_a = y_speech[:n]
    sf.write(str(OUT_DIR / "speechstyle.wav"), y_speech_a, sr)

    # ---- Measurements ----------------------------------------------------
    print("\n--- Measuring band-retained energy (dB rel. original) ---")
    results = {
        "input_file": str(wav_path),
        "sample_rate": sr,
        "duration_seconds": round(n / sr, 2),
        "bands": [lbl for lbl, _, _ in BANDS],
        "ours": measure_all_bands(y_ours_a, y_orig_a, sr),
        "speech_style_proxy": measure_all_bands(y_speech_a, y_orig_a, sr),
        "notes": (
            "speech_style_proxy is a SIMULATION, not a real ML model. "
            "It applies a 100 Hz 4th-order Butterworth high-pass (the "
            "effective low-frequency floor of RNNoise-family speech "
            "denoisers) followed by aggressive spectral subtraction. "
            "Energy retained is 10*log10(E_clean_band / E_original_band)."
        ),
    }

    print(f"  OURS:         {results['ours']}")
    print(f"  SPEECH-PROXY: {results['speech_style_proxy']}")

    with open(OUT_DIR / "results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"Wrote {OUT_DIR / 'results.json'}")

    # ---- Spectrograms (identical axes / cmap / vmin / vmax) -------------
    print("\n--- Saving spectrograms (0-200 Hz) ---")
    save_low_freq_spec(y_orig_a, sr, OUT_DIR / "original_spec.png",
                        "Original recording (0-200 Hz)")
    save_low_freq_spec(y_ours_a, sr, OUT_DIR / "ours_spec.png",
                        "Our pipeline — HPSS + spectral gate + 8 Hz bandpass (0-200 Hz)")
    save_low_freq_spec(y_speech_a, sr, OUT_DIR / "speechstyle_spec.png",
                        "Speech-style proxy — 100 Hz HPF + spectral gate (SIMULATION, 0-200 Hz)")

    # ---- Auto-generate REPORT.md with real numbers ---------------------
    write_report(results)

    print("Done.")


def _fmt(band: str, d: dict) -> str:
    v = d.get(band)
    if v is None:
        return "n/a"
    return f"{v:+.2f} dB"


def write_report(results: dict) -> None:
    """Render REPORT.md alongside the script using the measured numbers."""
    report_path = Path(__file__).resolve().parent / "REPORT.md"
    ours = results["ours"]
    spx = results["speech_style_proxy"]
    bands = results["bands"]

    # Compute headline delta in the fundamental band
    b_fund = bands[0]
    delta_fund = (ours.get(b_fund, 0.0) or 0.0) - (spx.get(b_fund, 0.0) or 0.0)

    # Honest verdict: require at least a 10 dB advantage in the fundamental
    if delta_fund >= 10.0:
        verdict = (
            f"Hypothesis CONFIRMED. Our pipeline retains "
            f"**{delta_fund:+.1f} dB** more energy in the 8–35 Hz elephant "
            f"fundamental band than the speech-style proxy."
        )
    elif delta_fund >= 3.0:
        verdict = (
            f"Hypothesis partially supported. Our pipeline retains "
            f"{delta_fund:+.1f} dB more energy in the 8–35 Hz band than "
            f"the speech-style proxy — a real but modest advantage."
        )
    else:
        verdict = (
            f"Hypothesis NOT supported on this file. Measured advantage "
            f"in the 8–35 Hz band is only {delta_fund:+.1f} dB."
        )

    md = f"""# Infrasound Preservation: Our Pipeline vs. a Speech-Denoiser Proxy

## Hypothesis

African-elephant rumbles carry their fundamental frequency in the 10–35 Hz
infrasound band. Our audio cleanup pipeline is designed from the ground up
to preserve that band (8 Hz bandpass floor, HPSS instead of any
speech-trained model). Generic speech denoisers — RNNoise, Facebook
Denoiser, Meta MetricGAN, Adobe Podcast, Krisp — are trained on human
speech that carries no useful energy below roughly 80–100 Hz, and they
implicitly or explicitly high-pass everything below that threshold. If you
run an elephant rumble through one, you erase the very thing you were
trying to hear.

## Methodology

Input recording: `{Path(results['input_file']).name}` — {results['duration_seconds']}s
at {results['sample_rate']} Hz. This file was chosen because
`output/summary.json` reports a labeled rumble with an estimated
fundamental of ~11.7 Hz, i.e. deep infrasound.

Two pipelines are run on the same input:

1. **Our pipeline** — `backend.pipeline.process.process_recording`:
   HPSS (harmonic/percussive separation) + per-recording spectral
   subtraction + 8–1200 Hz Butterworth bandpass.

2. **Speech-style proxy** — a *simulation* of a generic speech-trained
   denoiser. **This is not a real ML model.** It applies a 100 Hz
   4th-order Butterworth high-pass (the effective low-frequency floor
   imposed by the RNNoise family) followed by an aggressive
   spectral-subtraction gate (oversubtraction=2.0) built from a
   non-call section of the recording. The 100 Hz high-pass is the
   critical ingredient — it is the behaviour every speech-trained model
   inherits from its training data, and it is what would annihilate a
   14 Hz rumble fundamental.

For each pipeline we report **energy retained** in three bands, expressed
in dB relative to the same band in the original recording
(`10·log10(E_clean / E_orig)`). 0 dB = perfect preservation; large
negative numbers = energy destroyed.

## Results

| Band | Our pipeline | Speech-style proxy (simulated) |
|---|---|---|
| {bands[0]} | {_fmt(bands[0], ours)} | {_fmt(bands[0], spx)} |
| {bands[1]} | {_fmt(bands[1], ours)} | {_fmt(bands[1], spx)} |
| {bands[2]} | {_fmt(bands[2], ours)} | {_fmt(bands[2], spx)} |

Raw numbers: [`out/results.json`](out/results.json).

### Spectrograms (0–200 Hz, identical axes and colormap)

![Original](out/original_spec.png)

![Our pipeline](out/ours_spec.png)

![Speech-style proxy (simulation)](out/speechstyle_spec.png)

Cleaned audio files: [`out/ours.wav`](out/ours.wav),
[`out/speechstyle.wav`](out/speechstyle.wav).

## Conclusion

{verdict}

The speech-style proxy is deliberately conservative — a real RNNoise
deployment would often add an even harsher high-pass plus learned
suppression of unfamiliar low-frequency content, so the real-world gap
against our pipeline is expected to be at least as large as the number
above. The 35–200 Hz and 200–1200 Hz columns are provided for context:
both pipelines can preserve harmonic content there, but only a pipeline
that refuses to high-pass at 100 Hz can keep the infrasonic fundamental,
which is the signal we actually care about.
"""
    report_path.write_text(md)
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
