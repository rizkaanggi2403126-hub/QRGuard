const API_BASE = window.QRGUARD_CONFIG.API_BASE_URL;
let conditionChartInstance = null;

function navigateTo(sectionId) {
  document.querySelectorAll(".view-section").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.target === sectionId);
  });
  document.getElementById(sectionId).classList.add("active");

  if (sectionId === "dashboard") loadDashboardStats();
  if (sectionId === "history") loadHistory();
  if (sectionId !== "analyzer") stopCamera();
}

document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => navigateTo(btn.dataset.target));
});

async function loadDashboardStats() {
  try {
    const res = await fetch(`${API_BASE}/api/history/stats`);
    const data = await res.json();

    document.getElementById("stat-total").textContent = data.total_analyzed;
    document.getElementById("stat-decoded").textContent = data.decoded_success;
    document.getElementById("stat-failed").textContent = data.detected_failed;
    document.getElementById("stat-regen").textContent = data.regenerated_success;

    const tbody = document.getElementById("recent-history-body");
    if (data.recent_history.length === 0) {
      tbody.innerHTML = `<tr><td colspan="4" style="color:var(--text-muted);">Belum ada data analisis.</td></tr>`;
    } else {
      tbody.innerHTML = data.recent_history.map(item => `
        <tr>
          <td>${item.created_at}</td>
          <td>${escapeHtml(item.original_filename)}</td>
          <td>${escapeHtml(item.image_condition)}</td>
          <td>${escapeHtml(item.decoding_status)}</td>
        </tr>
      `).join("");
    }

    renderConditionChart(data.condition_distribution);
  } catch (err) {
    console.error("Gagal memuat statistik:", err);
  }
}

function renderConditionChart(dist) {
  const ctx = document.getElementById("conditionChart").getContext("2d");
  const labels = Object.keys(dist);
  const values = Object.values(dist);

  if (conditionChartInstance) conditionChartInstance.destroy();
  conditionChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels.length ? labels : ["Belum Ada Data"],
      datasets: [{
        data: values.length ? values : [1],
        backgroundColor: labels.length ? ["#2563eb", "#16a34a", "#d97706", "#dc2626", "#6366f1"] : ["#e2e8f0"]
      }]
    },
    options: { responsive: true, plugins: { legend: { position: "bottom" } } }
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>"']/g, m => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[m]));
}

lucide.createIcons();
loadDashboardStats();