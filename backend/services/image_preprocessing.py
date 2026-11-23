from pathlib import Path
import cv2
import numpy as np


def apply_preprocessing(
    input_path: str,
    output_path: str,
    methods: list[str],
    points: list[list[float]] | None = None,
) -> str:
    img = cv2.imread(input_path)
    if img is None:
        raise ValueError("Gambar tidak valid untuk preprocessing.")

    # Konversi awal ke grayscale jika dibutuhkan operasi biner/kontras
    if any(m in methods for m in ["grayscale", "threshold", "adaptive_threshold", "contrast"]):
        processed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        processed = img.copy()

    if "resize" in methods:
        h, w = processed.shape[:2]
        if max(h, w) < 500:
            scale = 500 / max(h, w)
            processed = cv2.resize(
                processed,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_CUBIC,
            )

    if "denoise" in methods:
        processed = cv2.GaussianBlur(processed, (5, 5), 0)

    if "contrast" in methods:
        if len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        processed = clahe.apply(processed)

    if "sharpen" in methods:
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
        processed = cv2.filter2D(processed, -1, kernel)

    if "perspective" in methods and points and len(points) == 4:
        if len(processed.shape) == 2:
            processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        src_pts = np.array(points, dtype="float32")
        side = 450
        dst_pts = np.array(
            [[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]],
            dtype="float32",
        )
        matrix = cv2.getPerspectiveTransform(src_pts, dst_pts)
        processed = cv2.warpPerspective(processed, matrix, (side, side))

    if "threshold" in methods:
        if len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        _, processed = cv2.threshold(processed, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if "adaptive_threshold" in methods:
        if len(processed.shape) == 3:
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        processed = cv2.adaptiveThreshold(
            processed, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 5
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(output_path, processed)
    return output_path