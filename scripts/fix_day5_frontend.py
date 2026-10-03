from pathlib import Path

FILES = {}

# ---------- router.js (adds version route) ----------
FILES["frontend/js/router.js"] = '''window.Router = (() => {
  const routes = [
    { path: "#/overview",    label: "Overview",    view: () => window.Views.Overview },
    { path: "#/agents",      label: "Agents",      view: () => window.Views.Agents },
    { path: "#/calls",       label: "Calls",       view: () => window.Views.Calls },
    { path: "#/traces",      label: "Traces",      view: () => window.Views.Traces },
    { path: "#/tools",       label: "Tools",       view: () => window.Views.Tools },
    { path: "#/evaluations", label: "Evaluations", view: () => window.Views.Evaluations },
    { path: "#/knowledge",   label: "Knowledge",   view: () => window.Views.Knowledge },
    { path: "#/settings",    label: "Settings",    view: () => window.Views.Settings },
  ];

  function renderNav() {
    const nav = document.getElementById("nav");
    nav.innerHTML = "";
    routes.forEach((r) => {
      const a = document.createElement("a");
      a.href = r.path;
      a.dataset.path = r.path;
      a.textContent = r.label;
      nav.appendChild(a);
    });
  }

  function highlight(current) {
    document.querySelectorAll("#nav a").forEach((a) => {
      const base = current.split("/").slice(0, 2).join("/");
      a.classList.toggle("active", a.dataset.path === base || a.dataset.path === current);
    });
  }

  async function render() {
    const hash = location.hash || "#/overview";
    highlight(hash);

    const view = document.getElementById("view");

    const agentDetail = hash.match(/^#\\/agents\\/([^/]+)$/);
    if (agentDetail) {
      view.innerHTML = "";
      await window.Views.AgentDetail.render(view, agentDetail[1]);
      return;
    }

    const agentVersions = hash.match(/^#\\/agents\\/([^/]+)\\/versions$/);
    if (agentVersions) {
      view.innerHTML = "";
      await window.Views.AgentDetail.render(view, agentVersions[1], "versions");
      return;
    }

    const match = routes.find((r) => r.path === hash) || routes[0];
    view.innerHTML = "";
    await match.view().render(view);
  }

  function go(path) { location.hash = path; }

  function start() {
    renderNav();
    window.addEventListener("hashchange", render);
    if (!location.hash) location.hash = "#/overview";
    render();
  }

  return { start, render, go };
})();
'''

