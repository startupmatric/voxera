window.App = (() => {
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

// ---------- Mobile sidebar ----------
(function () {
  const menu = document.getElementById("btn-menu");
  const sidebar = document.getElementById("sidebar");
  const backdrop = document.getElementById("sidebar-backdrop");
  if (!menu || !sidebar || !backdrop) return;

  function open() {
    sidebar.classList.add("open");
    backdrop.classList.add("show");
  }
  function close() {
    sidebar.classList.remove("open");
    backdrop.classList.remove("show");
  }

  menu.addEventListener("click", () => {
    sidebar.classList.contains("open") ? close() : open();
  });
  backdrop.addEventListener("click", close);
  sidebar.addEventListener("click", (e) => {
    if (e.target.tagName === "A") close();
  });
})();

// ---------- Header "Get Started" button ----------
(function () {
  const btn = document.getElementById("btn-header-register");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const org = document.getElementById("org");
    if (org) { org.focus(); org.scrollIntoView({ behavior: "smooth", block: "center" }); }
  });
})();
