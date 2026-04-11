import argparse
import json
from pathlib import Path

from backend.db.database import init_db
from backend.pipeline.process_calls import process_batch



def main() -> None:
    parser = argparse.ArgumentParser(description="Process HPSS calls using EchoMap Stage 2/3 pipeline")
    parser.add_argument("metadata_json", help="Path to JSON array with call_id/start_sec/end_sec")
    args = parser.parse_args()

    metadata_path = Path(args.metadata_json)
    items = json.loads(metadata_path.read_text())

    init_db()
    ids = process_batch(items)
    print(f"Processed {len(ids)} calls")


if __name__ == "__main__":
    main()
