window.Views = window.Views || {};
window.Views.Agents = (() => {
  async function render(el) {
    el.innerHTML = "<h2>Agents</h2><p>Loading...</p>";
    if (!State.tenantId) {
      el.innerHTML = `<h2>Agents</h2><p style="color:var(--muted)">Select a tenant first.</p>`;
      return;
    }
    try {
      const agents = await API.get("/agents", true);
      const canWrite = State.canWrite();
      el.innerHTML = `
        <h2>Agents <span style="font-size:.7rem;color:var(--muted)">(tenant: ${State.tenantId.slice(0,8)}...)</span></h2>
        <div class="panel">
          ${canWrite
            ? '<button class="btn" id="btn-new-agent">Create agent</button>'
            : '<p style="color:var(--muted);font-size:.75rem">Read-only: members cannot modify agents.</p>'}
        </div>
        <div class="panel">
          ${
            agents.length === 0
              ? '<p style="color:var(--muted);font-size:.8rem">No agents yet.</p>'
              : `<table class="data">
                  <thead><tr><th>Name</th><th>Status</th><th>Model</th><th>Updated</th><th></th></tr></thead>
                  <tbody>
                    ${agents.map((a) => `
                      <tr>
                        <td><a href="#/agents/${a.id}" style="color:var(--accent)">${a.name}</a></td>
                        <td>${a.status}</td>
                        <td>${a.model_provider}/${a.model_name}</td>
                        <td>${new Date(a.updated_at).toLocaleString()}</td>
                        <td>${canWrite ? `<button class="btn danger" data-del="${a.id}" style="padding:.25rem .5rem;font-size:.7rem">Delete</button>` : ""}</td>
                      </tr>`).join("")}
                  </tbody>
                </table>`
          }
        </div>
      `;

      const newBtn = document.getElementById("btn-new-agent");
      if (newBtn) newBtn.addEventListener("click", () => promptNewAgent(el));

      el.querySelectorAll("[data-del]").forEach((b) =>
        b.addEventListener("click", async () => {
          if (!confirm("Delete this agent?")) return;
          try {
            await API.del(`/agents/${b.dataset.del}`, true);
            window.Toast.success("Agent deleted");
            render(el);
          } catch (e) {
            window.Toast.error(e.message);
          }
        })
      );
    } catch (e) {
      el.innerHTML = `<h2>Agents</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  function promptNewAgent(el) {
    el.innerHTML = `
      <h2>New Agent</h2>
      <form class="form" id="new-agent-form">
        <label><span>Name</span><input id="na-name" required maxlength="255" /></label>
        <label><span>Description</span><textarea id="na-desc"></textarea></label>
        <label><span>Model provider</span><input id="na-provider" value="ollama" /></label>
        <label><span>Model name</span><input id="na-model" value="llama3" /></label>
        <label><span>System prompt</span><textarea id="na-prompt"></textarea></label>
        <div style="display:flex;gap:.5rem">
          <button type="submit" class="btn">Create</button>
          <button type="button" class="btn secondary" id="na-cancel">Cancel</button>
        </div>
      </form>
    `;
    document.getElementById("na-cancel").addEventListener("click", () => render(el));
    document.getElementById("new-agent-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      try {
        await API.post("/agents", {
          tenant_id: State.tenantId,
          name: document.getElementById("na-name").value,
          description: document.getElementById("na-desc").value || null,
          model_provider: document.getElementById("na-provider").value,
          model_name: document.getElementById("na-model").value,
          system_prompt: document.getElementById("na-prompt").value || null,
        });
        window.Toast.success("Agent created");
        Router.go("#/agents");
      } catch (e) {
        window.Toast.error(e.message);
      }
    });
  }

  return { render };
})();
