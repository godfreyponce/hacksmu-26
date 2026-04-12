# EchoMap - Elephant Vocalization Analysis Platform

EchoMap is a full-stack research platform that starts after HPSS and implements:

- Stage 2 spectral gating (`backend/pipeline/denoiser.py`)
- Stage 3 residual cleanup (`backend/pipeline/denoiser.py`)
- Spectrogram generation (`backend/pipeline/spectrogram.py`)
- Gemini vision classification (`backend/pipeline/classifier.py`)
- SQLite persistence (`backend/db/schema.sql`, `backend/db/database.py`)
- FastAPI API (`backend/api/main.py`)
- React research dashboard (`frontend/src`)

## Input Contract

For each call, teammate A provides:

- `data/hpss/{call_id}_hpss.wav`
- metadata JSON fields: `call_id`, `start_sec`, `end_sec`

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cd ..
uvicorn backend.api.main:app --reload
```

### Batch Processing

Use a metadata JSON array:

```json
[
	{ "call_id": "call_001", "start_sec": 2.1, "end_sec": 8.7 }
]
```

Run:

```bash
python3 -m backend.pipeline.run_from_metadata metadata.json
```

Outputs are written to:

- `data/gated/`
- `data/cleaned/`
- `data/spectrograms/`
- `data/echomap.db`

## API Contract

Public:

- `GET /calls`
- `GET /calls/{id}`
- `GET /calls/{id}/audio/{stage}` (`hpss|gated|clean`)
- `GET /calls/{id}/spectrogram/{stage}`
- `GET /stats`

Protected (Auth0 M2M bearer token, or `AUTH_DISABLED=true` for local dev):

- `POST /query`
- `POST /report`

## Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

The frontend expects `VITE_API_URL` to point to FastAPI (default `http://localhost:8000`).
