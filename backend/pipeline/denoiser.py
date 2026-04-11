from pathlib import Path

import librosa
import numpy as np
import scipy.ndimage
import soundfile as sf



def stage2_spectral_gate(hpss_path: Path, call_id: str, start_sec: float, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{call_id}_gated.wav"

    y, sr = librosa.load(str(hpss_path), sr=None)
    noise_region = y[: int(start_sec * sr)]

    if len(noise_region) > sr * 0.5:
        D_signal = librosa.stft(y, n_fft=4096)
        D_noise = librosa.stft(noise_region, n_fft=4096)

        noise_floor = np.mean(np.abs(D_noise), axis=1, keepdims=True)
        gate_mask = (np.abs(D_signal) > noise_floor * 1.5).astype(float)

        D_gated = D_signal * gate_mask
        y_gated = librosa.istft(D_gated)
    else:
        y_gated = y

    sf.write(str(output_path), y_gated, sr)
    return output_path



def stage3_residual_cleanup(gated_path: Path, call_id: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{call_id}_clean.wav"

    y_gated, sr = librosa.load(str(gated_path), sr=None)
    D = librosa.stft(y_gated, n_fft=4096)
    mag = np.abs(D)

    mag_smooth = scipy.ndimage.median_filter(mag, size=(1, 9))

    phase = np.angle(D)
    D_clean = mag_smooth * np.exp(1j * phase)

    y_clean = librosa.istft(D_clean)
    sf.write(str(output_path), y_clean, sr)
    return output_path
