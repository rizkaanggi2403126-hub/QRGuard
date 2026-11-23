import re
import cv2


def classify_payload(payload: str) -> str:
    if not payload:
        return "Tidak Diketahui"
    lower = payload.strip().lower()
    if re.match(r"^https?://", lower):
        return "URL / Tautan Web"
    if lower.startswith("wifi:"):
        return "Konfigurasi Wi-Fi"
    if lower.startswith("begin:vcard"):
        return "Kontak (vCard)"
    if lower.startswith("mailto:"):
        return "Alamat Email"
    if lower.startswith("tel:"):
        return "Nomor Telepon"
    if payload.isdigit():
        return "Numerik"
    return "Teks Biasa"


def detect_and_decode_qr(image_path: str) -> dict:
    img = cv2.imread(image_path)
    if img is None:
        return {
            "detected": False,
            "decoded": False,
            "payload": None,
            "payload_type": None,
            "points": None,
            "message": "Citra gagal dimuat.",
        }

    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(img)

    # Fallback grayscale jika BGR gagal
    if not data:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        data_gray, points_gray, _ = detector.detectAndDecode(gray)
        if data_gray:
            data = data_gray
            points = points_gray
        elif points is None and points_gray is not None:
            points = points_gray

    has_points = points is not None and len(points) > 0
    formatted_points = points[0].tolist() if has_points else None

    if data:
        return {
            "detected": True,
            "decoded": True,
            "payload": data,
            "payload_type": classify_payload(data),
            "points": formatted_points,
            "message": "QR Code berhasil dideteksi dan payload berhasil dibaca.",
        }

    if has_points:
        return {
            "detected": True,
            "decoded": False,
            "payload": None,
            "payload_type": None,
            "points": formatted_points,
            "message": (
                "Pola QR Code berhasil terdeteksi, tetapi payload gagal dibaca. "
                "Kemungkinan jumlah codeword yang rusak melebihi kapasitas koreksi kesalahan "
                "Reed-Solomon pada QR Code asli, atau modul terlalu buram/tertutup. "
                "Silakan coba fitur Image Preprocessing atau unggah ulang gambar yang lebih jelas."
            ),
        }

    return {
        "detected": False,
        "decoded": False,
        "payload": None,
        "payload_type": None,
        "points": None,
        "message": (
            "QR Code tidak terdeteksi pada gambar. Pastikan finder pattern (tiga kotak sudut) "
            "terlihat utuh, pencahayaan cukup, dan posisi kamera tidak terlalu miring."
        ),
    }