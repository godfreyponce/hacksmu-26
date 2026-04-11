"""
Elephant Audio Processing Pipeline
===================================
HackSMU VII — iMasons Challenge

Goal: Remove overlapping mechanical noise (airplanes, cars, generators) from
elephant audio recordings without distorting the elephant calls.

Science behind the approach:
- Elephant rumbles are HARMONIC: fundamental 10-20 Hz, harmonics up to ~1000 Hz.
  On a spectrogram they appear as horizontal bands (sustained frequency over time).
- Mechanical noise is BROADBAND + STATIONARY: it fills frequency space as a
  diffuse hum that is always present with no clean harmonic structure.
- These two signal types overlap in the same frequency range, so a simple bandpass
  filter won't work. The key insight: they differ in STRUCTURE, not frequency.
- We exploit this with HPSS (Harmonic-Percussive Source Separation), which uses
  median filters on the spectrogram to separate horizontal patterns (elephant calls)
  from diffuse/vertical patterns (noise). Then we do a second cleanup pass with
  spectral gating using the noise fingerprint derived from the silent gaps.
"""

import os
import json
import shutil

import numpy as np
import pandas as pd
import librosa
import librosa.display
import soundfile as sf
import matplotlib
matplotlib.use("Agg")  # headless — no display required, works on any machine
import matplotlib.pyplot as plt
from scipy.signal import butter, sosfilt


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_call_mask(num_samples: int, calls: list, sr: int) -> np.ndarray:
    """Return a boolean array of length num_samples that is True during call windows."""
    mask = np.zeros(num_samples, dtype=bool)
    for start_sec, end_sec in calls:
        s = int(start_sec * sr)
        e = min(int(end_sec * sr), num_samples)
        mask[s:e] = True
    return mask


def _compute_snr(audio: np.ndarray, calls: list, sr: int) -> float:
    """
    Compute Signal-to-Noise Ratio in dB.

    'Signal' = RMS energy during labeled call windows.
    'Noise'  = RMS energy during all other (non-call) samples.
    SNR = 20 * log10(signal_rms / noise_rms)
    """
    mask = _build_call_mask(len(audio), calls, sr)

    signal_samples = audio[mask]
    noise_samples = audio[~mask]

    # Guard against empty segments (recordings where calls span the whole file, etc.)
    signal_rms = np.sqrt(np.mean(signal_samples ** 2)) if mask.any() else 1e-10
    noise_rms = np.sqrt(np.mean(noise_samples ** 2)) if (~mask).any() else 1e-10

    return float(20 * np.log10(signal_rms / (noise_rms + 1e-10)))


def _estimate_fundamental(audio: np.ndarray, start_sec: float, end_sec: float,
                           sr: int, n_fft: int = 4096) -> float:
    """
    Estimate the fundamental frequency of a single call window.

    Strategy: take the mean power spectrum of the call segment in the
    10–200 Hz band and find the peak. Elephant fundamentals live in 10-20 Hz
    with first harmonics up to ~200 Hz, so this range captures both.
    Returns 0.0 if the segment is too short to analyze.
    """
    s = int(start_sec * sr)
    e = int(end_sec * sr)
    segment = audio[s:e]

    if len(segment) < n_fft:
        return 0.0

    D = np.abs(librosa.stft(segment, n_fft=n_fft))
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Restrict to 10–200 Hz — where elephant fundamentals and first harmonics live
    band = (freqs >= 10) & (freqs <= 200)
    if not band.any():
        return 0.0

    mean_spectrum = D[band].mean(axis=1)
    peak_freq = float(freqs[band][np.argmax(mean_spectrum)])
    return round(peak_freq, 2)


