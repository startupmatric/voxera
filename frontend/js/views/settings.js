window.Views = window.Views || {};
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
