from pathlib import Path

import librosa
import librosa.display
import matplotlib.pyplot as plt
import numpy as np



def generate_spectrogram(audio_path: Path, call_id: str, stage: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{call_id}_{stage}.png"

    y, sr = librosa.load(str(audio_path), sr=None)
    D = librosa.stft(y, n_fft=8192, hop_length=512)
    S_db = librosa.amplitude_to_db(np.abs(D), ref=np.max)

    plt.figure(figsize=(10, 4))
    librosa.display.specshow(
        S_db,
        sr=sr,
        hop_length=512,
        x_axis="time",
        y_axis="linear",
        fmax=1200,
    )
    plt.colorbar(format="%+2.0f dB")
    plt.title(f"{call_id} - {stage}")
    plt.tight_layout()
    plt.savefig(output_path, dpi=160)
    plt.close()

    return output_path
