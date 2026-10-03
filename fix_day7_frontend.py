from pathlib import Path

content = '''window.Views = window.Views || {};
window.Views.AgentChat = (() => {
  let history = [];

  async function render(el, agentId) {
    history = [];
    el.innerHTML = "<h2>Test Agent</h2><p>Loading...</p>";
    try {
      const a = await API.get(`/agents/${agentId}`, true);

      el.innerHTML = `
        <h2>Test: ${a.name}</h2>
        <div class="tabs">
          <a href="#/agents/${agentId}" class="tab">Configuration</a>
          <a href="#/agents/${agentId}/versions" class="tab">Versions</a>
          <a href="#/agents/${agentId}/chat" class="tab active">Test</a>
        </div>

        <div class="panel">
          <p style="color:var(--muted);font-size:.75rem;margin:0 0 .7rem">
            Messages flow through LangGraph → LLM → tools → LLM. Try:
            <em>What time is it?</em> ·
            <em>What's 234 * 17?</em> ·
            <em>Schedule a meeting tomorrow at 3pm</em> ·
            <em>Create a lead for jane@acme.com</em>
          </p>
          <div id="chat-log" class="chat-log"></div>

          <div class="chat-input">
            <textarea id="chat-text" placeholder="Type a message and press Enter..." rows="2"></textarea>
            <button class="btn" id="chat-send">Send</button>
          </div>
          <div id="chat-meta" style="color:var(--muted);font-size:.7rem;margin-top:.5rem"></div>
        </div>
      `;

      const log = document.getElementById("chat-log");
      const input = document.getElementById("chat-text");

      function addBubble(role, text, tools) {
        const div = document.createElement("div");
        div.className = "chat-bubble " + role;
        div.textContent = text;
        if (tools && tools.length) {
          const toolInfo = document.createElement("div");
          toolInfo.style.cssText = "margin-top:.5rem;font-size:.65rem;color:#9ca3af";
          toolInfo.textContent = tools.map((t) =>
            `→ ${t.name} (${t.status}, ${t.latency_ms}ms)`
          ).join(" · ");
          div.appendChild(toolInfo);
        }
        log.appendChild(div);
        log.scrollTop = log.scrollHeight;
      }

      async function send() {
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        addBubble("user", text);
        history.push({ role: "user", content: text });

        const meta = document.getElementById("chat-meta");
        meta.textContent = "Thinking...";

        try {
          const res = await API.post(`/agents/${agentId}/chat`, {
            message: text,
            history: history.slice(0, -1),
            enable_tools: true,
          }, true);

          history.push({ role: "assistant", content: res.response });
          addBubble("assistant", res.response, res.tool_traces);

          const toolCount = (res.tool_traces || []).length;
          meta.textContent =
            `v${res.version} · ${res.meta.model} · ${res.meta.total_ms}ms · ` +
            `${res.meta.prompt_tokens}+${res.meta.completion_tokens} tokens · ` +
            `${toolCount} tool call${toolCount === 1 ? "" : "s"}`;
        } catch (e) {
          addBubble("assistant", "[error] " + e.message);
          meta.textContent = "";
        }
      }

      document.getElementById("chat-send").addEventListener("click", send);
      input.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" && !ev.shiftKey) {
          ev.preventDefault();
          send();
        }
      });

      addBubble("assistant", "Hi! Send a message. I can check time, do math, schedule meetings, or work with the CRM.");
    } catch (e) {
      el.innerHTML = `<h2>Test</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  return { render };
})();
'''

Path("frontend/js/views/chat.js").write_text(content, encoding="utf-8")
print("Wrote chat.js")
print("Has tool_traces:", "tool_traces" in content)