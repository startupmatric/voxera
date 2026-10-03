from pathlib import Path

FILES = {}

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
  <script src="js/views/placeholder.js"></script>
  <script src="js/views/settings.js"></script>
  <script src="js/app.js"></script>
</body>
</html>
'''

FILES["frontend/css/dashboard.css"] = '''.hidden { display: none !important; }

.app {
  display: grid;
  grid-template-columns: 220px 1fr;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    "topbar topbar"
    "sidebar content";
  height: 100vh;
  background: var(--bg);
  color: var(--text);
}

.topbar {
  grid-area: topbar;
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0 1.2rem;
  background: var(--panel);
  border-bottom: 1px solid var(--border);
}

.brand { font-weight: bold; letter-spacing: 0.3em; font-size: 0.9rem; }
.spacer { flex: 1; }

.tenant-switcher {
  background: #0b0d10;
  color: var(--text);
  border: 1px solid var(--border);
  padding: 0.35rem 0.6rem;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.75rem;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.75rem;
  color: var(--muted);
}

.badge {
  background: var(--accent);
  color: #0b0d10;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.badge.admin { background: #60a5fa; }
.badge.member { background: var(--muted); }

.btn-ghost {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.35rem 0.8rem;
  border-radius: 6px;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.75rem;
}

.btn-ghost:hover { background: #1f2937; }

.sidebar {
  grid-area: sidebar;
  background: var(--panel);
  border-right: 1px solid var(--border);
  padding: 1rem 0;
  overflow-y: auto;
}

.sidebar nav { display: flex; flex-direction: column; }

.sidebar a {
  color: var(--muted);
  text-decoration: none;
  padding: 0.55rem 1.2rem;
  font-size: 0.8rem;
  border-left: 3px solid transparent;
}

.sidebar a:hover { color: var(--text); background: #1a1e24; }

.sidebar a.active {
  color: var(--accent);
  border-left-color: var(--accent);
  background: #1a1e24;
}

.content {
  grid-area: content;
  padding: 1.5rem 2rem;
  overflow-y: auto;
}

.content h2 {
  margin: 0 0 1rem;
  font-size: 1.1rem;
  letter-spacing: 0.05em;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.2rem;
}

.stat-label {
  font-size: 0.7rem;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.1em;
}

.stat-value { font-size: 1.8rem; margin-top: 0.35rem; }

.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  margin-bottom: 1.2rem;
}

table.data {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8rem;
}

table.data th,
table.data td {
  padding: 0.5rem 0.6rem;
  border-bottom: 1px solid var(--border);
  text-align: left;
}

table.data th {
  color: var(--muted);
  font-weight: normal;
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

button.btn {
  background: var(--accent);
  color: #0b0d10;
  border: none;
  padding: 0.45rem 0.9rem;
  border-radius: 6px;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.75rem;
  font-weight: bold;
}

button.btn.secondary {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border);
}

button.btn.danger { background: var(--error); color: white; }

button.btn:hover { opacity: 0.9; }

.form {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  max-width: 520px;
}

.form label {
  display: flex;
  flex-direction: column;
  font-size: 0.7rem;
  color: var(--muted);
  gap: 0.25rem;
}

.form input,
.form textarea,
.form select {
  background: #0b0d10;
  border: 1px solid var(--border);
  color: var(--text);
  padding: 0.5rem 0.6rem;
  border-radius: 6px;
  font-family: inherit;
  font-size: 0.85rem;
}

.form textarea { min-height: 100px; resize: vertical; }

.toast-container {
  position: fixed;
  bottom: 1rem;
  right: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 1000;
}

.toast {
  background: var(--panel);
  border-left: 3px solid var(--accent);
  padding: 0.6rem 1rem;
  border-radius: 6px;
  font-size: 0.8rem;
  box-shadow: 0 10px 30px rgba(0,0,0,0.4);
}

.toast.error { border-left-color: var(--error); }
'''

FILES["frontend/js/toast.js"] = '''window.Toast = (() => {
  const container = () => document.getElementById("toast-container");

  function show(message, type = "info", duration = 3000) {
    const el = document.createElement("div");
    el.className = "toast" + (type === "error" ? " error" : "");
    el.textContent = message;
    container().appendChild(el);
    setTimeout(() => el.remove(), duration);
  }

  return {
    info: (m) => show(m, "info"),
    error: (m) => show(m, "error", 5000),
    success: (m) => show(m, "info"),
  };
})();
'''

FILES["frontend/js/state.js"] = '''window.State = (() => {
  const TOKEN_KEY = "voxera_token";
  const TENANT_KEY = "voxera_tenant_id";

  let user = null;
  let org = null;
  let tenants = [];
  let currentTenantId = localStorage.getItem(TENANT_KEY) || null;

  return {
    get token() { return localStorage.getItem(TOKEN_KEY); },
    setToken(t) {
      if (t) localStorage.setItem(TOKEN_KEY, t);
      else localStorage.removeItem(TOKEN_KEY);
    },

    get user() { return user; },
    setUser(u) { user = u; },

    get org() { return org; },
    setOrg(o) { org = o; },

    get tenants() { return tenants; },
    setTenants(list) {
      tenants = list || [];
      if (!currentTenantId && tenants.length) {
        currentTenantId = tenants[0].id;
        localStorage.setItem(TENANT_KEY, currentTenantId);
      }
      if (currentTenantId && !tenants.find((t) => t.id === currentTenantId)) {
        currentTenantId = tenants.length ? tenants[0].id : null;
        if (currentTenantId) localStorage.setItem(TENANT_KEY, currentTenantId);
        else localStorage.removeItem(TENANT_KEY);
      }
    },

    get tenantId() { return currentTenantId; },
    setTenantId(id) {
      currentTenantId = id;
      if (id) localStorage.setItem(TENANT_KEY, id);
      else localStorage.removeItem(TENANT_KEY);
    },

    get role() { return user ? user.role : null; },
    canWrite() { return user && (user.role === "owner" || user.role === "admin"); },

    clear() {
      user = null; org = null; tenants = [];
      currentTenantId = null;
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(TENANT_KEY);
    },
  };
})();
'''

FILES["frontend/js/api.js"] = '''window.API = (() => {
  const BASE = "/api";

  async function request(path, opts = {}) {
    const headers = Object.assign(
      { "Content-Type": "application/json" },
      opts.headers || {}
    );
    const tok = window.State.token;
    if (tok) headers["Authorization"] = "Bearer " + tok;
    if (opts.tenant && window.State.tenantId)
      headers["X-Tenant-ID"] = window.State.tenantId;

    const res = await fetch(BASE + path, Object.assign({}, opts, { headers }));
    const text = await res.text();
    let body;
    try { body = text ? JSON.parse(text) : null; } catch (e) { body = text; }

    if (res.status === 401) {
      window.Auth.logout(true);
      throw Object.assign(new Error("Session expired"), { status: 401 });
    }
    if (!res.ok) {
      const msg = (body && body.detail) || ("HTTP " + res.status);
      throw Object.assign(new Error(typeof msg === "string" ? msg : "Request failed"), {
        status: res.status, body,
      });
    }
    return body;
  }

  return {
    get:   (p, tenant) => request(p, { method: "GET", tenant }),
    post:  (p, b, tenant) => request(p, { method: "POST", body: JSON.stringify(b), tenant }),
    patch: (p, b, tenant) => request(p, { method: "PATCH", body: JSON.stringify(b), tenant }),
    del:   (p, tenant) => request(p, { method: "DELETE", tenant }),
  };
})();
'''

FILES["frontend/js/auth.js"] = '''window.Auth = (() => {
  const loginScreen = () => document.getElementById("login-screen");
  const appShell = () => document.getElementById("app");

  function setLoginStatus(text) {
    const el = document.getElementById("login-result");
    if (el) el.textContent = text;
  }

  async function checkHealth() {
    const endpoints = ["/api/health", "/api/health/database", "/api/health/redis"];
    const results = await Promise.all(
      endpoints.map(async (url) => {
        try { const r = await fetch(url); const d = await r.json(); return d.status === "ok"; }
        catch { return false; }
      })
    );
    const allOk = results.every(Boolean);
    const el = document.getElementById("login-status");
    if (el) {
      el.textContent = allOk ? "System Online" : "Degraded";
      el.style.color = allOk ? "var(--accent)" : "var(--error)";
    }
  }

  function logout(silent = false) {
    window.State.clear();
    appShell().classList.add("hidden");
    loginScreen().classList.remove("hidden");
    if (!silent) window.Toast.info("Logged out");
  }

  async function bootstrapAfterLogin() {
    loginScreen().classList.add("hidden");
    appShell().classList.remove("hidden");
    await window.App.bootstrap();
  }

  function bindUI() {
    document.getElementById("btn-login").addEventListener("click", async () => {
      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;
      if (!email || !password) return setLoginStatus("Email and password required");
      try {
        const data = await API.post("/auth/login", { email, password });
        window.State.setToken(data.access_token);
        setLoginStatus("Login successful");
        await bootstrapAfterLogin();
      } catch (e) {
        window.State.clear();
        setLoginStatus("Login failed: " + e.message);
      }
    });

    document.getElementById("btn-register").addEventListener("click", async () => {
      const email = document.getElementById("email").value.trim();
      const password = document.getElementById("password").value;
      const organization_name = document.getElementById("org").value.trim();
      if (!email || !password || !organization_name)
        return setLoginStatus("Email, password and org name required");
      try {
        const data = await API.post("/auth/register", { email, password, organization_name });
        window.State.setToken(data.access_token);
        setLoginStatus("Registered + logged in");
        await bootstrapAfterLogin();
      } catch (e) {
        window.State.clear();
        setLoginStatus("Register failed: " + e.message);
      }
    });

    document.getElementById("btn-logout").addEventListener("click", () => logout());
  }

  return { bindUI, logout, checkHealth, setLoginStatus };
})();
'''

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
      a.classList.toggle("active", a.dataset.path === current);
    });
  }

  async function render() {
    const hash = location.hash || "#/overview";
    highlight(hash);

    const view = document.getElementById("view");

    const agentDetail = hash.match(/^#\\/agents\\/(.+)$/);
    if (agentDetail) {
      view.innerHTML = "";
      await window.Views.AgentDetail.render(view, agentDetail[1]);
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

FILES["frontend/js/views/overview.js"] = '''window.Views = window.Views || {};
window.Views.Overview = (() => {
  async function render(el) {
    el.innerHTML = "<h2>Overview</h2><p>Loading...</p>";
    try {
      const [stats, activity] = await Promise.all([
        API.get("/me/stats"),
        API.get("/me/recent-activity?limit=10"),
      ]);

      el.innerHTML = `
        <h2>Overview</h2>
        <div class="grid">
          <div class="stat-card">
            <div class="stat-label">Agents</div>
            <div class="stat-value">${stats.agents_count}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Tenants</div>
            <div class="stat-value">${stats.tenants_count}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Users</div>
            <div class="stat-value">${stats.users_count}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Organization</div>
            <div class="stat-value" style="font-size:1rem">${stats.organization_name}</div>
          </div>
        </div>
        <div class="panel">
          <h2>Recent Activity</h2>
          ${
            activity.length === 0
              ? '<p style="color:var(--muted);font-size:.8rem">No activity yet.</p>'
              : `<table class="data">
                  <thead><tr><th>Kind</th><th>Name</th><th>Updated</th></tr></thead>
                  <tbody>
                    ${activity.map((a) => `
                      <tr>
                        <td>${a.kind}</td>
                        <td>${a.name}</td>
                        <td>${new Date(a.updated_at).toLocaleString()}</td>
                      </tr>`).join("")}
                  </tbody>
                </table>`
          }
        </div>
      `;
    } catch (e) {
      el.innerHTML = `<h2>Overview</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }
  return { render };
})();
'''

FILES["frontend/js/views/agents.js"] = '''window.Views = window.Views || {};
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
'''

FILES["frontend/js/views/agent-detail.js"] = '''window.Views = window.Views || {};
window.Views.AgentDetail = (() => {
  async function render(el, agentId) {
    el.innerHTML = "<h2>Agent</h2><p>Loading...</p>";
    try {
      const a = await API.get(`/agents/${agentId}`, true);
      const canWrite = State.canWrite();
      el.innerHTML = `
        <h2>Agent: ${a.name}</h2>
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
              <button type="submit" class="btn">Save</button>
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
            window.Toast.success("Saved");
          } catch (e) {
            window.Toast.error(e.message);
          }
        });
      }
    } catch (e) {
      el.innerHTML = `<h2>Agent</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }
  return { render };
})();
'''

FILES["frontend/js/views/placeholder.js"] = '''window.Views = window.Views || {};

function makePlaceholder(name, description) {
  return {
    render: async (el) => {
      el.innerHTML = `
        <h2>${name}</h2>
        <div class="panel">
          <p style="color:var(--muted);font-size:.85rem">${description}</p>
          <p style="color:var(--muted);font-size:.75rem;margin-top:.5rem">
            Coming in a later day.
          </p>
        </div>
      `;
    },
  };
}

window.Views.Calls       = makePlaceholder("Calls", "Real-time and historical call logs with transcripts, outcomes, and recordings.");
window.Views.Traces      = makePlaceholder("Traces", "Step-by-step execution traces for every agent turn -- LLM calls, tool invocations, and timings.");
window.Views.Tools       = makePlaceholder("Tools", "Function tools available to agents -- calendar, CRM, custom HTTP endpoints.");
window.Views.Evaluations = makePlaceholder("Evaluations", "Automated quality scoring and regression tests against agent versions.");
window.Views.Knowledge   = makePlaceholder("Knowledge", "Vector-indexed documents and chunks used for retrieval-augmented agents.");
'''

FILES["frontend/js/views/settings.js"] = '''window.Views = window.Views || {};
window.Views.Settings = (() => {
  async function render(el) {
    const u = State.user || {};
    const org = State.org || {};
    el.innerHTML = `
      <h2>Settings</h2>
      <div class="panel">
        <h2>Current User</h2>
        <table class="data">
          <tr><th>Email</th><td>${u.email || "--"}</td></tr>
          <tr><th>Full name</th><td>${u.full_name || "--"}</td></tr>
          <tr><th>Role</th><td>${u.role || "--"}</td></tr>
          <tr><th>User ID</th><td>${u.id || "--"}</td></tr>
        </table>
      </div>
      <div class="panel">
        <h2>Organization</h2>
        <table class="data">
          <tr><th>Name</th><td>${org.name || "--"}</td></tr>
          <tr><th>ID</th><td>${org.id || "--"}</td></tr>
        </table>
      </div>
      <div class="panel">
        <h2>Session</h2>
        <button class="btn danger" id="settings-logout">Logout</button>
      </div>
    `;
    document.getElementById("settings-logout").addEventListener("click", () => Auth.logout());
  }
  return { render };
})();
'''

FILES["frontend/js/app.js"] = '''window.App = (() => {
  let bootstrapped = false;

  function renderTenantSwitcher() {
    const sel = document.getElementById("tenant-switcher");
    sel.innerHTML = "";
    const list = State.tenants || [];
    if (list.length === 0) {
      const opt = document.createElement("option");
      opt.textContent = "(no tenants)";
      opt.disabled = true;
      sel.appendChild(opt);
      return;
    }
    list.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t.id;
      opt.textContent = t.name;
      if (t.id === State.tenantId) opt.selected = true;
      sel.appendChild(opt);
    });
    sel.onchange = () => {
      State.setTenantId(sel.value);
      window.Toast.info("Tenant switched");
      Router.render();
    };
  }

  function renderHeader() {
    document.getElementById("user-email").textContent =
      (State.user && State.user.email) || "--";
    const roleEl = document.getElementById("user-role");
    const role = (State.user && State.user.role) || "--";
    roleEl.textContent = role;
    roleEl.className = "badge" + (role === "admin" ? " admin" : role === "member" ? " member" : "");
  }

  async function fetchBootstrapData() {
    const me = await API.get("/auth/me");
    State.setUser(me);

    const org = await API.get(`/organizations/${me.organization_id}`).catch(() => null);
    if (org) State.setOrg(org);

    const tenants = await API.get(`/tenants?organization_id=${me.organization_id}`);
    State.setTenants(tenants);
  }

  async function bootstrap() {
    try {
      await fetchBootstrapData();
    } catch (e) {
      window.Toast.error("Failed to load session: " + e.message);
      Auth.logout(true);
      return;
    }
    renderHeader();
    renderTenantSwitcher();
    if (!bootstrapped) {
      Router.start();
      bootstrapped = true;
    } else {
      Router.render();
    }
  }

  async function start() {
    Auth.bindUI();
    await Auth.checkHealth();

    if (State.token) {
      try {
        await bootstrap();
        document.getElementById("login-screen").classList.add("hidden");
        document.getElementById("app").classList.remove("hidden");
        return;
      } catch (e) {
        State.clear();
      }
    }
    Auth.setLoginStatus("Not authenticated");
  }

  return { start, bootstrap };
})();

document.addEventListener("DOMContentLoaded", () => window.App.start());
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal frontend files: {len(FILES)}")