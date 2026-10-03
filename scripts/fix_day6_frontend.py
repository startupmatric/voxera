from pathlib import Path

FILES = {}

# ---------- index.html — add chat.js script tag ----------
FILES["frontend/index.html"] = '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Voxera</title>
  <link rel="stylesheet" href="css/main.css" />
  <link rel="stylesheet" href="css/dashboard.css" />
</head>
<body>
  <div id="login-screen" class="login-screen">
    <main class="card">
      <h1>VOXERA</h1>
      <p class="tagline">AI Voice Agent Platform</p>
      <div class="status" id="login-status">System Online</div>

      <form class="auth" onsubmit="return false;">
        <label>
          <span>Email</span>
          <input type="email" id="email" autocomplete="username" required />
        </label>
        <label>
          <span>Password</span>
          <input type="password" id="password" autocomplete="current-password" required minlength="6" />
        </label>
        <label>
          <span>Org name <small>(only for signup)</small></span>
          <input type="text" id="org" placeholder="Acme Motors" />
        </label>
        <div class="buttons">
          <button type="button" id="btn-login">Login</button>
          <button type="button" id="btn-register">Sign up</button>
        </div>
      </form>
      <div class="result" id="login-result">Not authenticated</div>
    </main>
  </div>

  <div id="app" class="app hidden">
    <header class="topbar">
      <div class="brand">VOXERA</div>
      <div class="spacer"></div>
      <select id="tenant-switcher" class="tenant-switcher" title="Current tenant"></select>
      <div class="user-info">
        <span id="user-email">--</span>
        <span id="user-role" class="badge">--</span>
      </div>
      <button id="btn-logout" class="btn-ghost">Logout</button>
    </header>

    <aside class="sidebar">
      <nav id="nav"></nav>
    </aside>

    <main class="content" id="view"></main>
  </div>

  <div id="toast-container" class="toast-container"></div>

  <script src="js/toast.js"></script>
  <script src="js/state.js"></script>
  <script src="js/api.js"></script>
  <script src="js/auth.js"></script>
  <script src="js/router.js"></script>
  <script src="js/views/overview.js"></script>
  <script src="js/views/agents.js"></script>
  <script src="js/views/agent-detail.js"></script>
  <script src="js/views/chat.js"></script>
  <script src="js/views/placeholder.js"></script>
  <script src="js/views/settings.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
'''

# ---------- router.js — add /chat route ----------
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

    const agentChat = hash.match(/^#\\/agents\\/([^/]+)\\/chat$/);
    if (agentChat) {
      view.innerHTML = "";
      await window.Views.AgentChat.render(view, agentChat[1]);
      return;
    }

    const agentVersions = hash.match(/^#\\/agents\\/([^/]+)\\/versions$/);
    if (agentVersions) {
      view.innerHTML = "";
      await window.Views.AgentDetail.render(view, agentVersions[1], "versions");
      return;
    }

    const agentDetail = hash.match(/^#\\/agents\\/([^/]+)$/);
    if (agentDetail) {
      view.innerHTML = "";
      await window.Views.AgentDetail.render(view, agentDetail[1], "config");
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

# ---------- agent-detail.js — add chat tab ----------
FILES["frontend/js/views/agent-detail.js"] = '''window.Views = window.Views || {};
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
'''

# ---------- views/chat.js ----------
FILES["frontend/js/views/chat.js"] = '''window.Views = window.Views || {};
window.Views.AgentChat = (() => {
  let history = [];

  async function render(el, agentId) {
    history = [];
    el.innerHTML = "<h2>Test Agent</h2><p>Loading...</p>";
    try {
      const a = await API.get(`/agents/${agentId}`, true);

      el.innerHTML = `
        <h2>Test: ${a.name}</h2>
        <div class="tabs">
          <a href="#/agents/${agentId}" class="tab">Configuration</a>
          <a href="#/agents/${agentId}/versions" class="tab">Versions</a>
          <a href="#/agents/${agentId}/chat" class="tab active">Test</a>
        </div>

        <div class="panel">
          <p style="color:var(--muted);font-size:.75rem;margin:0 0 .7rem">
            Messages are sent to the active version of this agent and routed through LangGraph → Ollama.
          </p>
          <div id="chat-log" class="chat-log"></div>

          <div class="chat-input">
            <textarea id="chat-text" placeholder="Type a message and press Enter..." rows="2"></textarea>
            <button class="btn" id="chat-send">Send</button>
          </div>
          <div id="chat-meta" style="color:var(--muted);font-size:.7rem;margin-top:.5rem"></div>
        </div>
      `;

      const log = document.getElementById("chat-log");
      const input = document.getElementById("chat-text");

      function addBubble(role, text) {
        const div = document.createElement("div");
        div.className = "chat-bubble " + role;
        div.textContent = text;
        log.appendChild(div);
        log.scrollTop = log.scrollHeight;
      }

      async function send() {
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        addBubble("user", text);
        history.push({ role: "user", content: text });

        const meta = document.getElementById("chat-meta");
        meta.textContent = "Thinking...";

        try {
          const res = await API.post(`/agents/${agentId}/chat`, {
            message: text,
            history: history.slice(0, -1),   // exclude the just-added user message
          }, true);

          history.push({ role: "assistant", content: res.response });
          addBubble("assistant", res.response);

          meta.textContent =
            `v${res.version} · ${res.meta.model} · ${res.meta.latency_ms}ms · ` +
            `${res.meta.prompt_tokens}+${res.meta.completion_tokens} tokens`;
        } catch (e) {
          addBubble("assistant", "[error] " + e.message);
          meta.textContent = "";
        }
      }

      document.getElementById("chat-send").addEventListener("click", send);
      input.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" && !ev.shiftKey) {
          ev.preventDefault();
          send();
        }
      });

      addBubble("assistant", "Hi! Send a message to test this agent.");
    } catch (e) {
      el.innerHTML = `<h2>Test</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  return { render };
})();
'''

# ---------- CSS additions ----------
FILES["frontend/css/dashboard.css"] = open("frontend/css/dashboard.css", encoding="utf-8").read() + '''

.chat-log {
  background: #0b0d10;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  height: 360px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  margin-bottom: 0.8rem;
}

.chat-bubble {
  max-width: 78%;
  padding: 0.55rem 0.85rem;
  border-radius: 10px;
  font-size: 0.85rem;
  line-height: 1.4;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.chat-bubble.user {
  background: #1e3a2c;
  color: #e5ffe8;
  align-self: flex-end;
  border-bottom-right-radius: 3px;
}

.chat-bubble.assistant {
  background: #1a1e24;
  color: var(--text);
  align-self: flex-start;
  border-bottom-left-radius: 3px;
}

.chat-input {
  display: flex;
  gap: 0.5rem;
}

.chat-input textarea {
  flex: 1;
  background: #0b0d10;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.5rem 0.6rem;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.85rem;
  resize: vertical;
  min-height: 40px;
}

.chat-input button {
  min-width: 90px;
}
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal frontend files: {len(FILES)}")