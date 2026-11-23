async function loadHistory() {
  const query = document.getElementById("history-search").value;
  const res = await fetch(`${API_BASE}/api/history/?search=${encodeURIComponent(query)}`);
  const rows = await res.json();

  const tbody = document.getElementById("history-table-body");
  if (rows.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="color:var(--text-muted);">Tidak ada riwayat ditemukan.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${r.created_at}</td>
      <td>${escapeHtml(r.original_filename)}</td>
      <td>${escapeHtml(r.input_method.toUpperCase())}</td>
      <td>${escapeHtml(r.image_condition)}</td>
      <td>${escapeHtml(r.decoding_status)}</td>
      <td>${escapeHtml(r.regeneration_status)}</td>
      <td style="display:flex; gap:0.4rem;">
        ${r.saved_regenerated_path ? `<a class="btn btn-outline" href="${API_BASE}${r.saved_regenerated_path}" download="QRGuard_${r.id}.png">Unduh</a>` : ""}
        <button class="btn btn-danger" onclick="deleteHistoryItem(${r.id})">Hapus</button>
      </td>
    </tr>
  `).join("");
}

async function deleteHistoryItem(id) {
  if (!confirm("Hapus riwayat analisis ini beserta file gambarnya?")) return;
  await fetch(`${API_BASE}/api/history/${id}`, { method: "DELETE" });
  loadHistory();
}