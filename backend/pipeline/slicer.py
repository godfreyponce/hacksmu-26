# pydub: cut 212 clips from 44 wav files

from pathlib import Path
from typing import Any

import librosa
import soundfile as sf


def slice_clip(
    wav_path: str | Path,
    start_sec: float,
    end_sec: float,
    call_id: str,
    out_dir: str | Path
) -> Path:
    """
    Extract a clip from a WAV file and apply HPSS for initial separation.

    Args:
        wav_path: Path to source WAV file
        start_sec: Start time in seconds
        end_sec: End time in seconds
        call_id: Unique identifier for the call
        out_dir: Output directory for clips

    Returns:
        Path to the extracted clip with HPSS applied
    """
    wav_path = Path(wav_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    output_path = out_dir / f"{call_id}_hpss.wav"

    # Load the segment
    y, sr = librosa.load(
        str(wav_path),
        sr=None,
        offset=start_sec,
        duration=end_sec - start_sec
    )

    # Apply HPSS (Harmonic-Percussive Source Separation)
    # Keep harmonic component which contains elephant vocalizations
    y_harmonic, y_percussive = librosa.effects.hpss(y)

    # Save the harmonic component
    sf.write(str(output_path), y_harmonic, sr)

    return output_path


def slice_all_from_calls(
    calls: list[dict[str, Any]],
    raw_dir: str | Path,
    out_dir: str | Path
) -> list[dict[str, Any]]:
    """
    Process all calls, extracting clips with HPSS.

    Args:
        calls: List of call records from loader.py
        raw_dir: Directory containing source WAV files
        out_dir: Output directory for clips

    Returns:
        Updated call records with clip paths
    """
    raw_dir = Path(raw_dir)
    out_dir = Path(out_dir)

    processed = []

    for call in calls:
        wav_path = raw_dir / call['file']
        if not wav_path.exists():
            print(f"Skipping {call['call_id_csv']}: source file not found")
            continue

        try:
            hpss_path = slice_clip(
                wav_path,
                call['start_sec'],
                call['end_sec'],
                call['call_id_csv'],
                out_dir
            )

            call['hpss_path'] = str(hpss_path)
            processed.append(call)
            print(f"Sliced: {call['call_id_csv']}")

        except Exception as e:
            print(f"Error processing {call['call_id_csv']}: {e}")

    return processed


if __name__ == "__main__":
    from loader import load_calls_csv
    import sys

    if len(sys.argv) < 4:
        print("Usage: python slicer.py <calls.csv> <raw_dir> <output_dir>")
        sys.exit(1)

    csv_path = sys.argv[1]
    raw_directory = sys.argv[2]
    output_directory = sys.argv[3]

    calls = load_calls_csv(csv_path)
    processed = slice_all_from_calls(calls, raw_directory, output_directory)
    print(f"\nProcessed {len(processed)} clips")
