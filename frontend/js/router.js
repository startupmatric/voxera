window.Router = (() => {
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

    const callDetail = hash.match(/^#\/calls\/([^/]+)$/);
    if (callDetail) {
      view.innerHTML = "";
      await window.Views.CallDetail.render(view, callDetail[1]);
      return;
    }

    const agentChat = hash.match(/^#\/agents\/([^/]+)\/chat$/);
    if (agentChat) {
      view.innerHTML = "";
      await window.Views.AgentChat.render(view, agentChat[1]);
      return;
    }

    const agentVersions = hash.match(/^#\/agents\/([^/]+)\/versions$/);
    if (agentVersions) {
      view.innerHTML = "";
      await window.Views.AgentDetail.render(view, agentVersions[1], "versions");
      return;
    }

    const agentDetail = hash.match(/^#\/agents\/([^/]+)$/);
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
