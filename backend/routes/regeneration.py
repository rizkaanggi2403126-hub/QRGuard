from pathlib import Path
from fastapi import APIRouter, Form, HTTPException
from database.db import get_connection
from services.qr_regenerator import regenerate_and_validate_qr

router = APIRouter(prefix="/api/regenerate", tags=["Regeneration"])
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "outputs"


@router.post("/{record_id}")
async def customize_regeneration(
    record_id: int,
    ec_level: str = Form("M"),
    box_size: int = Form(10),
    fill_color: str = Form("#000000"),
    back_color: str = Form("#FFFFFF"),
):
    conn = get_connection()
    row = conn.execute("SELECT * FROM analysis_history WHERE id = ?", (record_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Data analisis tidak ditemukan.")

    if not row["payload"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Payload tidak tersedia. QR Code tidak dapat diregenerasi.")

    orig_stem = Path(row["saved_original_path"]).stem
    regen_filename = f"regen_{orig_stem}.png"
    regen_path = OUTPUT_DIR / regen_filename

    regen_res = regenerate_and_validate_qr(
        payload=row["payload"],
        output_path=str(regen_path),
        box_size=box_size,
        fill_color=fill_color,
        back_color=back_color,
        error_correction=ec_level,
    )
    saved_regen_rel = f"/outputs/{regen_filename}"

    conn.execute(
        """
        UPDATE analysis_history
        SET saved_regenerated_path = ?,
            regeneration_status = 'Berhasil',
            validation_status = ?
        WHERE id = ?
        """,
        ("Tervalidasi" if regen_res["validated"] else "Gagal Validasi", record_id),
    )
    conn.commit()
    conn.close()

    return {
        "regenerated": regen_res["regenerated"],
        "validated": regen_res["validated"],
        "url": saved_regen_rel,
        "error_correction": regen_res["error_correction"],
    }