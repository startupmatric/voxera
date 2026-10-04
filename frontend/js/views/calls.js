window.Views = window.Views || {};
window.Views.Calls = (() => {
  let ws = null;
  let currentCallId = null;

  async function render(el) {
    el.innerHTML = "<h2>Calls</h2><p>Loading...</p>";
    try {
      const agents = await API.get("/agents", true);
      const calls = await API.get("/calls", true);

      el.innerHTML = `
        <h2>Calls</h2>
        <div class="panel">
          <label style="display:block;font-size:.75rem;color:var(--muted);margin-bottom:.3rem">
            Agent to call
          </label>
          <select id="call-agent" class="tenant-switcher" style="width:100%;max-width:400px">
            ${agents.map((a) => `<option value="${a.id}">${a.name}</option>`).join("")}
          </select>
          <div style="margin-top:.8rem;display:flex;gap:.5rem">
            <button class="btn" id="start-call">Start Call</button>
            <button class="btn danger hidden" id="end-call">End Call</button>
          </div>
          <div id="call-status" style="margin-top:.7rem;font-size:.75rem;color:var(--muted)">Not connected</div>
        </div>

        <div class="panel hidden" id="call-panel">
          <h2>Live Call</h2>
          <div id="call-log" class="chat-log"></div>
          <div class="chat-input">
            <textarea id="call-text" placeholder="Type your message..." rows="2"></textarea>
            <button class="btn" id="call-send">Send</button>
          </div>
        </div>

        <div class="panel">
          <h2>Recent Calls</h2>
          ${calls.length === 0
            ? '<p style="color:var(--muted);font-size:.8rem">No calls yet.</p>'
            : `<table class="data">
                <thead><tr><th>ID</th><th>Agent</th><th>Status</th><th>Started</th></tr></thead>
                <tbody>
                  ${calls.map((c) => `
                    <tr>
                      <td>${c.id.slice(0,8)}…</td>
                      <td>${c.agent_id ? c.agent_id.slice(0,8) + "…" : "—"}</td>
                      <td>${c.status}</td>
                      <td>${new Date(c.created_at).toLocaleString()}</td>
                    </tr>`).join("")}
                </tbody>
              </table>`}
        </div>
      `;

      const startBtn = document.getElementById("start-call");
      const endBtn = document.getElementById("end-call");
      const sendBtn = document.getElementById("call-send");
      const textInput = document.getElementById("call-text");
      const statusEl = document.getElementById("call-status");
      const logEl = document.getElementById("call-log");
      const panel = document.getElementById("call-panel");

      function addBubble(role, text, tools) {
        const div = document.createElement("div");
        div.className = "chat-bubble " + role;
        div.textContent = text;
        if (tools && tools.length) {
          const info = document.createElement("div");
          info.style.cssText = "margin-top:.5rem;font-size:.65rem;color:#9ca3af";
          info.textContent = tools.map((t) => `→ ${t.name} (${t.status}, ${t.latency_ms}ms)`).join(" · ");
          div.appendChild(info);
        }
        logEl.appendChild(div);
        logEl.scrollTop = logEl.scrollHeight;
      }

      startBtn.addEventListener("click", () => {
        const agentId = document.getElementById("call-agent").value;
        if (!agentId) return;
        const token = State.token;
        const proto = location.protocol === "https:" ? "wss" : "ws";
        const url = `${proto}://${location.host}/api/ws/calls/${agentId}?token=${encodeURIComponent(token)}`;
        statusEl.textContent = "Connecting…";
        ws = new WebSocket(url);

        ws.onopen = () => { statusEl.textContent = "Connecting (waiting for greeting)…"; };

        ws.onmessage = (ev) => {
          const msg = JSON.parse(ev.data);
          if (msg.type === "call_started") {
            currentCallId = msg.call_id;
            statusEl.textContent = `🟢 Connected — call ${currentCallId.slice(0,8)}…`;
            panel.classList.remove("hidden");
            startBtn.classList.add("hidden");
            endBtn.classList.remove("hidden");
            addBubble("assistant", msg.greeting);
          } else if (msg.type === "llm_started") {
            statusEl.textContent = "🤔 Thinking…";
          } else if (msg.type === "tool_call") {
            statusEl.textContent = `🔧 ${msg.tool} (${msg.status})`;
          } else if (msg.type === "assistant_message") {
            statusEl.textContent = `🟢 Connected — call ${currentCallId.slice(0,8)}…`;
            addBubble("assistant", msg.content, msg.tool_traces);
          } else if (msg.type === "call_ended") {
            statusEl.textContent = "Call ended";
          } else if (msg.type === "error") {
            addBubble("assistant", "[error] " + msg.detail);
          }
        };

        ws.onerror = () => { statusEl.textContent = "Connection error"; };
        ws.onclose = () => {
          statusEl.textContent = "Disconnected";
          startBtn.classList.remove("hidden");
          endBtn.classList.add("hidden");
          ws = null;
        };
      });

      endBtn.addEventListener("click", () => {
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "end_call" }));
        }
        setTimeout(() => { if (ws) ws.close(); }, 300);
      });

      function send() {
        const text = textInput.value.trim();
        if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
        addBubble("user", text);
        textInput.value = "";
        ws.send(JSON.stringify({ type: "user_message", content: text }));
      }

      sendBtn.addEventListener("click", send);
      textInput.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" && !ev.shiftKey) {
          ev.preventDefault();
          send();
        }
      });

    } catch (e) {
      el.innerHTML = `<h2>Calls</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  return { render };
})();