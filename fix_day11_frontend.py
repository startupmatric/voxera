from pathlib import Path

FILES = {}

FILES["frontend/js/views/debug.js"] = '''window.Views = window.Views || {};
window.Views.DebugPanel = (() => {
  function renderInto(el, report) {
    const color = {
      low: "var(--muted)",
      medium: "#eab308",
      high: "var(--error)",
      critical: "#dc2626",
    }[report.severity] || "var(--muted)";

    el.innerHTML = `
      <div class="panel">
        <h3 style="margin:0 0 .6rem;font-size:.9rem">AI Debugger</h3>
        <div class="grid">
          <div class="stat-card"><div class="stat-label">Category</div><div class="stat-value" style="font-size:.95rem">${report.category}</div></div>
          <div class="stat-card"><div class="stat-label">Stage</div><div class="stat-value" style="font-size:.95rem">${report.stage}</div></div>
          <div class="stat-card"><div class="stat-label">Severity</div><div class="stat-value" style="font-size:.95rem;color:${color}">${report.severity}</div></div>
          <div class="stat-card"><div class="stat-label">Confidence</div><div class="stat-value" style="font-size:.95rem">${(report.confidence*100).toFixed(0)}%</div></div>
        </div>

        <div style="margin-top:.8rem">
          <div style="color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em">Root cause</div>
          <p style="font-size:.85rem;margin:.3rem 0 1rem">${escapeHtml(report.root_cause)}</p>
        </div>

        <div style="margin-bottom:1rem">
          <div style="color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em">Evidence</div>
          ${report.evidence.length === 0
            ? '<p style="color:var(--muted);font-size:.8rem">No evidence items.</p>'
            : `<table class="data" style="margin-top:.4rem">
                <thead><tr><th>Type</th><th>Name</th><th>Status</th><th>Latency</th><th>Detail</th></tr></thead>
                <tbody>
                  ${report.evidence.map((e) => `
                    <tr>
                      <td>${e.type}</td>
                      <td>${escapeHtml(e.name || e.message_id || e.trace_id || "")}</td>
                      <td>${e.status || ""}</td>
                      <td>${e.latency_ms ? (e.latency_ms/1000).toFixed(2) + "s" : ""}</td>
                      <td style="color:var(--muted);font-size:.72rem">${escapeHtml((e.error || e.content || "").toString().slice(0, 100))}</td>
                    </tr>`).join("")}
                </tbody>
              </table>`}
        </div>

        <div>
          <div style="color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em">Recommended fixes</div>
          <ul style="font-size:.82rem;margin:.3rem 0 0 1rem">
            ${report.recommendation.map((r) => `<li>${escapeHtml(r)}</li>`).join("")}
          </ul>
        </div>
      </div>
    `;
  }

  function escapeHtml(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  return { renderInto };
})();
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")