# ---------- views/agent-detail.js (tabs + versions) ----------
FILES["frontend/js/views/agent-detail.js"] = '''window.Views = window.Views || {};
window.Views.AgentDetail = (() => {

  function tabBar(agentId, active) {
    const tab = (key, label, href) =>
      `<a href="${href}" class="tab ${active === key ? "active" : ""}">${label}</a>`;
    return `
      <div class="tabs">
        ${tab("config", "Configuration", `#/agents/${agentId}`)}
        ${tab("versions", "Versions", `#/agents/${agentId}/versions`)}
      </div>
    `;
  }

  async function render(el, agentId, activeTab = "config") {
    el.innerHTML = "<h2>Agent</h2><p>Loading...</p>";
    try {
      const a = await API.get(`/agents/${agentId}`, true);
      const canWrite = State.canWrite();
      const header = `
        <h2>Agent: ${a.name}</h2>
        ${tabBar(agentId, activeTab)}
      `;

      if (activeTab === "versions") {
        const versions = await API.get(`/agents/${agentId}/versions`, true);
        el.innerHTML = `
          ${header}
          <div class="panel">
            <p style="color:var(--muted);font-size:.75rem">
              Versions are immutable snapshots. Activate any version to promote it to production.
              ${canWrite ? "" : " (Read-only — members cannot activate or rollback.)"}
            </p>
          </div>
          <div class="panel">
            <table class="data">
              <thead>
                <tr>
                  <th>Version</th>
                  <th>Status</th>
                  <th>Model</th>
                  <th>Temp</th>
                  <th>Created</th>
                  ${canWrite ? "<th></th>" : ""}
                </tr>
              </thead>
              <tbody>
                ${versions.map((v) => `
                  <tr>
                    <td>v${v.version}</td>
                    <td>${v.is_active
                        ? '<span class="badge">ACTIVE</span>'
                        : '<span class="badge member">DRAFT</span>'}</td>
                    <td>${v.model_name}</td>
                    <td>${v.temperature}</td>
                    <td>${new Date(v.created_at).toLocaleString()}</td>
                    ${canWrite ? `<td>
                      ${v.is_active
                        ? '<span style="color:var(--muted);font-size:.7rem">(current)</span>'
                        : `<button class="btn" data-activate="${v.id}" style="padding:.25rem .5rem;font-size:.7rem">Activate</button>`}
                    </td>` : ""}
                  </tr>
                  <tr>
                    <td colspan="${canWrite ? 6 : 5}" style="padding:0 .6rem .8rem;background:#0e1216">
                      <div style="font-size:.7rem;color:var(--muted);margin-bottom:.3rem">System prompt:</div>
                      <pre style="white-space:pre-wrap;font-size:.72rem;margin:0;color:var(--text)">${escapeHtml(v.system_prompt || "(empty)")}</pre>
                    </td>
                  </tr>`).join("")}
              </tbody>
            </table>
          </div>
        `;

        el.querySelectorAll("[data-activate]").forEach((b) =>
          b.addEventListener("click", async () => {
            if (!confirm("Activate this version? The agent configuration will be replaced.")) return;
            try {
              await API.post(`/agents/${agentId}/versions/${b.dataset.activate}/activate`, {}, true);
              window.Toast.success("Version activated");
              render(el, agentId, "versions");
            } catch (e) {
              window.Toast.error(e.message);
            }
          })
        );
        return;
      }

      el.innerHTML = `
        ${header}
        <form class="form" id="agent-form">
          <label><span>Name</span>
            <input id="af-name" value="${a.name}" ${canWrite ? "" : "disabled"} />
          </label>
          <label><span>Description</span>
            <textarea id="af-desc" ${canWrite ? "" : "disabled"}>${a.description || ""}</textarea>
          </label>
          <label><span>Status</span>
            <select id="af-status" ${canWrite ? "" : "disabled"}>
              ${["draft","active","paused","archived"].map((s) => `<option ${s === a.status ? "selected" : ""}>${s}</option>`).join("")}
            </select>
          </label>
          <label><span>Model provider</span>
            <input id="af-provider" value="${a.model_provider}" ${canWrite ? "" : "disabled"} />
          </label>
          <label><span>Model name</span>
            <input id="af-model" value="${a.model_name}" ${canWrite ? "" : "disabled"} />
          </label>
          <label><span>Temperature</span>
            <input id="af-temp" type="number" step="0.05" min="0" max="2" value="${a.temperature}" ${canWrite ? "" : "disabled"} />
          </label>
          <label><span>System prompt</span>
            <textarea id="af-prompt" ${canWrite ? "" : "disabled"}>${a.system_prompt || ""}</textarea>
          </label>
          ${canWrite ? `
            <div style="display:flex;gap:.5rem">
              <button type="submit" class="btn">Save (creates new version)</button>
              <button type="button" class="btn secondary" id="af-back">Back</button>
            </div>` : `
            <p style="color:var(--muted);font-size:.75rem">Read-only.</p>
            <button type="button" class="btn secondary" id="af-back">Back</button>`}
        </form>
      `;
      document.getElementById("af-back").addEventListener("click", () => Router.go("#/agents"));
      if (canWrite) {
        document.getElementById("agent-form").addEventListener("submit", async (ev) => {
          ev.preventDefault();
          try {
            await API.patch(`/agents/${agentId}`, {
              name: document.getElementById("af-name").value,
              description: document.getElementById("af-desc").value || null,
              status: document.getElementById("af-status").value,
              model_provider: document.getElementById("af-provider").value,
              model_name: document.getElementById("af-model").value,
              temperature: parseFloat(document.getElementById("af-temp").value),
              system_prompt: document.getElementById("af-prompt").value || null,
            }, true);
            window.Toast.success("Saved — a new draft version was created");
          } catch (e) {
            window.Toast.error(e.message);
          }
        });
      }
    } catch (e) {
      el.innerHTML = `<h2>Agent</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  return { render };
})();
'''

# ---------- CSS additions for tabs ----------
FILES["frontend/css/dashboard.css"] = open("frontend/css/dashboard.css", encoding="utf-8").read() + '''

.tabs {
  display: flex;
  gap: 0.4rem;
  margin-bottom: 1rem;
  border-bottom: 1px solid var(--border);
}

.tabs .tab {
  color: var(--muted);
  text-decoration: none;
  font-size: 0.8rem;
  padding: 0.5rem 0.9rem;
  border-bottom: 2px solid transparent;
}

.tabs .tab:hover { color: var(--text); }

.tabs .tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal frontend files: {len(FILES)}")