def _auto_detect_calls(H_mag: np.ndarray, sr: int, n_fft: int = 4096,
                        min_duration: float = 0.5, merge_gap: float = 0.5) -> list:
    """
    Auto-detect likely elephant call regions from the HPSS harmonic magnitude.

    For recordings with no labeled calls, we can still find probable call regions
    by looking for bursts of harmonic energy in the 10-200 Hz band.

    Steps:
    1. Sum harmonic energy in 10-200 Hz per time frame
    2. Smooth with a median filter to remove transient spikes
    3. Threshold at mean + 1 std → candidate regions
    4. Merge nearby candidates (gap < merge_gap seconds)
    5. Drop regions shorter than min_duration

    Returns list of (start_sec, end_sec) tuples.
    """
    from scipy.ndimage import median_filter

    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)
    band = (freqs >= 10) & (freqs <= 200)

    # Energy in elephant frequency band per time frame
    energy = H_mag[band].sum(axis=0)

    # Smooth to remove transient spikes (window ~0.25s worth of frames)
    hop_length = n_fft // 4
    frames_per_quarter_sec = max(1, int(0.25 * sr / hop_length))
    energy_smooth = median_filter(energy, size=frames_per_quarter_sec)

    # Threshold: frames above mean + 1 std are candidate call frames
    threshold = np.mean(energy_smooth) + np.std(energy_smooth)
    active = energy_smooth > threshold

    # Convert frame indices to time
    frame_times = librosa.frames_to_time(np.arange(len(active)), sr=sr, hop_length=hop_length)

    # Find contiguous active regions
    regions = []
    in_region = False
    start = 0.0
    for i, is_active in enumerate(active):
        t = frame_times[i]
        if is_active and not in_region:
            start = t
            in_region = True
        elif not is_active and in_region:
            regions.append((start, t))
            in_region = False
    if in_region:
        regions.append((start, frame_times[-1]))

    # Merge regions separated by less than merge_gap
    merged = []
    for s, e in regions:
        if merged and s - merged[-1][1] < merge_gap:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))

    # Filter out regions shorter than min_duration
    merged = [(s, e) for s, e in merged if e - s >= min_duration]

    return merged


def _save_spectrogram(audio: np.ndarray, sr: int, path: str, title: str,
                      n_fft: int = 4096) -> None:
    """
    Save a presentation-quality spectrogram PNG.

    Design choices:
    - Dark background (#0d1117) looks great on the demo UI
    - 'magma' colormap: perceptually uniform, readable at any brightness
    - y-axis capped at 2000 Hz: shows the full elephant call range without
      wasting space on empty high-frequency space
    - 150 DPI: crisp on retina displays without being enormous
    """
    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    D = librosa.stft(audio, n_fft=n_fft)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

    img = librosa.display.specshow(
        S_db,
        sr=sr,
        x_axis="time",
        y_axis="hz",
        fmin=0,
        fmax=2000,
        ax=ax,
        cmap="magma",
    )

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
# Pipeline steps (exposed separately so they're easy to test or swap out)
# ---------------------------------------------------------------------------

def step1_load(wav_path: str, csv_path: str):
    """
    Step 1: Load audio + parse call timestamps from CSV.

    sr=None is CRITICAL — we must preserve the original sample rate.
    Elephant infrasound at 10-20 Hz requires full resolution; resampling
    down (librosa's default 22050 Hz) would wipe out these fundamentals.
    """
    print(f"  [1/6] Loading {os.path.basename(wav_path)} ...")
    y, sr = librosa.load(wav_path, sr=None)

    basename = os.path.basename(wav_path)
    df = pd.read_csv(csv_path)

    # The CSV may use slightly different column names — try common variants
    fn_col = next((c for c in df.columns if "file" in c.lower()), df.columns[0])
    df_file = df[df[fn_col] == basename]

    # Try to find start/end columns regardless of exact naming
    start_col = next((c for c in df.columns if "start" in c.lower()), None)
    end_col = next((c for c in df.columns if "end" in c.lower()), None)

    calls = []
    call_types = []
    type_col = next((c for c in df.columns if "type" in c.lower() or "call" in c.lower() and c != fn_col), None)
    if start_col and end_col and not df_file.empty:
        calls = df_file[[start_col, end_col]].values.tolist()
        if type_col:
            call_types = df_file[type_col].fillna("unknown").tolist()
        else:
            call_types = ["unknown"] * len(calls)

    print(f"     Sample rate: {sr} Hz | Duration: {len(y)/sr:.1f}s | Calls: {len(calls)}")
    return y, sr, calls, call_types, basename


