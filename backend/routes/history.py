from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from database.db import get_connection

router = APIRouter(prefix="/api/history", tags=["History"])
BASE_DIR = Path(__file__).resolve().parent.parent


@router.get("/stats")
async def get_dashboard_stats():
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()[0]
    decoded_ok = conn.execute(
        "SELECT COUNT(*) FROM analysis_history WHERE decoding_status = 'Berhasil Dibaca'"
    ).fetchone()[0]
    detected_failed = conn.execute(
        "SELECT COUNT(*) FROM analysis_history WHERE detection_status = 'Terdeteksi' AND decoding_status = 'Gagal Dibaca'"
    ).fetchone()[0]
    regenerated_ok = conn.execute(
        "SELECT COUNT(*) FROM analysis_history WHERE regeneration_status = 'Berhasil'"
    ).fetchone()[0]

    cond_rows = conn.execute(
        "SELECT image_condition, COUNT(*) as count FROM analysis_history GROUP BY image_condition"
    ).fetchall()
    condition_distribution = {row["image_condition"]: row["count"] for row in cond_rows}

    recent_rows = conn.execute(
        "SELECT id, created_at, original_filename, input_method, image_condition, decoding_status, regeneration_status "
        "FROM analysis_history ORDER BY id DESC LIMIT 5"
    ).fetchall()
    conn.close()

    return {
        "total_analyzed": total,
        "decoded_success": decoded_ok,
        "detected_failed": detected_failed,
        "regenerated_success": regenerated_ok,
        "condition_distribution": condition_distribution,
        "recent_history": [dict(r) for r in recent_rows],
    }


@router.get("/")
async def list_history(search: str = Query("", max_length=100)):
    conn = get_connection()
    if search.strip():
        like_term = f"%{search.strip()}%"
        rows = conn.execute(
            """
            SELECT * FROM analysis_history
            WHERE original_filename LIKE ? OR created_at LIKE ?
            ORDER BY id DESC
            """,
            (like_term, like_term),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM analysis_history ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/{record_id}")
async def get_history_detail(record_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM analysis_history WHERE id = ?", (record_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Riwayat tidak ditemukan.")
    return dict(row)


@router.delete("/{record_id}")
async def delete_history(record_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM analysis_history WHERE id = ?", (record_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Riwayat tidak ditemukan.")

    for col in ["saved_original_path", "saved_preprocessed_path", "saved_regenerated_path"]:
        if row[col]:
            target = BASE_DIR / row[col].lstrip("/")
            if target.exists():
                target.unlink()

    conn.execute("DELETE FROM analysis_history WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    return {"deleted": True, "id": record_id}