window.API = (() => {
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