def step2_noise_profile(y: np.ndarray, sr: int, calls: list, n_fft: int = 4096) -> np.ndarray:
    """
    Step 2: Build a per-frequency noise fingerprint from non-call segments.

    We extract only the audio samples that fall OUTSIDE labeled call windows,
    compute their STFT, and average the magnitude spectrum across time.
    The resulting vector (one value per frequency bin) tells us the typical
    noise floor at each frequency for this specific recording.

    This per-recording fingerprint accounts for the fact that a generator in
    one recording will have a different spectral shape than road noise in another.
    """
    print("  [2/6] Building noise profile from silence gaps ...")

    if not calls:
        # No labeled calls — can't identify noise-only segments.
        # Use percentile-based estimation: the 25th percentile of spectral energy
        # across time gives the noise floor. This assumes noise is present in at
        # least 75% of frames (true for recordings dominated by mechanical noise).
        print("     No labeled calls — using percentile-based noise estimation.")
        D_full = np.abs(librosa.stft(y, n_fft=n_fft))
        noise_profile = np.percentile(D_full, 25, axis=1, keepdims=True)
    else:
        mask = _build_call_mask(len(y), calls, sr)
        noise_samples = y[~mask]

        if len(noise_samples) < n_fft:
            # Edge case: calls span almost the entire file — use the whole signal
            print("     Warning: almost no non-call audio. Using full signal for noise profile.")
            noise_samples = y

        D_noise = librosa.stft(noise_samples, n_fft=n_fft)
        # keepdims=True keeps shape (n_freqs, 1) so we can broadcast against (n_freqs, n_frames)
        noise_profile = np.mean(np.abs(D_noise), axis=1, keepdims=True)
    print(f"     Noise profile shape: {noise_profile.shape} | "
          f"Mean noise floor: {float(noise_profile.mean()):.4f}")
    return noise_profile


def step3_hpss(y: np.ndarray, sr: int, n_fft: int = 4096,
               kernel_size: int = 31) -> tuple:
    """
    Step 3: Harmonic-Percussive Source Separation (HPSS).

    HPSS applies two median filters to the STFT magnitude:
    - A HORIZONTAL median filter isolates patterns that persist across time
      → these are the harmonic components (elephant calls appear as flat
        horizontal bands on the spectrogram)
    - A VERTICAL median filter isolates patterns that span many frequencies
      at the same time frame → these are the percussive/broadband components
      (mechanical noise appears as a diffuse cloud or vertical smear)

    The reconstruction uses the original phase from the full STFT, which
    preserves audio quality — we're only modifying the magnitude.

    kernel_size controls the median filter window:
    - Smaller (e.g. 17): gentler separation, preserves more of both
    - Larger (e.g. 51): more aggressive, cleaner separation but may clip call edges

    Returns: (y_harmonic, D_mag, D_phase, H_mag) for use in step 4
    """
    print(f"  [3/6] HPSS separation (n_fft={n_fft}, kernel_size={kernel_size}) ...")
    D = librosa.stft(y, n_fft=n_fft)
    D_mag = np.abs(D)
    D_phase = np.angle(D)

    H_mag, P_mag = librosa.decompose.hpss(D_mag, kernel_size=kernel_size)

    # Reconstruct harmonic audio using harmonic magnitude + original phase
    D_harmonic = H_mag * np.exp(1j * D_phase)
    y_harmonic = librosa.istft(D_harmonic, length=len(y))

    h_energy = float(np.mean(H_mag ** 2))
    p_energy = float(np.mean(P_mag ** 2))
    print(f"     Harmonic energy: {h_energy:.4f} | Percussive energy: {p_energy:.4f} | "
          f"Harmonic ratio: {h_energy/(h_energy+p_energy+1e-10):.1%}")

    return y_harmonic, D_phase, H_mag


