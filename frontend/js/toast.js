window.Toast = (() => {
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
