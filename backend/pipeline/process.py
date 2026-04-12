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
    - y-axis capped at 5000 Hz: shows elephant calls in context with enough
      surrounding frequency range for judges to see the full picture
    - 150 DPI: crisp on retina displays without being enormous
    """
    fig, ax = plt.subplots(figsize=(12, 5), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    D = librosa.stft(audio, n_fft=n_fft)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

    img = librosa.display.specshow(
        S_db,
        sr=sr,
        hop_length=n_fft // 4,
        x_axis="time",
        y_axis="hz",
        ax=ax,
        cmap="magma",
    )
    ax.set_ylim(0, 5000)

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


def step2_noise_profile(source: np.ndarray, sr: int, calls: list, n_fft: int = 4096,
                         label: str = "harmonic") -> np.ndarray:
    """
    Step 2: Build a per-frequency noise fingerprint from non-call segments
    of the HPSS harmonic signal.

    IMPORTANT: the `source` we profile must be on the SAME scale as the signal
    we later subtract from. Previously we profiled the raw `y` but subtracted
    from the STFT of `y_harmonic` (HPSS output), which is already magnitude-
    reduced — that mismatch caused the oversubtraction factor to behave
    unpredictably. We now profile the harmonic signal directly so the
    subtraction is self-consistent.
    """
    print(f"  [2/6] Building noise profile from {label} non-call segments ...")

    if not calls:
        # No labeled calls — use percentile-based estimation: the 25th percentile
        # of spectral magnitude across time approximates the noise floor.
        print("     No labeled calls — using percentile-based noise estimation.")
        D_full = np.abs(librosa.stft(source, n_fft=n_fft))
        noise_profile = np.percentile(D_full, 25, axis=1, keepdims=True)
    else:
        mask = _build_call_mask(len(source), calls, sr)
        noise_samples = source[~mask]

        if len(noise_samples) < n_fft:
            print("     Warning: almost no non-call audio. Using full signal for noise profile.")
            noise_samples = source

        D_noise = librosa.stft(noise_samples, n_fft=n_fft)
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


def step4a_spectral_gate(y_harmonic: np.ndarray, sr: int,
                          noise_profile: np.ndarray,
                          n_fft: int = 4096,
                          oversubtraction: float = 1.5,
                          residual_floor: float = 0.1) -> np.ndarray:
    """
    Step 4a: Wiener-style spectral gain mask (replaces hard subtraction).

    Previously we used hard spectral subtraction: D_gated = max(D - alpha*N, 0).
    That works on high-SNR recordings but annihilates weak signal at low SNR
    — failure mode observed on 99-37_airplane_and_vehicle_01.wav where the
    elephant rumble was softer than the noise floor and got zeroed out.

    The fix: a bounded, power-domain Wiener gain with a residual floor.

        gain(f,t) = max( P_signal / (P_signal + (alpha·N)^2 ), residual_floor )
        P_signal  = max( D^2 - (alpha·N)^2, 0 )   (signal power estimate)

    Properties:
    - Gain is in [residual_floor, 1], never negative, never exploding.
    - When D >> N, gain → 1 (signal passes through untouched).
    - When D ~ alpha·N, gain → 0.5 (attenuated but not annihilated).
    - When D << N, gain → residual_floor (weak call survives at reduced level
      instead of being deleted — judge can still hear it).

    residual_floor=0.1 means we always keep at least 10% of the harmonic
    magnitude. This is audibly the difference between "muffled but audible
    rumble in a noisy cleanup" and "dead silence where the call used to be."
    """
    print(f"  [4a/6] Wiener gain mask (alpha={oversubtraction}, "
          f"floor={residual_floor}) ...")

    D_h = librosa.stft(y_harmonic, n_fft=n_fft)
    D_h_mag = np.abs(D_h)
    D_h_phase = np.angle(D_h)

    N = np.tile(noise_profile, (1, D_h_mag.shape[1])) * oversubtraction
    # Power-domain Wiener-style gain
    sig_power = np.maximum(D_h_mag ** 2 - N ** 2, 0.0)
    gain = sig_power / (sig_power + N ** 2 + 1e-12)
    gain = np.maximum(gain, residual_floor)

    D_gated_mag = D_h_mag * gain
    D_gated_complex = D_gated_mag * np.exp(1j * D_h_phase)
    y_gated = librosa.istft(D_gated_complex, length=len(y_harmonic))
    return y_gated


def step4b_bandpass(y_gated: np.ndarray, sr: int,
                     bandpass_low: float = 8.0,
                     bandpass_high: float = 1200.0) -> np.ndarray:
    """
    Step 4b: 4th-order Butterworth bandpass — 8 Hz lower cutoff preserves
    elephant infrasound (fundamentals at 10-20 Hz) while cutting DC drift and
    mic-handling rumble. Upper cutoff 1200 Hz covers rumble harmonics without
    admitting birds/insects/wind.
    """
    print(f"  [4b/6] Bandpass {bandpass_low}–{bandpass_high} Hz ...")
    sos = butter(4, [bandpass_low, bandpass_high], btype="bandpass", fs=sr, output="sos")
    y_cleaned = sosfilt(sos, y_gated)

    peak = np.max(np.abs(y_cleaned))
    if peak > 0:
        y_cleaned = y_cleaned / peak * 0.95
    print(f"     Done. Output peak amplitude: {float(np.max(np.abs(y_cleaned))):.3f}")
    return y_cleaned


def step5_spectrograms(y: np.ndarray, y_harmonic: np.ndarray, y_gated: np.ndarray,
                        y_cleaned: np.ndarray, sr: int,
                        output_dir: str, n_fft: int = 4096) -> dict:
    """
    Step 5: Generate presentation-quality spectrograms for every pipeline stage
    so the 3-stage toggle in the UI shows real intermediate output (not fakes).
    All spectrograms share identical axes for a fair visual comparison.
    """
    print("  [5/6] Generating spectrograms (original / harmonic / gated / cleaned) ...")
    paths = {
        "original": os.path.join(output_dir, "spectrogram_original.png"),
        "harmonic": os.path.join(output_dir, "spectrogram_harmonic.png"),
        "gated":    os.path.join(output_dir, "spectrogram_gated.png"),
        "cleaned":  os.path.join(output_dir, "spectrogram_cleaned.png"),
    }
    _save_spectrogram(y,          sr, paths["original"], "Original Recording",                n_fft=n_fft)
    _save_spectrogram(y_harmonic, sr, paths["harmonic"], "After HPSS (harmonic component)",   n_fft=n_fft)
    _save_spectrogram(y_gated,    sr, paths["gated"],    "After Spectral Gate (pre-bandpass)", n_fft=n_fft)
    _save_spectrogram(y_cleaned,  sr, paths["cleaned"],  "Cleaned (HPSS + Gate + Bandpass)",  n_fft=n_fft)

    # Back-compat aliases for existing API consumers that expect *_before / *_after names.
    shutil.copyfile(paths["original"], os.path.join(output_dir, "spectrogram_before.png"))
    shutil.copyfile(paths["cleaned"],  os.path.join(output_dir, "spectrogram_after.png"))

    for label, p in paths.items():
        print(f"     Saved [{label}]: {p}")
    return paths


def step6_energy_ratio(y: np.ndarray, y_cleaned: np.ndarray,
                        sr: int, calls: list, call_types: list, basename: str,
                        n_fft: int = 4096) -> tuple:
    """
    Step 6: In-call vs out-of-call energy ratio (proxy for cleanup).

    This is NOT a true SNR — no clean reference exists for field recordings,
    so we can't compute SDR/SI-SDR here. We compute:
        ratio_dB = 20 * log10(RMS_during_calls / RMS_during_non_calls)
    and report before/after values. A rising ratio can mean a cleaner
    background *or* more aggressive attenuation of non-call audio.
    The synthetic-mix evaluation harness in scripts/eval/ measures
    true SI-SDR against a clean reference — that is the scientific metric;
    this one is just a quick sanity indicator.

    We deliberately do not return any "fundamental frequency" field:
    at n_fft=4096 and sr=48 kHz, FFT bin spacing is ~11.7 Hz, which leaves
    only ~2 bins in the 8-35 Hz elephant-fundamental search range — the
    estimate would quantize to one of two values and be scientifically
    meaningless. Use scripts/eval/ for real pitch analysis if needed.
    """
    print("  [6/6] Computing in-call energy ratio (proxy) ...")

    if not calls:
        print("     No labeled calls — ratio not applicable.")
        snr_before = 0.0
        snr_after = 0.0
        improvement = 0.0
        calls_detected = []
    else:
        snr_before = _compute_snr(y, calls, sr)
        snr_after = _compute_snr(y_cleaned, calls, sr)
        improvement = snr_after - snr_before

        print(f"     Ratio before: {snr_before:.1f} dB")
        print(f"     Ratio after:  {snr_after:.1f} dB")
        print(f"     Improvement: {improvement:+.1f} dB (proxy — not true SNR)")

        calls_detected = []
        for i, (start, end) in enumerate(calls):
            calls_detected.append({
                "start_time": round(start, 3),
                "end_time": round(end, 3),
                "call_type": call_types[i] if i < len(call_types) else "unknown",
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
                       oversubtraction: float = 1.5,
                       residual_floor: float = 0.1) -> dict:
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

    # Adaptive parameter tuning for difficult recordings (must happen BEFORE HPSS
    # since kernel_size is an HPSS parameter):
    if not calls:
        hpss_kernel_size = min(hpss_kernel_size, 17)
        oversubtraction = min(oversubtraction, 0.8)
        print(f"  Adaptive: no calls → kernel_size={hpss_kernel_size}, "
              f"oversubtraction={oversubtraction}")
    else:
        rough_snr = _compute_snr(y, calls, sr)
        if rough_snr < -5:
            # Extreme low SNR: noise strongly dominates the call. Be VERY gentle
            # with the gate and raise the residual floor so the rumble is not
            # annihilated (e.g. 99-37_airplane_and_vehicle_01.wav — both airplane
            # and vehicle noise are themselves harmonic, so HPSS can't fully
            # separate them).
            hpss_kernel_size = min(hpss_kernel_size, 17)
            oversubtraction = min(oversubtraction, 0.7)
            residual_floor = max(residual_floor, 0.3)
            print(f"  Adaptive: extreme low ratio ({rough_snr:.1f} dB) → "
                  f"kernel={hpss_kernel_size}, oversub={oversubtraction}, "
                  f"floor={residual_floor} (preserve weak call)")
        elif rough_snr < 0:
            hpss_kernel_size = min(hpss_kernel_size, 21)
            oversubtraction = min(oversubtraction, 1.0)
            residual_floor = max(residual_floor, 0.15)
            print(f"  Adaptive: low in-call/out ratio ({rough_snr:.1f} dB) → "
                  f"kernel_size={hpss_kernel_size}, oversubtraction={oversubtraction}, "
                  f"floor={residual_floor}")

    # Step 3 (now before step 2): HPSS — separate harmonic (calls) from percussive (noise).
    # We run HPSS FIRST so the noise profile can be built from the harmonic signal's
    # silent gaps — same scale as what we'll subtract from in step 4a. This fixes
    # the magnitude-mismatch bug in the previous version.
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

    # Step 2: Noise profile — built from the HARMONIC signal's non-call segments so
    # it's on the same magnitude scale as the STFT we subtract from in step 4a.
    noise_profile = step2_noise_profile(y_harmonic, sr, calls, n_fft=n_fft, label="harmonic")

    # Step 4a: Spectral gating on the harmonic signal
    y_gated = step4a_spectral_gate(y_harmonic, sr, noise_profile,
                                   n_fft=n_fft, oversubtraction=oversubtraction,
                                   residual_floor=residual_floor)

    # Step 4b: Bandpass filter to produce the final cleaned output
    y_cleaned = step4b_bandpass(y_gated, sr,
                                bandpass_low=bandpass_low, bandpass_high=bandpass_high)

    # Step 5: Spectrograms for every stage (real intermediates, not fakes)
    step5_spectrograms(y, y_harmonic, y_gated, y_cleaned, sr, output_dir, n_fft=n_fft)

    # Step 6: In-call energy ratio (proxy metric)
    snr_before, snr_after, improvement, calls_detected = step6_energy_ratio(
        y, y_cleaned, sr, calls, call_types, basename, n_fft=n_fft
    )

    # Write all stage outputs so the frontend stage toggle can serve real audio
    print("  Writing output files ...")
    shutil.copy(wav_path, os.path.join(output_dir, "original.wav"))
    sf.write(os.path.join(output_dir, "harmonic.wav"), y_harmonic, sr)
    sf.write(os.path.join(output_dir, "gated.wav"),    y_gated,    sr)
    sf.write(os.path.join(output_dir, "cleaned.wav"),  y_cleaned,  sr)

    results = {
        "filename": basename,
        "sample_rate": sr,
        "duration_seconds": round(len(y) / sr, 2),
        # Legacy "snr_*" field names retained for API back-compat.
        # These are actually an in-call / out-of-call energy ratio (dB), NOT true SNR.
        # See metric_note below, and scripts/eval/ for real SI-SDR on synthetic mixes.
        "snr_before_db": round(snr_before, 2),
        "snr_after_db": round(snr_after, 2),
        "snr_improvement_db": round(improvement, 2),
        "metric_note": "snr_* fields are an in-call/out-of-call energy ratio (proxy), not a true SNR. Real SI-SDR in scripts/eval/.",
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
