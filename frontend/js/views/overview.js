window.Views = window.Views || {};
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
