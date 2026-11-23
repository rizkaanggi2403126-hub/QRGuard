from pathlib import Path
import cv2
import pymupdf as fitz


def get_pdf_info(pdf_path: str) -> dict:
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()
    return {"page_count": page_count}


def render_pdf_page_to_image(pdf_path: str, page_number: int, output_image_path: str) -> dict:
    doc = fitz.open(pdf_path)
    if page_number < 1 or page_number > len(doc):
        doc.close()
        raise ValueError(f"Nomor halaman harus antara 1 dan {len(doc)}.")

    page = doc[page_number - 1]
    pix = page.get_pixmap(dpi=220)
    Path(output_image_path).parent.mkdir(parents=True, exist_ok=True)
    pix.save(output_image_path)
    doc.close()

    # Cek apakah ada multi-QR pada halaman
    img = cv2.imread(output_image_path)
    detector = cv2.QRCodeDetector()
    retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
    multi_qrs = []
    if retval and decoded_info:
        for idx, text in enumerate(decoded_info):
            if text:
                multi_qrs.append({"index": idx + 1, "payload": text})

    return {
        "rendered_image_path": output_image_path,
        "multi_qr_detected": multi_qrs,
    }