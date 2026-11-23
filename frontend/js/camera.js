let cameraStream = null;

async function startCamera() {
  const video = document.getElementById("camera-video");
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "environment", width: { ideal: 1280 }, height: { ideal: 720 } }
    });
    video.srcObject = cameraStream;
    video.style.display = "block";
  } catch (err) {
    alert("Tidak dapat mengakses kamera. Pastikan izin kamera diberikan dan halaman diakses melalui HTTPS atau localhost.");
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(track => track.stop());
    cameraStream = null;
  }
  const video = document.getElementById("camera-video");
  if (video) video.style.display = "none";
}

async function captureAndAnalyze() {
  const video = document.getElementById("camera-video");
  if (!cameraStream || video.readyState !== 4) {
    alert("Aktifkan kamera terlebih dahulu.");
    return;
  }
  const canvas = document.getElementById("camera-canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d").drawImage(video, 0, 0);

  canvas.toBlob(async (blob) => {
    const formData = new FormData();
    formData.append("file", blob, `camera_scan_${Date.now()}.png`);
    formData.append("input_method", "camera");
    await sendAnalysisRequest(`${API_BASE}/api/analyze/image`, formData);
  }, "image/png");
}