def step4_spectral_gate_and_bandpass(y_harmonic: np.ndarray, sr: int,
                                      noise_profile: np.ndarray, D_phase: np.ndarray,
                                      n_fft: int = 4096,
                                      oversubtraction: float = 1.5,
                                      bandpass_low: float = 8.0,
                                      bandpass_high: float = 1200.0) -> np.ndarray:
    """
    Step 4: Spectral Gating + Bandpass Filter.

    HPSS alone might leave residual tonal noise (a generator hum is technically
    harmonic — it has steady tones at its fundamental and harmonics, so HPSS
    won't fully remove it). This step does a surgical cleanup:

    1. SPECTRAL SUBTRACTION: For each frequency bin, subtract the expected noise
       floor (from step 2) scaled by `oversubtraction`. The scale > 1.0 means we
       remove slightly more than the measured noise floor, which handles noise
       variance. np.maximum(..., 0) prevents negative magnitudes (Wiener-style).

    2. BANDPASS FILTER: Hard cut anything outside 8–1200 Hz using a 4th-order
       Butterworth filter. This removes:
       - Sub-8 Hz: seismic rumble, mic handling noise
       - Above 1200 Hz: birds, insects, wind — not elephant calls
       (Note: 8 Hz not 0 Hz as lower bound because the Butterworth filter
        needs a non-zero lower cutoff for a bandpass design)

    oversubtraction tuning guide:
    - 1.0: subtract exactly the measured noise floor (conservative)
    - 1.5: subtract 150% of measured floor (default — handles noise variance)
    - 2.0: very aggressive, may cause 'musical noise' artifacts if overdone
    """
    print(f"  [4/6] Spectral gating (oversubtraction={oversubtraction}) + "
          f"bandpass {bandpass_low}–{bandpass_high} Hz ...")

    D_h = librosa.stft(y_harmonic, n_fft=n_fft)
    D_h_mag = np.abs(D_h)
    D_h_phase = np.angle(D_h)

    # Broadcast noise profile (n_freqs, 1) across all time frames
    noise_floor = np.tile(noise_profile, (1, D_h_mag.shape[1]))
    D_gated = np.maximum(D_h_mag - noise_floor * oversubtraction, 0)

    # Reconstruct audio from gated magnitude + harmonic phase
    D_cleaned = D_gated * np.exp(1j * D_h_phase)
    y_cleaned = librosa.istft(D_cleaned, length=len(y_harmonic))

    # Bandpass filter: 4th-order Butterworth in second-order sections (sosfilt)
    # sosfilt is numerically more stable than lfilter for high-order filters
    sos = butter(4, [bandpass_low, bandpass_high], btype="bandpass", fs=sr, output="sos")
    y_cleaned = sosfilt(sos, y_cleaned)

    # Normalize to avoid clipping
    peak = np.max(np.abs(y_cleaned))
    if peak > 0:
        y_cleaned = y_cleaned / peak * 0.95

    print(f"     Done. Output peak amplitude: {float(np.max(np.abs(y_cleaned))):.3f}")
    return y_cleaned


def step5_spectrograms(y: np.ndarray, y_cleaned: np.ndarray, sr: int,
                        output_dir: str, n_fft: int = 4096) -> tuple:
    """
    Step 5: Generate presentation-quality spectrogram PNGs.

    Both before and after spectrograms use identical settings so the comparison
    is visually meaningful — the only difference is the signal content.
    """
    print("  [5/6] Generating spectrograms ...")
    before_path = os.path.join(output_dir, "spectrogram_before.png")
    after_path = os.path.join(output_dir, "spectrogram_after.png")

    _save_spectrogram(y, sr, before_path, "Original Recording", n_fft=n_fft)
    _save_spectrogram(y_cleaned, sr, after_path, "Cleaned Recording (HPSS + Spectral Gate)", n_fft=n_fft)

    print(f"     Saved: {before_path}")
    print(f"     Saved: {after_path}")
    return before_path, after_path


def step6_snr_validation(y: np.ndarray, y_cleaned: np.ndarray,
                          sr: int, calls: list, call_types: list, basename: str,
                          n_fft: int = 4096) -> tuple:
    """
    Step 6: Measure SNR before/after and compute per-call metrics.

    SNR = 20 * log10(RMS_during_calls / RMS_during_non_calls)

    A positive SNR_improvement means the cleaned audio has a higher
    signal-to-noise ratio — elephant calls are louder relative to the
    background noise after processing.

    Per-call metrics include the estimated fundamental frequency, which
    is useful for the research dashboard to show which calls were best
    preserved.
    """
    print("  [6/6] Computing SNR metrics ...")

    if not calls:
        # No labeled calls — can't compute meaningful call-vs-noise SNR.
        # Report 0.0 instead of nonsensical -160 dB values.
        print("     No labeled calls — SNR metrics not applicable.")
        snr_before = 0.0
        snr_after = 0.0
        improvement = 0.0
        calls_detected = []
    else:
        snr_before = _compute_snr(y, calls, sr)
        snr_after = _compute_snr(y_cleaned, calls, sr)
        improvement = snr_after - snr_before

        print(f"     SNR before: {snr_before:.1f} dB")
        print(f"     SNR after:  {snr_after:.1f} dB")
        print(f"     Improvement: {improvement:+.1f} dB")

        calls_detected = []
        for i, (start, end) in enumerate(calls):
            fundamental = _estimate_fundamental(y_cleaned, start, end, sr, n_fft=n_fft)
            calls_detected.append({
                "start_time": round(start, 3),
                "end_time": round(end, 3),
                "call_type": call_types[i] if i < len(call_types) else "unknown",
                "estimated_fundamental_hz": fundamental,
            })

    return snr_before, snr_after, improvement, calls_detected


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------

