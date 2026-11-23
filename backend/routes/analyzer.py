import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from database.db import get_connection
from services.image_analyzer import analyze_image_quality
from services.image_preprocessing import apply_preprocessing
from services.pdf_processor import get_pdf_info, render_pdf_page_to_image
from services.qr_detector_decoder import detect_and_decode_qr
from services.qr_regenerator import regenerate_and_validate_qr

router = APIRouter(prefix="/api/analyze", tags=["Analyzer"])

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def sanitize_filename(filename: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9._-]", "_", Path(filename).name)
    return f"{uuid.uuid4().hex[:8]}_{clean}"


def determine_overall_condition(visual_issues: list[str], detected: bool, decoded: bool) -> str:
    if not detected:
        return "Tidak Terdeteksi"
    if detected and not decoded:
        return "Terdeteksi tetapi Tidak Dapat Dibaca"
    if len(visual_issues) == 0:
        return "Kondisi Baik"
    if len(visual_issues) <= 2:
        return "Terdeteksi dengan Gangguan"
    return "Kualitas Gambar Rendah"


def _run_full_pipeline(
    image_path: Path,
    original_filename: str,
    input_method: str,
    ec_level: str = "M",
    box_size: int = 10,
    fill_color: str = "#000000",
    back_color: str = "#FFFFFF",
) -> dict:
    analysis = analyze_image_quality(str(image_path))
    qr_result = detect_and_decode_qr(str(image_path))
    condition = determine_overall_condition(
        analysis["visual_issues"], qr_result["detected"], qr_result["decoded"]
    )

    regen_info = {
        "regenerated": False,
        "validated": False,
        "url": None,
        "error_correction": ec_level,
    }
    saved_regen_rel = None

    if qr_result["decoded"] and qr_result["payload"]:
        regen_filename = f"regen_{image_path.stem}.png"
        regen_path = OUTPUT_DIR / regen_filename
        regen_res = regenerate_and_validate_qr(
            payload=qr_result["payload"],
            output_path=str(regen_path),
            box_size=box_size,
            fill_color=fill_color,
            back_color=back_color,
            error_correction=ec_level,
        )
        saved_regen_rel = f"/outputs/{regen_filename}"
        regen_info = {
            "regenerated": regen_res["regenerated"],
            "validated": regen_res["validated"],
            "url": saved_regen_rel,
            "error_correction": regen_res["error_correction"],
        }

    saved_orig_rel = f"/uploads/{image_path.name}"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO analysis_history (
            created_at, original_filename, saved_original_path, saved_preprocessed_path,
            saved_regenerated_path, input_method, image_condition, detection_status,
            decoding_status, payload, payload_type, preprocessing_used,
            preprocessing_methods, regeneration_status, validation_status, metrics_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            created_at,
            original_filename,
            saved_orig_rel,
            None,
            saved_regen_rel,
            input_method,
            condition,
            "Terdeteksi" if qr_result["detected"] else "Tidak Terdeteksi",
            "Berhasil Dibaca" if qr_result["decoded"] else "Gagal Dibaca",
            qr_result["payload"],
            qr_result["payload_type"],
            0,
            "",
            "Berhasil" if regen_info["regenerated"] else "Tidak Dilakukan",
            "Tervalidasi" if regen_info["validated"] else "Belum Tervalidasi",
            json.dumps(analysis),
        ),
    )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "record_id": record_id,
        "created_at": created_at,
        "input_method": input_method,
        "original_image_url": saved_orig_rel,
        "preprocessed_image_url": None,
        "regenerated_image_url": saved_regen_rel,
        "condition": condition,
        "analysis": analysis,
        "qr_result": qr_result,
        "regeneration": regen_info,
    }


@router.post("/image")
async def analyze_uploaded_image(
    file: UploadFile = File(...),
    input_method: str = Form("upload"),
    ec_level: str = Form("M"),
    box_size: int = Form(10),
    fill_color: str = Form("#000000"),
    back_color: str = Form("#FFFFFF"),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise HTTPException(status_code=400, detail="Format gambar tidak didukung. Gunakan PNG, JPG, JPEG, BMP, atau WEBP.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Ukuran file melebihi batas maksimum 10 MB.")

    safe_name = sanitize_filename(file.filename or "capture.png")
    saved_path = UPLOAD_DIR / safe_name
    saved_path.write_bytes(content)

    try:
        return _run_full_pipeline(
            saved_path, file.filename or safe_name, input_method, ec_level, box_size, fill_color, back_color
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal memproses citra: {str(exc)}")


@router.post("/pdf/inspect")
async def inspect_pdf(file: UploadFile = File(...)):
    if Path(file.filename or "").suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="File harus berformat PDF.")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="Ukuran file PDF melebihi 10 MB.")

    safe_name = sanitize_filename(file.filename or "document.pdf")
    saved_pdf = UPLOAD_DIR / safe_name
    saved_pdf.write_bytes(content)

    info = get_pdf_info(str(saved_pdf))
    return {"pdf_server_filename": safe_name, "original_filename": file.filename, "page_count": info["page_count"]}


