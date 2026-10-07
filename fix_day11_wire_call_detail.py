from pathlib import Path

p = Path("frontend/js/views/call-detail.js")
text = p.read_text(encoding="utf-8")

# 1) Add Debug button + panel to the HTML (before the back button)
old_btn = '        <button class="btn secondary" id="back">Back to Calls</button>'
new_btn = '''        <div id="debug-section" class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem">AI Debugger</h3>
          <p style="color:var(--muted);font-size:.75rem;margin:0 0 .6rem">
            Analyze this call to identify failures and get fix suggestions.
          </p>
          <button class="btn" id="btn-debug">Analyze Call</button>
          <div id="debug-result" style="margin-top:.8rem"></div>
        </div>

        <button class="btn secondary" id="back">Back to Calls</button>'''

if old_btn not in text:
    print("WARNING: back button anchor not found")
else:
    text = text.replace(old_btn, new_btn, 1)

# 2) Add the click handler before the back handler
old_back = '      document.getElementById("back").addEventListener("click", () => Router.go("#/calls"));'
new_back = '''      document.getElementById("back").addEventListener("click", () => Router.go("#/calls"));

      document.getElementById("btn-debug").addEventListener("click", async () => {
        const out = document.getElementById("debug-result");
        out.innerHTML = "<p style='color:var(--muted);font-size:.8rem'>Analyzing...</p>";
        try {
          const report = await API.post(`/debug/calls/${callId}`, {}, true);
          window.Views.DebugPanel.renderInto(out, report);
        } catch (e) {
          out.innerHTML = `<p style="color:var(--error);font-size:.8rem">${e.message}</p>`;
        }
      });'''

if old_back not in text:
    print("WARNING: back click handler not found")
else:
    text = text.replace(old_back, new_back, 1)

p.write_text(text, encoding="utf-8")
print("Patched call-detail.js")
print("has DebugPanel import:", "DebugPanel" in text)
print("has btn-debug:", "btn-debug" in text)