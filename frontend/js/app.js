const API_BASE = "/api";
const TOKEN_KEY = "voxera_token";

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(t) {
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function api(path, opts = {}) {
  const headers = Object.assign(
    { "Content-Type": "application/json" },
    opts.headers || {}
  );
  const tok = getToken();
  if (tok) headers["Authorization"] = "Bearer " + tok;

  const res = await fetch(API_BASE + path, Object.assign({}, opts, { headers }));
  const text = await res.text();
  let body;
  try { body = text ? JSON.parse(text) : null; } catch (e) { body = text; }
  if (!res.ok) {
    const err = new Error((body && body.detail) || ("HTTP " + res.status));
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}

function $(id) { return document.getElementById(id); }

function setResult(msg) {
  $("result").textContent = msg;
}

async function checkHealth() {
  const endpoints = {
    api: API_BASE + "/health",
    db: API_BASE + "/health/database",
    redis: API_BASE + "/health/redis",
  };
  const results = await Promise.all(
    Object.keys(endpoints).map(async function (k) {
      try {
        const r = await fetch(endpoints[k]);
        const d = await r.json();
        return d.status === "ok";
      } catch (e) {
        return false;
      }
    })
  );
  const allOk = results.every(Boolean);
  const el = $("overall");
  el.textContent = allOk ? "System Online" : "Degraded";
  el.style.color = allOk ? "var(--accent)" : "var(--error)";
}

$("btn-login").addEventListener("click", async function () {
  const email = $("email").value.trim();
  const password = $("password").value;
  if (!email || !password) { setResult("Email and password required"); return; }
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: email, password: password }),
    });
    setToken(data.access_token);
    const me = await api("/auth/me");
    setResult("Logged in as " + me.email + " (" + me.role + ")");
  } catch (e) {
    setToken(null);
    setResult("Login failed: " + e.message);
  }
});

$("btn-register").addEventListener("click", async function () {
  const email = $("email").value.trim();
  const password = $("password").value;
  const organization_name = $("org").value.trim();
  if (!email || !password || !organization_name) {
    setResult("Email, password and org name required");
    return;
  }
  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: email,
        password: password,
        organization_name: organization_name,
      }),
    });
    setToken(data.access_token);
    const me = await api("/auth/me");
    setResult("Registered + logged in as " + me.email + " (" + me.role + ")");
  } catch (e) {
    setToken(null);
    setResult("Register failed: " + e.message);
  }
});

(async function () {
  await checkHealth();
  const tok = getToken();
  if (tok) {
    try {
      const me = await api("/auth/me");
      setResult("Logged in as " + me.email + " (" + me.role + ")");
    } catch (e) {
      setToken(null);
      setResult("Session expired, please login");
    }
  }
})();
