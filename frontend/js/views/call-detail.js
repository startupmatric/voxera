window.Views = window.Views || {};
window.Views.CallDetail = (() => {
  async function render(el, callId) {
    el.innerHTML = "<h2>Call</h2><p>Loading...</p>";
    try {
      const [call, msgs, traces, timeline, latency] = await Promise.all([
        API.get(`/calls/${callId}`, true),
        API.get(`/calls/${callId}/messages`, true),
        API.get(`/calls/${callId}/traces`, true),
        API.get(`/calls/${callId}/timeline`, true),
        API.get(`/calls/${callId}/latency`, true),
      ]);

      el.innerHTML = `
        <h2>Call ${call.id.slice(0,8)}…</h2>

        <div class="grid">
          <div class="stat-card">
            <div class="stat-label">Agent</div>
            <div class="stat-value" style="font-size:1rem">${call.agent_name || "—"}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Status</div>
            <div class="stat-value" style="font-size:1rem">${call.status}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Duration</div>
            <div class="stat-value" style="font-size:1rem">${(call.duration_ms / 1000).toFixed(2)}s</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Model</div>
            <div class="stat-value" style="font-size:1rem">${call.model_name || "—"}</div>
          </div>
        </div>

        <div class="panel">
          <h2>Transcript</h2>
          <div id="transcript" class="chat-log">
            ${msgs.map((m) => `
              <div class="chat-bubble ${m.role}">
                ${escapeHtml(m.content)}
                ${m.tool_traces && m.tool_traces.length
                  ? `<div style="margin-top:.5rem;font-size:.65rem;color:#9ca3af">${m.tool_traces.map((t) => `→ ${t.name} (${t.status}, ${t.latency_ms}ms)`).join(" · ")}</div>`
                  : ""}
              </div>`).join("")}
          </div>
        </div>

        <div class="panel">
          <h2>Trace Timeline</h2>
          <table class="data">
            <thead>
              <tr><th>Time</th><th>Kind</th><th>Event</th><th>Status</th><th>Latency</th><th>Detail</th></tr>
            </thead>
            <tbody>
              ${timeline.map((e) => `
                <tr>
                  <td>${new Date(e.ts).toLocaleTimeString()}</td>
                  <td>${e.kind}</td>
                  <td>${e.name}</td>
                  <td>${e.status === "success" ? "✅" : "❌"} ${e.status}</td>
                  <td>${e.latency_ms ? e.latency_ms.toFixed(0) + "ms" : "—"}</td>
                  <td style="color:var(--muted);font-size:.72rem">${escapeHtml(e.summary || "")}</td>
                </tr>`).join("")}
            </tbody>
          </table>
        </div>

        <div class="panel">
          <h2>Latency Breakdown</h2>
          <table class="data">
            <tr><th>Total</th><td>${(latency.total_ms / 1000).toFixed(2)}s</td></tr>
            <tr><th>LLM</th><td>${(latency.llm_ms / 1000).toFixed(2)}s</td></tr>
            <tr><th>Tools</th><td>${(latency.tools_ms / 1000).toFixed(3)}s</td></tr>
            <tr><th>STT</th><td>${(latency.stt_ms / 1000).toFixed(3)}s</td></tr>
            <tr><th>TTS</th><td>${(latency.tts_ms / 1000).toFixed(3)}s</td></tr>
            <tr><th>Other</th><td>${(latency.other_ms / 1000).toFixed(2)}s</td></tr>
          </table>
        </div>

        <div id="debug-section" class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">AI Debugger</h3>
          <p style="color:var(--muted);font-size:.75rem;margin:0 0 .6rem">
            Analyze this call to identify failures and get fix suggestions.
          </p>
          <button class="btn" id="btn-debug">Analyze Call</button>
          <div id="debug-result" style="margin-top:.8rem"></div>
        </div>

        <button class="btn secondary" id="back">Back to Calls</button>
      `;

      document.getElementById("back").addEventListener("click", () => Router.go("#/calls"));

      document.getElementById("btn-debug").addEventListener("click", async () => {
        const out = document.getElementById("debug-result");
        out.innerHTML = "<p style='color:var(--muted);font-size:.8rem'>Analyzing...</p>";
        try {
          const report = await API.post(`/debug/calls/${callId}`, {}, true);
          window.Views.DebugPanel.renderInto(out, report);
        } catch (e) {
          out.innerHTML = `<p style="color:var(--error);font-size:.8rem">${e.message}</p>`;
        }
      });
    } catch (e) {
      el.innerHTML = `<h2>Call</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  function escapeHtml(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  return { render };
})();