def process_recording(wav_path: str, csv_path: str, output_dir: str,
                       n_fft: int = 4096,
                       hpss_kernel_size: int = 31,
                       bandpass_low: float = 8.0,
                       bandpass_high: float = 1200.0,
                       oversubtraction: float = 1.5) -> dict:
    """
    Full elephant audio processing pipeline.

    Parameters
    ----------
    wav_path : str
        Path to the input .wav file.
    csv_path : str
        Path to calls.csv containing labeled call timestamps.
    output_dir : str
        Directory where outputs will be written. Created if it doesn't exist.
    n_fft : int
        STFT window size. 4096 gives ~1 Hz frequency resolution at 44.1 kHz,
        which is essential for resolving 10-20 Hz elephant fundamentals.
    hpss_kernel_size : int
        Median filter size for HPSS. Higher = more aggressive separation.
        Try 17 (gentle), 31 (default), 51 (aggressive) if tuning is needed.
    bandpass_low : float
        Lower cutoff of bandpass filter in Hz.
    bandpass_high : float
        Upper cutoff of bandpass filter in Hz.
    oversubtraction : float
        Spectral gate aggressiveness. 1.0 = subtract measured noise floor exactly.
        1.5 = subtract 150% (default). Higher values risk musical noise artifacts.

    Returns
    -------
    dict
        The results.json payload (also written to output_dir/results.json).
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n{'='*60}")
    print(f"Processing: {os.path.basename(wav_path)}")
    print(f"Output dir: {output_dir}")
    print(f"{'='*60}")

    # Step 1: Load
    y, sr, calls, call_types, basename = step1_load(wav_path, csv_path)

    # Step 2: Noise profile (from non-call gaps)
    noise_profile = step2_noise_profile(y, sr, calls, n_fft=n_fft)

    # Adaptive parameter tuning for difficult recordings:
    # - No labeled calls: use gentle params since we can't precisely identify signal
    # - Low SNR (noise louder than signal): reduce aggressiveness to preserve calls
    if not calls:
        hpss_kernel_size = min(hpss_kernel_size, 17)
        oversubtraction = min(oversubtraction, 0.8)
        print(f"     Adaptive: no calls → kernel_size={hpss_kernel_size}, "
              f"oversubtraction={oversubtraction}")
    else:
        rough_snr = _compute_snr(y, calls, sr)
        if rough_snr < 0:
            hpss_kernel_size = min(hpss_kernel_size, 21)
            oversubtraction = min(oversubtraction, 1.0)
            print(f"     Adaptive: low SNR ({rough_snr:.1f} dB) → kernel_size={hpss_kernel_size}, "
                  f"oversubtraction={oversubtraction}")

    # Step 3: HPSS — separate harmonic (calls) from percussive (noise)
    y_harmonic, D_phase, H_mag = step3_hpss(y, sr, n_fft=n_fft, kernel_size=hpss_kernel_size)

    # Auto-detect calls for unlabeled recordings using harmonic energy peaks
    detection_method = "labeled"
    if not calls:
        auto_calls = _auto_detect_calls(H_mag, sr, n_fft=n_fft)
        if auto_calls:
            calls = auto_calls
            call_types = ["auto-detected"] * len(calls)
            detection_method = "auto"
            print(f"     Auto-detected {len(calls)} probable call regions")

    # Step 4: Spectral gating + bandpass filter
    y_cleaned = step4_spectral_gate_and_bandpass(
        y_harmonic, sr, noise_profile, D_phase,
        n_fft=n_fft,
        oversubtraction=oversubtraction,
        bandpass_low=bandpass_low,
        bandpass_high=bandpass_high,
    )

    # Step 5: Spectrograms
    step5_spectrograms(y, y_cleaned, sr, output_dir, n_fft=n_fft)

    # Step 6: SNR metrics
    snr_before, snr_after, improvement, calls_detected = step6_snr_validation(
        y, y_cleaned, sr, calls, call_types, basename, n_fft=n_fft
    )

    # Write outputs
    print("  Writing output files ...")
    shutil.copy(wav_path, os.path.join(output_dir, "original.wav"))
    sf.write(os.path.join(output_dir, "cleaned.wav"), y_cleaned, sr)

    results = {
        "filename": basename,
        "sample_rate": sr,
        "duration_seconds": round(len(y) / sr, 2),
        "snr_before_db": round(snr_before, 2),
        "snr_after_db": round(snr_after, 2),
        "snr_improvement_db": round(improvement, 2),
        "detection_method": detection_method,
        "calls_detected": calls_detected,
        "processing_params": {
            "n_fft": n_fft,
            "hpss_kernel_size": hpss_kernel_size,
            "bandpass_low_hz": bandpass_low,
            "bandpass_high_hz": bandpass_high,
            "oversubtraction_factor": oversubtraction,
        },
    }

    results_path = os.path.join(output_dir, "results.json")
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n  Done! SNR improvement: {improvement:+.1f} dB")
    print(f"  Outputs in: {output_dir}")
    return results


# ---------------------------------------------------------------------------
# Batch processing (stretch goal)
# ---------------------------------------------------------------------------

def process_all(recordings_dir: str, csv_path: str, output_base: str, **kwargs) -> list:
    """
    Process all .wav files in recordings_dir.

    Results are written to output_base/recording_XX/ for each file.
    Returns a list of result dicts.

    Usage:
        results = process_all("data/recordings", "data/calls.csv", "output")
    """
    wav_files = sorted([
        os.path.join(recordings_dir, f)
        for f in os.listdir(recordings_dir)
        if f.lower().endswith(".wav")
    ])

    print(f"Found {len(wav_files)} recordings to process.")
    all_results = []

    for i, wav_path in enumerate(wav_files, 1):
        stem = os.path.splitext(os.path.basename(wav_path))[0]
        output_dir = os.path.join(output_base, stem)
        try:
            result = process_recording(wav_path, csv_path, output_dir, **kwargs)
            all_results.append(result)
        except Exception as e:
            print(f"  ERROR processing {wav_path}: {e}")
            all_results.append({"filename": os.path.basename(wav_path), "error": str(e)})

    # Write a summary across all recordings
    summary_path = os.path.join(output_base, "summary.json")
    with open(summary_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nBatch complete. Summary: {summary_path}")

    return all_results


# ---------------------------------------------------------------------------
# Quick test entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 2 and sys.argv[1] == "batch":
        # Batch mode: python process.py batch [recordings_dir] [csv_path] [output_base]
        recordings_dir = sys.argv[2] if len(sys.argv) > 2 else "data/recordings"
        csv_path = sys.argv[3] if len(sys.argv) > 3 else "data/calls.csv"
        output_base = sys.argv[4] if len(sys.argv) > 4 else "output"
        results = process_all(recordings_dir, csv_path, output_base)
        improvements = [r.get("snr_improvement_db", 0) for r in results if "error" not in r]
        if improvements:
            print(f"\nMean SNR improvement across {len(improvements)} files: "
                  f"{sum(improvements)/len(improvements):+.1f} dB")
    else:
        # Single file mode: python process.py [wav_path] [csv_path] [output_dir]
        wav = sys.argv[1] if len(sys.argv) > 1 else "data/recordings/recording_01.wav"
        csv = sys.argv[2] if len(sys.argv) > 2 else "data/calls.csv"
        out = sys.argv[3] if len(sys.argv) > 3 else "output/test_run"

        result = process_recording(wav, csv, out)
        print("\n" + json.dumps(result, indent=2))
