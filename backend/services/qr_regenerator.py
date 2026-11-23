from pathlib import Path
import cv2
import qrcode
from qrcode.constants import (
    ERROR_CORRECT_L,
    ERROR_CORRECT_M,
    ERROR_CORRECT_Q,
    ERROR_CORRECT_H,
)

EC_MAP = {
    "L": ERROR_CORRECT_L,
    "M": ERROR_CORRECT_M,
    "Q": ERROR_CORRECT_Q,
    "H": ERROR_CORRECT_H,
}


def regenerate_and_validate_qr(
    payload: str,
    output_path: str,
    box_size: int = 10,
    fill_color: str = "#000000",
    back_color: str = "#FFFFFF",
    error_correction: str = "M",
) -> dict:
    if not payload:
        raise ValueError("Regenerasi dibatalkan: payload kosong.")

    ec_level = EC_MAP.get(error_correction.upper(), ERROR_CORRECT_M)
    box_size = max(4, min(box_size, 25))

    qr = qrcode.QRCode(
        version=None,
        error_correction=ec_level,
        box_size=box_size,
        border=4,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGB")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path, format="PNG")

    # Validasi ulang QR Code hasil regenerasi
    verify_img = cv2.imread(output_path)
    detector = cv2.QRCodeDetector()
    verified_data, _, _ = detector.detectAndDecode(verify_img)

    is_valid = verified_data == payload
    return {
        "regenerated": True,
        "validated": is_valid,
        "verified_payload": verified_data,
        "error_correction": error_correction.upper(),
        "output_path": output_path,
    }