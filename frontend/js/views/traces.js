window.Views = window.Views || {};
window.Views.Traces = (() => {
  async function render(el) {
    el.innerHTML = "<h2>Traces</h2><p>Loading...</p>";
    try {
      const traces = await API.get("/traces?limit=200", true);
      const stats = {
        total: traces.length,
        tools: traces.filter((t) => t.kind === "tool").length,
        errors: traces.filter((t) => t.status === "error").length,
        avgLatency: traces.length
          ? traces.reduce((a, t) => a + (t.latency_ms || 0), 0) / traces.length
          : 0,
      };

      el.innerHTML = `
        <h2>Traces</h2>
        <div class="grid">
          <div class="stat-card"><div class="stat-label">Total</div><div class="stat-value">${stats.total}</div></div>
          <div class="stat-card"><div class="stat-label">Tool Calls</div><div class="stat-value">${stats.tools}</div></div>
          <div class="stat-card"><div class="stat-label">Errors</div><div class="stat-value">${stats.errors}</div></div>
          <div class="stat-card"><div class="stat-label">Avg Latency</div><div class="stat-value" style="font-size:1rem">${(stats.avgLatency / 1000).toFixed(2)}s</div></div>
        </div>
        <div class="panel">
          <p style="color:var(--muted);font-size:.75rem;margin:0 0 .7rem">
            Every tool call, LLM invocation, and error across all calls.
            Click a trace to open its parent call.
          </p>
          ${traces.length === 0
            ? '<p style="color:var(--muted);font-size:.8rem">No traces yet.</p>'
            : `<table class="data">
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Kind</th>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Latency</th>
                    <th>Call</th>
                  </tr>
                </thead>
                <tbody>
                  ${traces.map((t) => `
                    <tr>
                      <td>${new Date(t.created_at).toLocaleTimeString()}</td>
                      <td>${t.kind}</td>
                      <td>${t.name}</td>
                      <td>${t.status === "success" ? "?" : "?"} ${t.status}</td>
                      <td>${(t.latency_ms / 1000).toFixed(2)}s</td>
                      <td>${t.call_id
                        ? `<a href="#/calls/${t.call_id}" style="color:var(--accent)">${t.call_id.slice(0,8)}?</a>`
                        : "?"}</td>
                    </tr>`).join("")}
                </tbody>
              </table>`}
        </div>
      `;
    } catch (e) {
      el.innerHTML = `<h2>Traces</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }
  return { render };
})();
