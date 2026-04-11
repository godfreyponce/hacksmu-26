from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.protected import router as protected_router
from backend.api.routes.public import router as public_router
from backend.config import FRONTEND_ORIGIN
from backend.db.database import init_db

app = FastAPI(title="EchoMap API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


app.include_router(public_router)
app.include_router(protected_router)


@app.get("/health")
def health() -> dict:
    return {"ok": True}