@router.post("/pdf/process")
async def process_pdf_page(
    pdf_server_filename: str = Form(...),
    original_filename: str = Form(...),
    page_number: int = Form(1),
    ec_level: str = Form("M"),
):
    pdf_path = UPLOAD_DIR / Path(pdf_server_filename).name
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Dokumen PDF tidak ditemukan.")

    rendered_name = f"pdf_p{page_number}_{pdf_path.stem}.png"
    rendered_path = UPLOAD_DIR / rendered_name
    pdf_render_info = render_pdf_page_to_image(str(pdf_path), page_number, str(rendered_path))

    result = _run_full_pipeline(
        rendered_path,
        f"{original_filename} (Halaman {page_number})",
        "pdf",
        ec_level=ec_level,
    )
    result["multi_qr_detected"] = pdf_render_info["multi_qr_detected"]
    return result


@router.post("/preprocess/{record_id}")
async def preprocess_existing_record(
    record_id: int,
    methods: str = Form(...),  # comma-separated: grayscale,contrast,adaptive_threshold
    ec_level: str = Form("M"),
):
    conn = get_connection()
    row = conn.execute("SELECT * FROM analysis_history WHERE id = ?", (record_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Riwayat analisis tidak ditemukan.")

    orig_rel = row["saved_original_path"].lstrip("/")
    orig_path = BASE_DIR / orig_rel
    if not orig_path.exists():
        conn.close()
        raise HTTPException(status_code=404, detail="Gambar asli tidak ditemukan di server.")

    method_list = [m.strip() for m in methods.split(",") if m.strip()]
    existing_metrics = json.loads(row["metrics_json"]) if row["metrics_json"] else {}
    points = existing_metrics.get("points")

    prep_filename = f"prep_{orig_path.stem}.png"
    prep_path = OUTPUT_DIR / prep_filename
    apply_preprocessing(str(orig_path), str(prep_path), method_list, points=points)

    qr_result = detect_and_decode_qr(str(prep_path))
    analysis = analyze_image_quality(str(orig_path))
    condition = determine_overall_condition(
        analysis["visual_issues"], qr_result["detected"], qr_result["decoded"]
    )

    saved_regen_rel = row["saved_regenerated_path"]
    regen_info = {
        "regenerated": bool(saved_regen_rel),
        "validated": row["validation_status"] == "Tervalidasi",
        "url": saved_regen_rel,
        "error_correction": ec_level,
    }

    if qr_result["decoded"] and qr_result["payload"]:
        regen_filename = f"regen_{orig_path.stem}.png"
        regen_path = OUTPUT_DIR / regen_filename
        regen_res = regenerate_and_validate_qr(
            payload=qr_result["payload"],
            output_path=str(regen_path),
            error_correction=ec_level,
        )
        saved_regen_rel = f"/outputs/{regen_filename}"
        regen_info = {
            "regenerated": regen_res["regenerated"],
            "validated": regen_res["validated"],
            "url": saved_regen_rel,
            "error_correction": regen_res["error_correction"],
        }

    saved_prep_rel = f"/outputs/{prep_filename}"
    conn.execute(
        """
        UPDATE analysis_history
        SET saved_preprocessed_path = ?,
            saved_regenerated_path = ?,
            image_condition = ?,
            detection_status = ?,
            decoding_status = ?,
            payload = ?,
            payload_type = ?,
            preprocessing_used = 1,
            preprocessing_methods = ?,
            regeneration_status = ?,
            validation_status = ?
        WHERE id = ?
        """,
        (
            saved_prep_rel,
            saved_regen_rel,
            condition,
            "Terdeteksi" if qr_result["detected"] else "Tidak Terdeteksi",
            "Berhasil Dibaca" if qr_result["decoded"] else "Gagal Dibaca",
            qr_result["payload"],
            qr_result["payload_type"],
            ", ".join(method_list),
            "Berhasil" if regen_info["regenerated"] else "Tidak Dilakukan",
            "Tervalidasi" if regen_info["validated"] else "Belum Tervalidasi",
            record_id,
        ),
    )
    conn.commit()
    conn.close()

    return {
        "record_id": record_id,
        "original_image_url": row["saved_original_path"],
        "preprocessed_image_url": saved_prep_rel,
        "regenerated_image_url": saved_regen_rel,
        "condition": condition,
        "analysis": analysis,
        "qr_result": qr_result,
        "regeneration": regen_info,
    }