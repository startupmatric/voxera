window.Views = window.Views || {};

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

window.Views.Tools       = makePlaceholder("Tools", "Function tools available to agents -- calendar, CRM, custom HTTP endpoints.");
window.Views.Knowledge   = makePlaceholder("Knowledge", "Vector-indexed documents and chunks used for retrieval-augmented agents.");
