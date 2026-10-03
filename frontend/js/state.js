window.State = (() => {
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
