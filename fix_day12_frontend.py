from pathlib import Path

content = r"""window.Views = window.Views || {};
window.Views.Knowledge = (() => {
  async function render(el) {
    el.innerHTML = "<h2>Knowledge</h2><p>Loading...</p>";
    try {
      const docs = await API.get("/knowledge/documents", true);
      el.innerHTML = `
        <h2>Knowledge Base</h2>
        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">Upload Document</h3>
          <form class="form" id="kb-form">
            <label><span>Name</span><input id="kb-name" required maxlength="255" /></label>
            <label><span>Source (optional)</span><input id="kb-source" placeholder="e.g. faq.md" /></label>
            <label><span>Content</span><textarea id="kb-content" required rows="8"></textarea></label>
            <button type="submit" class="btn">Add Document</button>
          </form>
        </div>
        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">Documents (${docs.length})</h3>
          ${docs.length === 0
            ? '<p style="color:var(--muted);font-size:.8rem">No documents yet.</p>'
            : `<table class="data">
                <thead><tr><th>Name</th><th>Source</th><th>Created</th><th></th></tr></thead>
                <tbody>
                  ${docs.map((d) => `
                    <tr>
                      <td>${d.name}</td>
                      <td style="color:var(--muted);font-size:.75rem">${d.source || "?"}</td>
                      <td>${new Date(d.created_at).toLocaleString()}</td>
                      <td><button class="btn danger" data-del="${d.id}" style="padding:.2rem .5rem;font-size:.7rem">Delete</button></td>
                    </tr>`).join("")}
                </tbody>
              </table>`}
        </div>
        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">Semantic Search</h3>
          <div style="display:flex;gap:.5rem">
            <input id="kb-query" placeholder="Ask a question..." style="flex:1;background:#0b0d10;border:1px solid var(--border);color:var(--text);padding:.5rem;border-radius:6px;font-family:inherit" />
            <button class="btn" id="kb-search">Search</button>
          </div>
          <div id="kb-results" style="margin-top:.8rem"></div>
        </div>
      `;

      document.getElementById("kb-form").addEventListener("submit", async (ev) => {
        ev.preventDefault();
        const btn = ev.submitter;
        if (btn) btn.disabled = true;
        window.Toast.info("Uploading and embedding... this can take a moment");
        try {
          await API.post("/knowledge/documents", {
            name: document.getElementById("kb-name").value,
            source: document.getElementById("kb-source").value || null,
            content: document.getElementById("kb-content").value,
          }, true);
          window.Toast.success("Document added");
          render(el);
        } catch (e) {
          window.Toast.error(e.message);
        } finally {
          if (btn) btn.disabled = false;
        }
      });

      document.getElementById("kb-search").addEventListener("click", async () => {
        const q = document.getElementById("kb-query").value.trim();
        if (!q) return;
        const out = document.getElementById("kb-results");
        out.innerHTML = "<p style='color:var(--muted);font-size:.8rem'>Searching...</p>";
        try {
          const res = await API.post("/knowledge/search", { query: q, top_k: 5 }, true);
          if (res.results.length === 0) {
            out.innerHTML = '<p style="color:var(--muted);font-size:.8rem">No results.</p>';
            return;
          }
          out.innerHTML = res.results.map((r) => `
            <div class="panel" style="margin:0 0 .6rem">
              <div style="font-size:.75rem;color:var(--muted);margin-bottom:.3rem">Doc: ${escapeHtml(r.document_name)}  --  score ${r.score.toFixed(3)}</div>
              <p style="font-size:.85rem;margin:0">${escapeHtml(r.content)}</p>
            </div>
          `).join("");
        } catch (e) {
          out.innerHTML = `<p style="color:var(--error);font-size:.8rem">${e.message}</p>`;
        }
      });

      el.querySelectorAll("[data-del]").forEach((b) =>
        b.addEventListener("click", async () => {
          if (!confirm("Delete this document?")) return;
          try {
            await API.del(`/knowledge/documents/${b.dataset.del}`, true);
            window.Toast.success("Deleted");
            render(el);
          } catch (e) { window.Toast.error(e.message); }
        })
      );
    } catch (e) {
      el.innerHTML = `<h2>Knowledge</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  function escapeHtml(s) {
    return String(s || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  return { render };
})();
"""

p = Path("frontend/js/views/knowledge.js")
p.write_text(content, encoding="utf-8")
print("wrote", p)
print("bytes:", len(content))

idx = Path("frontend/index.html")
text = idx.read_text(encoding="utf-8")
if "js/views/knowledge.js" not in text:
    text = text.replace(
        '<script src="js/views/evaluations.js"></script>',
        '<script src="js/views/evaluations.js"></script>\n  <script src="js/views/knowledge.js"></script>',
        1,
    )
    idx.write_text(text, encoding="utf-8")
    print("Added knowledge.js to index.html")
else:
    print("knowledge.js already in index.html")

ph = Path("frontend/js/views/placeholder.js")
pt = ph.read_text(encoding="utf-8")
old = 'window.Views.Knowledge   = makePlaceholder("Knowledge", "Vector-indexed documents and chunks used for retrieval-augmented agents.");\n'
if old in pt:
    pt = pt.replace(old, "")
    ph.write_text(pt, encoding="utf-8")
    print("Removed Knowledge placeholder")
else:
    print("Knowledge placeholder already removed")
