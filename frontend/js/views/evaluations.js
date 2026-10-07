window.Views = window.Views || {};
window.Views.Evaluations = (() => {
  async function render(el) {
    el.innerHTML = "<h2>Evaluations</h2><p>Loading...</p>";
    try {
      const datasets = await API.get("/evaluations", true);
      el.innerHTML = `
        <h2>Evaluations</h2>
        <div class="panel">
          <p style="color:var(--muted);font-size:.75rem;margin:0 0 .7rem">
            Test your agents against a set of expected inputs. Every run is scored
            and compared to the previous run to detect regressions.
          </p>
          <button class="btn" id="new-dataset">New Dataset</button>
        </div>
        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">Datasets</h3>
          ${datasets.length === 0
            ? '<p style="color:var(--muted);font-size:.8rem">No datasets yet.</p>'
            : `<table class="data">
                <thead><tr><th>Name</th><th>Agent</th><th>Cases</th><th>Actions</th></tr></thead>
                <tbody>
                  ${datasets.map((d) => `
                    <tr>
                      <td>${d.name}</td>
                      <td>${d.agent_id ? d.agent_id.slice(0,8) + "?" : "?"}</td>
                      <td data-cases="${d.id}">?</td>
                      <td>
                        <button class="btn secondary" data-open="${d.id}" style="padding:.25rem .5rem;font-size:.7rem">Open</button>
                        <button class="btn" data-run="${d.id}" style="padding:.25rem .5rem;font-size:.7rem">Run</button>
                      </td>
                    </tr>`).join("")}
                </tbody>
              </table>`}
        </div>
        <div id="dataset-panel"></div>
      `;

      document.getElementById("new-dataset").addEventListener("click", () => showNewDataset(el));

      el.querySelectorAll("[data-open]").forEach((b) =>
        b.addEventListener("click", () => openDataset(el, b.dataset.open))
      );
      el.querySelectorAll("[data-run]").forEach((b) =>
        b.addEventListener("click", async () => {
          try {
            window.Toast.info("Running evaluation... this can take a few minutes");
            const run = await API.post(`/evaluations/${b.dataset.run}/run`, {}, true);
            window.Toast.success(`Run complete: ${run.passed_cases}/${run.total_cases} passed`);
            openDataset(el, b.dataset.run);
          } catch (e) {
            window.Toast.error(e.message);
          }
        })
      );

      for (const d of datasets) {
        try {
          const cases = await API.get(`/evaluations/${d.id}/cases`, true);
          const cell = el.querySelector(`[data-cases="${d.id}"]`);
          if (cell) cell.textContent = cases.length;
        } catch {}
      }
    } catch (e) {
      el.innerHTML = `<h2>Evaluations</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  async function showNewDataset(el) {
    const agents = await API.get("/agents", true);
    const panel = document.getElementById("dataset-panel");
    panel.innerHTML = `
      <div class="panel">
        <h3 style="margin:0 0 .6rem;font-size:.9rem">New Dataset</h3>
        <form class="form" id="dataset-form">
          <label><span>Name</span><input id="ds-name" required /></label>
          <label><span>Description</span><textarea id="ds-desc"></textarea></label>
          <label><span>Agent</span>
            <select id="ds-agent">
              <option value="">(none)</option>
              ${agents.map((a) => `<option value="${a.id}">${a.name}</option>`).join("")}
            </select>
          </label>
          <div style="display:flex;gap:.5rem">
            <button type="submit" class="btn">Create</button>
            <button type="button" class="btn secondary" id="ds-cancel">Cancel</button>
          </div>
        </form>
      </div>
    `;
    document.getElementById("ds-cancel").addEventListener("click", () => panel.innerHTML = "");
    document.getElementById("dataset-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const body = {
        name: document.getElementById("ds-name").value,
        description: document.getElementById("ds-desc").value || null,
        agent_id: document.getElementById("ds-agent").value || null,
      };
      try {
        await API.post("/evaluations", body, true);
        window.Toast.success("Dataset created");
        render(el);
      } catch (e) { window.Toast.error(e.message); }
    });
  }

  async function openDataset(el, datasetId) {
    const panel = document.getElementById("dataset-panel");
    panel.innerHTML = "<p>Loading dataset?</p>";
    try {
      const [ds, cases, runs] = await Promise.all([
        API.get(`/evaluations/${datasetId}`, true),
        API.get(`/evaluations/${datasetId}/cases`, true),
        API.get(`/evaluations/${datasetId}/runs`, true),
      ]);
      const latest = runs[0] || null;

      panel.innerHTML = `
        <div class="panel">
          <h3 style="margin:0 0 .4rem;font-size:.9rem">${ds.name}</h3>
          <p style="color:var(--muted);font-size:.75rem">${ds.description || ""}</p>
          <div class="grid">
            <div class="stat-card"><div class="stat-label">Latest Score</div><div class="stat-value">${latest ? latest.average_score.toFixed(1) : "?"}</div></div>
            <div class="stat-card"><div class="stat-label">Pass Rate</div><div class="stat-value">${latest ? latest.pass_rate.toFixed(0) + "%" : "?"}</div></div>
            <div class="stat-card"><div class="stat-label">Avg Latency</div><div class="stat-value">${latest ? (latest.avg_latency_ms / 1000).toFixed(1) + "s" : "?"}</div></div>
            <div class="stat-card"><div class="stat-label">Version</div><div class="stat-value">v${latest?.agent_version_number ?? "?"}</div></div>
          </div>
          ${latest?.regression_detected ? '<p style="color:var(--error);font-weight:bold">? REGRESSION DETECTED</p>' : ""}
          <button class="btn" id="add-case">Add Test Case</button>
          <button class="btn" id="run-now">Run Evaluation</button>
        </div>

        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">Test Cases (${cases.length})</h3>
          ${cases.length === 0
            ? '<p style="color:var(--muted);font-size:.8rem">No cases yet.</p>'
            : `<table class="data">
                <thead><tr><th>Name</th><th>Input</th><th>Expected Tool</th><th></th></tr></thead>
                <tbody>
                  ${cases.map((c) => `
                    <tr>
                      <td>${c.name}</td>
                      <td style="color:var(--muted);font-size:.72rem">${escapeHtml((c.input_text || "").slice(0, 50))}</td>
                      <td>${(c.expected_tools || []).join(", ") || "?"}</td>
                      <td><button class="btn danger" data-del-case="${c.id}" style="padding:.2rem .5rem;font-size:.7rem">Delete</button></td>
                    </tr>`).join("")}
                </tbody>
              </table>`}
        </div>

        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">Runs (${runs.length})</h3>
          ${runs.length === 0
            ? '<p style="color:var(--muted);font-size:.8rem">No runs yet.</p>'
            : `<table class="data">
                <thead><tr><th>Started</th><th>Version</th><th>Pass</th><th>Score</th><th>Latency</th><th>Regression</th><th></th></tr></thead>
                <tbody>
                  ${runs.map((r) => `
                    <tr>
                      <td>${new Date(r.created_at).toLocaleString()}</td>
                      <td>v${r.agent_version_number ?? "?"}</td>
                      <td>${r.passed_cases}/${r.total_cases} (${r.pass_rate.toFixed(0)}%)</td>
                      <td>${r.average_score.toFixed(1)}</td>
                      <td>${(r.avg_latency_ms / 1000).toFixed(1)}s</td>
                      <td>${r.regression_detected ? "?" : "?"}</td>
                      <td><button class="btn secondary" data-open-run="${r.id}" style="padding:.2rem .5rem;font-size:.7rem">View</button></td>
                    </tr>`).join("")}
                </tbody>
              </table>`}
        </div>

        <div id="run-panel"></div>
      `;

      document.getElementById("add-case").addEventListener("click", () => showNewCase(el, datasetId));
      document.getElementById("run-now").addEventListener("click", async () => {
        try {
          window.Toast.info("Running evaluation...");
          await API.post(`/evaluations/${datasetId}/run`, {}, true);
          window.Toast.success("Run complete");
          openDataset(el, datasetId);
        } catch (e) { window.Toast.error(e.message); }
      });
      el.querySelectorAll("[data-del-case]").forEach((b) =>
        b.addEventListener("click", async () => {
          if (!confirm("Delete case?")) return;
          try {
            await API.del(`/evaluations/${datasetId}/cases/${b.dataset.delCase}`, true);
            openDataset(el, datasetId);
          } catch (e) { window.Toast.error(e.message); }
        })
      );
      el.querySelectorAll("[data-open-run]").forEach((b) =>
        b.addEventListener("click", () => viewRun(datasetId, b.dataset.openRun))
      );
    } catch (e) {
      panel.innerHTML = `<p style="color:var(--error)">${e.message}</p>`;
    }
  }

  async function showNewCase(el, datasetId) {
    const panel = document.getElementById("run-panel");
    panel.innerHTML = `
      <div class="panel">
        <h3 style="margin:0 0 .6rem;font-size:.9rem">New Test Case</h3>
        <form class="form" id="case-form">
          <label><span>Name</span><input id="c-name" required /></label>
          <label><span>Input</span><textarea id="c-input" required></textarea></label>
          <label><span>Expected output contains</span><input id="c-exp" placeholder="(optional) e.g. 10" /></label>
          <label><span>Expected tools (comma-separated)</span><input id="c-tools" placeholder="e.g. calculate, get_current_time" /></label>
          <label><span>Max latency (ms)</span><input id="c-lat" type="number" value="120000" /></label>
          <div style="display:flex;gap:.5rem">
            <button type="submit" class="btn">Create</button>
            <button type="button" class="btn secondary" id="c-cancel">Cancel</button>
          </div>
        </form>
      </div>
    `;
    document.getElementById("c-cancel").addEventListener("click", () => panel.innerHTML = "");
    document.getElementById("case-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const tools = document.getElementById("c-tools").value
        .split(",").map((s) => s.trim()).filter(Boolean);
      try {
        await API.post(`/evaluations/${datasetId}/cases`, {
          name: document.getElementById("c-name").value,
          input_text: document.getElementById("c-input").value,
          expected_output: document.getElementById("c-exp").value || null,
          expected_tools: tools,
          max_latency_ms: parseInt(document.getElementById("c-lat").value, 10) || 120000,
          enabled: true,
        }, true);
        window.Toast.success("Case created");
        openDataset(el, datasetId);
      } catch (e) { window.Toast.error(e.message); }
    });
  }

  async function viewRun(datasetId, runId) {
    const panel = document.getElementById("run-panel");
    panel.innerHTML = "<p>Loading run?</p>";
    try {
      const results = await API.get(`/evaluations/${datasetId}/runs/${runId}/results`, true);
      panel.innerHTML = `
        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">Run Results (${results.length})</h3>
          <table class="data">
            <thead><tr><th>Case</th><th>Status</th><th>Score</th><th>Expected</th><th>Actual</th><th>Tools</th><th>Latency</th></tr></thead>
            <tbody>
              ${results.map((r) => `
                <tr>
                  <td style="font-size:.72rem">${escapeHtml((r.input_text || "").slice(0, 40))}</td>
                  <td>${r.status === "passed" ? "?" : "?"} ${r.status}</td>
                  <td>${r.score.toFixed(0)}</td>
                  <td style="color:var(--muted);font-size:.7rem">${escapeHtml((r.expected_output || "?").slice(0, 30))}</td>
                  <td style="color:var(--muted);font-size:.7rem">${escapeHtml((r.actual_output || "?").slice(0, 50))}</td>
                  <td style="font-size:.7rem">
                    Exp: ${(r.expected_tools || []).join(", ") || "?"}<br>
                    Act: ${(r.actual_tools || []).join(", ") || "?"}
                  </td>
                  <td>${(r.latency_ms / 1000).toFixed(1)}s</td>
                </tr>`).join("")}
            </tbody>
          </table>
          <button class="btn secondary" id="run-close">Close</button>
        </div>
      `;
      document.getElementById("run-close").addEventListener("click", () => panel.innerHTML = "");
    } catch (e) {
      panel.innerHTML = `<p style="color:var(--error)">${e.message}</p>`;
    }
  }

  function escapeHtml(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  return { render };
})();
