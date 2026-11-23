import os
from pathlib import Path
import cv2
import numpy as np
from PIL import Image


def analyze_image_quality(image_path: str) -> dict:
    path_obj = Path(image_path)
    file_size_bytes = os.path.getsize(image_path)

    with Image.open(image_path) as pil_img:
        img_format = pil_img.format or path_obj.suffix.replace(".", "").upper()
        width, height = pil_img.size
        dpi = pil_img.info.get("dpi", (72, 72))
        resolution = f"{int(dpi[0])}x{int(dpi[1])} DPI"

    img_bgr = cv2.imread(image_path)
    if img_bgr is None:
        raise ValueError("File citra tidak dapat dibaca oleh OpenCV.")

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Brightness (0 - 255)
    brightness = float(np.mean(gray))

    # 2. Contrast (RMS Contrast / Std Dev)
    contrast = float(np.std(gray))

    # 3. Sharpness / Blur (Variance of Laplacian)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    # 4. Estimasi Noise (Selisih dengan Gaussian Blur)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    noise_level = float(np.mean(np.abs(gray.astype(np.float32) - blurred.astype(np.float32))))

    # 5. Estimasi Kemiringan (Skew) & Perspektif dari kontur utama
    skew_angle = 0.0
    perspective_distorted = False
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        if cv2.contourArea(largest) > (width * height * 0.05):
            rect = cv2.minAreaRect(largest)
            angle = rect[2]
            if angle < -45:
                angle += 90
            skew_angle = round(float(angle), 2)

            peri = cv2.arcLength(largest, True)
            approx = cv2.approxPolyDP(largest, 0.04 * peri, True)
            if len(approx) == 4 and not cv2.isContourConvex(approx):
                perspective_distorted = True

    # 6. Identifikasi Permasalahan Visual
    issues = []
    if laplacian_var < 80.0:
        issues.append("Gambar QR Code buram (ketajaman rendah)")
    if contrast < 38.0:
        issues.append("Kontras QR Code rendah")
    if brightness < 55.0:
        issues.append("Gambar QR Code terlalu gelap")
    elif brightness > 215.0:
        issues.append("Gambar QR Code terlalu terang / overexposed")
    if noise_level > 14.0:
        issues.append("Terdapat noise / bintik visual cukup tinggi")
    if abs(skew_angle) > 7.0:
        issues.append(f"QR Code miring ({skew_angle}°)")
    if perspective_distorted:
        issues.append("Terindikasi distorsi perspektif")

    return {
        "basic_info": {
            "filename": path_obj.name,
            "format": img_format,
            "dimensions": f"{width} x {height} px",
            "width": width,
            "height": height,
            "file_size_kb": round(file_size_bytes / 1024, 2),
            "resolution": resolution,
        },
        "quality_metrics": {
            "brightness": round(brightness, 2),
            "contrast": round(contrast, 2),
            "sharpness_laplacian": round(laplacian_var, 2),
            "noise_estimate": round(noise_level, 2),
            "skew_angle_deg": skew_angle,
            "perspective_warning": perspective_distorted,
        },
        "visual_issues": issues,
    }