window.Views = window.Views || {};
window.Views.AgentDetail = (() => {

  function tabBar(agentId, active) {
    const tab = (key, label, href) =>
      `<a href="${href}" class="tab ${active === key ? "active" : ""}">${label}</a>`;
    return `
      <div class="tabs">
        ${tab("config", "Configuration", `#/agents/${agentId}`)}
        ${tab("versions", "Versions", `#/agents/${agentId}/versions`)}
        ${tab("chat", "Test", `#/agents/${agentId}/chat`)}
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
            </p>
          </div>
          <div class="panel">
            <table class="data">
              <thead>
                <tr><th>Version</th><th>Status</th><th>Model</th><th>Temp</th><th>Created</th>${canWrite ? "<th></th>" : ""}</tr>
              </thead>
              <tbody>
                ${versions.map((v) => `
                  <tr>
                    <td>v${v.version}</td>
                    <td>${v.is_active ? '<span class="badge">ACTIVE</span>' : '<span class="badge member">DRAFT</span>'}</td>
                    <td>${v.model_name}</td>
                    <td>${v.temperature}</td>
                    <td>${new Date(v.created_at).toLocaleString()}</td>
                    ${canWrite ? `<td>${v.is_active ? '<span style="color:var(--muted);font-size:.7rem">(current)</span>' : `<button class="btn" data-activate="${v.id}" style="padding:.25rem .5rem;font-size:.7rem">Activate</button>`}</td>` : ""}
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
            if (!confirm("Activate this version?")) return;
            try {
              await API.post(`/agents/${agentId}/versions/${b.dataset.activate}/activate`, {}, true);
              window.Toast.success("Version activated");
              render(el, agentId, "versions");
            } catch (e) { window.Toast.error(e.message); }
          })
        );
        return;
      }

      el.innerHTML = `
        ${header}
        <form class="form" id="agent-form">
          <label><span>Name</span><input id="af-name" value="${a.name}" ${canWrite ? "" : "disabled"} /></label>
          <label><span>Description</span><textarea id="af-desc" ${canWrite ? "" : "disabled"}>${a.description || ""}</textarea></label>
          <label><span>Status</span>
            <select id="af-status" ${canWrite ? "" : "disabled"}>
              ${["draft","active","paused","archived"].map((s) => `<option ${s === a.status ? "selected" : ""}>${s}</option>`).join("")}
            </select>
          </label>
          <label><span>Model provider</span><input id="af-provider" value="${a.model_provider}" ${canWrite ? "" : "disabled"} /></label>
          <label><span>Model name</span><input id="af-model" value="${a.model_name}" ${canWrite ? "" : "disabled"} /></label>
          <label><span>Temperature</span><input id="af-temp" type="number" step="0.05" min="0" max="2" value="${a.temperature}" ${canWrite ? "" : "disabled"} /></label>
          <label><span>System prompt</span><textarea id="af-prompt" ${canWrite ? "" : "disabled"}>${a.system_prompt || ""}</textarea></label>
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
          } catch (e) { window.Toast.error(e.message); }
        });
      }
    } catch (e) {
      el.innerHTML = `<h2>Agent</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  function escapeHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  return { render };
})();
