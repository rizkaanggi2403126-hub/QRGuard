import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database.db import init_db
from routes import analyzer, history, regeneration

load_dotenv()

app = FastAPI(
    title="QRGuard API",
    description="Sistem Analisis dan Pemulihan QR Code Menggunakan Konsep Reed-Solomon",
    version="1.0.0",
)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
(BASE_DIR / "uploads").mkdir(exist_ok=True)
(BASE_DIR / "outputs").mkdir(exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "uploads")), name="uploads")
app.mount("/outputs", StaticFiles(directory=str(BASE_DIR / "outputs")), name="outputs")

init_db()

app.include_router(analyzer.router)
app.include_router(regeneration.router)
app.include_router(history.router)


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "QRGuard Backend"}