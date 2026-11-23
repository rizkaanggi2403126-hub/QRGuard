let cameraStream = null;

function showCameraAlert(message) {
  const alertBox = document.getElementById("camera-alert-box");
  if (!alertBox) {
    alert(message);
    return;
  }
  alertBox.innerHTML = `<strong>Peringatan Kamera:</strong> ${message}`;
  alertBox.style.display = "block";
}

function clearCameraAlert() {
  const alertBox = document.getElementById("camera-alert-box");
  if (alertBox) {
    alertBox.style.display = "none";
    alertBox.innerHTML = "";
  }
}

function updateCameraButtons(isActive) {
  const btnCapture = document.getElementById("btn-capture-camera");
  const btnRescan = document.getElementById("btn-rescan-camera");

  if (btnCapture) {
    btnCapture.style.display = isActive ? "inline-flex" : "none";
    btnCapture.disabled = !isActive;
  }
  if (btnRescan) {
    btnRescan.style.display = isActive ? "none" : "inline-flex";
  }
}

async function startCamera() {
  clearCameraAlert();

  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showCameraAlert("Browser tidak mendukung akses kamera atau halaman tidak dibuka melalui HTTPS / localhost.");
    updateCameraButtons(false);
    return;
  }

  try {
    stopCamera();
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });

    const video = document.getElementById("camera-video");
    video.srcObject = cameraStream;
    video.style.display = "block";
    await video.play();

    updateCameraButtons(true);
  } catch (err) {
    updateCameraButtons(false);
    showCameraAlert(`Akses kamera belum diizinkan atau gagal dibuka (${err.message}). Klik "Scan Ulang" setelah mengizinkan kamera di browser.`);
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }

  const video = document.getElementById("camera-video");
  if (video) {
    video.pause();
    video.srcObject = null;
    video.style.display = "none";
  }

  updateCameraButtons(false);
}

function captureFrameToBlob() {
  return new Promise((resolve, reject) => {
    const video = document.getElementById("camera-video");
    const canvas = document.getElementById("camera-canvas");

    if (!cameraStream || !video || video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
      reject(new Error("Kamera belum siap atau frame video kosong. Klik 'Scan Ulang' untuk menyalakan kamera."));
      return;
    }

    try {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        reject(new Error("Gagal menginisialisasi kanvas untuk menangkap gambar kamera."));
        return;
      }

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => {
          if (!blob || blob.size === 0) {
            reject(new Error("Gagal menangkap gambar dari kamera (hasil tangkapan kosong)."));
            return;
          }
          resolve(blob);
        },
        "image/png",
        1.0
      );
    } catch (err) {
      reject(new Error(`Gagal menangkap gambar dari kamera: ${err.message}`));
    }
  });
}

async function captureAndAnalyze() {
  clearCameraAlert();

  try {
    const blob = await captureFrameToBlob();

    // Matikan kamera otomatis setelah frame berhasil ditangkap dan tampilkan tombol "Scan Ulang"
    stopCamera();

    const file = new File([blob], `camera_capture_${Date.now()}.png`, { type: "image/png" });
    const formData = new FormData();
    formData.append("file", file);
    formData.append("input_method", "camera");

    await sendAnalysisRequest(`${API_BASE}/api/analyze/image`, formData);
  } catch (err) {
    // Tampilkan peringatan jika gagal menangkap gambar dari kamera (bukan gagal deteksi QR di backend)
    showCameraAlert(err.message || "Gagal menangkap gambar dari kamera.");
  }
}

// Otomatis matikan kamera jika berpindah menu sidebar
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.getAttribute("data-target") !== "analyzer") {
        stopCamera();
      }
    });
  });
});