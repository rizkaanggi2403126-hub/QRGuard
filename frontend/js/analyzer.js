let currentRecordId = null;
let currentPdfServerFile = null;
let currentPdfOriginalName = null;

function switchInputTab(tabId, btnEl) {
  document.querySelectorAll(".input-tab").forEach(el => el.style.display = "none");
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
  document.getElementById(tabId).style.display = "block";
  btnEl.classList.add("active");
  if (tabId !== "tab-camera") stopCamera();
}

async function submitImageAnalysis() {
  const fileInput = document.getElementById("image-input");
  if (!fileInput.files.length) return alert("Pilih file gambar terlebih dahulu.");

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("input_method", "upload");
  await sendAnalysisRequest(`${API_BASE}/api/analyze/image`, formData);
}

async function inspectPdfFile() {
  const pdfInput = document.getElementById("pdf-input");
  if (!pdfInput.files.length) return alert("Pilih dokumen PDF terlebih dahulu.");

  const formData = new FormData();
  formData.append("file", pdfInput.files[0]);

  const res = await fetch(`${API_BASE}/api/analyze/pdf/inspect`, { method: "POST", body: formData });
  const data = await res.json();
  if (!res.ok) return alert(data.detail || "Gagal membaca PDF.");

  currentPdfServerFile = data.pdf_server_filename;
  currentPdfOriginalName = data.original_filename;

  const select = document.getElementById("pdf-page-select");
  select.innerHTML = "";
  for (let i = 1; i <= data.page_count; i++) {
    select.innerHTML += `<option value="${i}">Halaman ${i}</option>`;
  }
  document.getElementById("pdf-page-selector").style.display = "block";
}

async function submitPdfPageAnalysis() {
  const pageNum = document.getElementById("pdf-page-select").value;
  const formData = new FormData();
  formData.append("pdf_server_filename", currentPdfServerFile);
  formData.append("original_filename", currentPdfOriginalName);
  formData.append("page_number", pageNum);
  await sendAnalysisRequest(`${API_BASE}/api/analyze/pdf/process`, formData);
}

async function sendAnalysisRequest(url, formData) {
  try {
    const res = await fetch(url, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) return alert(data.detail || "Terjadi kesalahan saat analisis.");
    renderAnalysisResult(data);
  } catch (err) {
    alert("Gagal terhubung ke server backend.");
  }
}

function renderAnalysisResult(data) {
  currentRecordId = data.record_id;
  document.getElementById("analysis-result-container").style.display = "block";

  const badge = document.getElementById("res-condition-badge");
  badge.textContent = data.condition;
  badge.className = "badge " + (
    data.condition === "Kondisi Baik" ? "badge-success" :
    data.condition.includes("Gangguan") ? "badge-warning" : "badge-danger"
  );

  // Gambar Asli
  document.getElementById("res-orig-img").src = `${API_BASE}${data.original_image_url}`;
  const b = data.analysis.basic_info;
  document.getElementById("res-basic-info").textContent = `${b.format} | ${b.dimensions} | ${b.file_size_kb} KB | ${b.resolution}`;

  // Gambar Preprocessing
  const prepBox = document.getElementById("res-prep-box");
  if (data.preprocessed_image_url) {
    prepBox.style.display = "block";
    document.getElementById("res-prep-img").src = `${API_BASE}${data.preprocessed_image_url}?t=${Date.now()}`;
  } else {
    prepBox.style.display = "none";
  }

  // Gambar Regenerasi
  const regenBox = document.getElementById("res-regen-box");
  const payloadSection = document.getElementById("payload-section");
  document.getElementById("res-decode-msg").textContent = data.qr_result.message;

  if (data.qr_result.decoded && data.regenerated_image_url) {
    regenBox.style.display = "block";
    document.getElementById("res-regen-img").src = `${API_BASE}${data.regenerated_image_url}?t=${Date.now()}`;
    document.getElementById("res-validation-badge").textContent = data.regeneration.validated
      ? "Tervalidasi: Payload Identik dengan Sumber"
      : "Peringatan Validasi";

    payloadSection.style.display = "block";
    document.getElementById("res-payload-type").textContent = data.qr_result.payload_type;
    document.getElementById("res-payload-text").textContent = data.qr_result.payload;
    document.getElementById("download-regen-btn").href = `${API_BASE}${data.regenerated_image_url}`;
  } else {
    regenBox.style.display = "none";
    payloadSection.style.display = "none";
  }

  // Metrik Kualitas
  const m = data.analysis.quality_metrics;
  document.getElementById("res-metrics-list").innerHTML = `
    <li>Kecerahan (Brightness): <strong>${m.brightness}</strong> / 255</li>
    <li>Kontras (Std Dev): <strong>${m.contrast}</strong></li>
    <li>Ketajaman (Laplacian Var): <strong>${m.sharpness_laplacian}</strong></li>
    <li>Estimasi Noise: <strong>${m.noise_estimate}</strong></li>
    <li>Kemiringan (Skew): <strong>${m.skew_angle_deg}°</strong></li>
  `;

  const issuesList = document.getElementById("res-issues-list");
  if (data.analysis.visual_issues.length === 0) {
    issuesList.innerHTML = `<li style="color:var(--success);">Tidak ditemukan gangguan kualitas visual yang signifikan.</li>`;
  } else {
    issuesList.innerHTML = data.analysis.visual_issues.map(i => `<li>${escapeHtml(i)}</li>`).join("");
  }
}

async function runOptionalPreprocessing() {
  if (!currentRecordId) return;
  const selected = Array.from(document.querySelectorAll(".prep-chk:checked")).map(cb => cb.value);
  if (selected.length === 0) return alert("Pilih minimal satu metode preprocessing.");

  const formData = new FormData();
  formData.append("methods", selected.join(","));
  formData.append("ec_level", document.getElementById("regen-ec").value);

  await sendAnalysisRequest(`${API_BASE}/api/analyze/preprocess/${currentRecordId}`, formData);
}

async function customizeRegenerate() {
  if (!currentRecordId) return;
  const formData = new FormData();
  formData.append("ec_level", document.getElementById("regen-ec").value);
  formData.append("box_size", document.getElementById("regen-size").value);
  formData.append("fill_color", document.getElementById("regen-fg").value);
  formData.append("back_color", document.getElementById("regen-bg").value);

  const res = await fetch(`${API_BASE}/api/regenerate/${currentRecordId}`, { method: "POST", body: formData });
  const data = await res.json();
  if (!res.ok) return alert(data.detail || "Gagal regenerasi ulang.");

  const imgUrl = `${API_BASE}${data.url}?t=${Date.now()}`;
  document.getElementById("res-regen-img").src = imgUrl;
  document.getElementById("download-regen-btn").href = `${API_BASE}${data.url}`;
}