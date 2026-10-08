window.Views = window.Views || {};
window.Views.Tools = (() => {
  async function render(el) {
    el.innerHTML = "<h2>Tools</h2><p>Loading...</p>";
    try {
      const resp = await API.get("/agents/runtime/tools", true);
      const tools = resp.tools || [];

      el.innerHTML = `
        <h2>Tools</h2>
        <div class="panel">
          <p style="color:var(--text-muted);font-size:.8125rem;margin:0 0 .75rem">
            Every tool registered with the Voxera agent runtime. The LLM chooses
            which tools to call based on their name and description. Each tool's
            inputs are validated against a JSON schema before execution.
          </p>
          <div class="stat-label">${tools.length} tools registered</div>
        </div>
        <div class="stagger">
          ${tools.map((t) => `
            <div class="panel">
              <div style="display:flex;align-items:center;justify-content:space-between;gap:1rem;flex-wrap:wrap">
                <div>
                  <h3 style="margin:0 0 .25rem;font-family:var(--font-mono);font-size:.9rem">${escapeHtml(t.name)}</h3>
                  <p style="color:var(--text-muted);font-size:.8125rem;margin:0">${escapeHtml(t.description || "")}</p>
                </div>
                <span class="status-badge success">REGISTERED</span>
              </div>
              <details style="margin-top:.75rem">
                <summary style="cursor:pointer;font-size:.75rem;color:var(--text-muted);font-weight:600">Input schema</summary>
                <pre class="mono" style="background:var(--panel-alt);border:1px solid var(--border-soft);border-radius:4px;padding:.75rem;font-size:.75rem;overflow-x:auto;margin:.5rem 0 0">${escapeHtml(JSON.stringify(t.schema, null, 2))}</pre>
              </details>
            </div>
          `).join("")}
        </div>
      `;
    } catch (e) {
      el.innerHTML = `<h2>Tools</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  function escapeHtml(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  return { render };
})();
