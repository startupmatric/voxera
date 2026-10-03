window.Auth = (() => {
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
