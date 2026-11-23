import os
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("DATABASE_PATH", BASE_DIR / "qrguard.db"))


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            saved_original_path TEXT NOT NULL,
            saved_preprocessed_path TEXT,
            saved_regenerated_path TEXT,
            input_method TEXT NOT NULL,
            image_condition TEXT NOT NULL,
            detection_status TEXT NOT NULL,
            decoding_status TEXT NOT NULL,
            payload TEXT,
            payload_type TEXT,
            preprocessing_used INTEGER DEFAULT 0,
            preprocessing_methods TEXT,
            regeneration_status TEXT NOT NULL,
            validation_status TEXT NOT NULL,
            metrics_json TEXT
        )
        """
    )
    conn.commit()
    conn.close()