# Parse calls.csv → call list

import csv
from pathlib import Path
from typing import Any


def load_calls_csv(csv_path: str | Path) -> list[dict[str, Any]]:
    """
    Parse ElephantVoices calls.csv spreadsheet.

    Expected columns:
    - call_id: Unique identifier for the call
    - file: Source WAV filename
    - start_sec: Start time in seconds
    - end_sec: End time in seconds
    - call_type: Type of call (rumble, trumpet, etc.)
    - notes: Additional notes

    Returns list of call records.
    """
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    calls = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            call = {
                'call_id_csv': row.get('call_id') or row.get('Call ID') or row.get('id', ''),
                'file': row.get('file') or row.get('File') or row.get('filename', ''),
                'start_sec': float(row.get('start_sec') or row.get('Start') or row.get('start', 0)),
                'end_sec': float(row.get('end_sec') or row.get('End') or row.get('end', 0)),
                'call_type': row.get('call_type') or row.get('Type') or row.get('type'),
                'notes': row.get('notes') or row.get('Notes') or '',
            }

            # Skip invalid entries
            if call['call_id_csv'] and call['file']:
                calls.append(call)

    return calls


def load_and_validate(csv_path: str | Path, raw_dir: str | Path) -> list[dict[str, Any]]:
    """
    Load calls.csv and validate that source files exist.
    Returns only calls whose source WAV files are present.
    """
    raw_dir = Path(raw_dir)
    calls = load_calls_csv(csv_path)

    valid_calls = []
    missing_files = set()

    for call in calls:
        wav_path = raw_dir / call['file']
        if wav_path.exists():
            call['wav_path'] = str(wav_path)
            valid_calls.append(call)
        else:
            missing_files.add(call['file'])

    if missing_files:
        print(f"Warning: {len(missing_files)} source files not found: {', '.join(list(missing_files)[:5])}...")

    return valid_calls


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python loader.py <path_to_calls.csv> [raw_dir]")
        sys.exit(1)

    csv_file = sys.argv[1]
    raw_directory = sys.argv[2] if len(sys.argv) > 2 else None

    if raw_directory:
        calls = load_and_validate(csv_file, raw_directory)
        print(f"Loaded {len(calls)} valid calls")
    else:
        calls = load_calls_csv(csv_file)
        print(f"Loaded {len(calls)} calls from CSV")

    for call in calls[:5]:
        print(f"  {call['call_id_csv']}: {call['file']} ({call['start_sec']}-{call['end_sec']}s)")
