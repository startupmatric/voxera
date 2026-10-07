window.Views = window.Views || {};
window.Views.Calls = (() => {
  let ws = null;
  let currentCallId = null;
  let recording = false;
  let audioPlayer = null;
  let autoPlay = true;
  let recordStartTs = 0;

  function blobToBase64(blob) {
    return new Promise((resolve) => {
      const r = new FileReader();
      r.onloadend = () => {
        const s = r.result;
        const comma = s.indexOf(",");
        resolve(comma >= 0 ? s.substring(comma + 1) : "");
      };
      r.readAsDataURL(blob);
    });
  }

  function b64ToBlob(b64, mime) {
    const bin = atob(b64);
    const bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new Blob([bytes], { type: mime || "audio/wav" });
  }

  async function render(el) {
    el.innerHTML = "<h2>Calls</h2><p>Loading...</p>";
    try {
      const agents = await API.get("/agents", true);
      const calls = await API.get("/calls", true);

      el.innerHTML = `
        <h2>Calls</h2>

        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem;letter-spacing:.05em">Start a New Call</h3>
          <label style="display:block;font-size:.75rem;color:var(--muted);margin-bottom:.3rem">
            Agent to call
          </label>
          <select id="call-agent" class="tenant-switcher" style="width:100%;max-width:400px">
            ${agents.map((a) => `<option value="${a.id}">${a.name}</option>`).join("")}
          </select>

          <div style="margin-top:.8rem;display:flex;gap:.5rem;align-items:center;flex-wrap:wrap">
            <button class="btn" id="start-call">Start Call</button>
            <button class="btn danger hidden" id="end-call">End Call</button>
            <button class="btn hidden" id="ptt-btn">🎙️ Hold to Talk</button>
            <button class="btn secondary hidden" id="mute-btn">🔇 Mute</button>
            <label class="voice-toggle">
              <input type="checkbox" id="auto-play" checked />
              <span>Auto-play audio</span>
            </label>
          </div>
          <div id="call-status" style="margin-top:.7rem;font-size:.75rem;color:var(--muted)">Not connected</div>
        </div>

        <div class="panel hidden" id="call-panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem;letter-spacing:.05em">Live Call</h3>
          <div id="call-log" class="chat-log"></div>
          <div class="chat-input">
            <textarea id="call-text" placeholder="Type a message, or hold the 🎙️ button..." rows="2"></textarea>
            <button class="btn" id="call-send">Send</button>
          </div>
        </div>

        <div class="panel">
          <h3 style="margin:0 0 .6rem;font-size:.9rem;letter-spacing:.05em">Recent Calls</h3>
          ${calls.length === 0
            ? '<p style="color:var(--muted);font-size:.8rem">No calls yet.</p>'
            : `<table class="data">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Agent</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Msgs</th>
                    <th>Traces</th>
                    <th>Started</th>
                  </tr>
                </thead>
                <tbody>
                  ${calls.map((c) => `
                    <tr>
                      <td><a href="#/calls/${c.id}" style="color:var(--accent)">${c.id.slice(0,8)}…</a></td>
                      <td>${c.agent_name || "—"}</td>
                      <td>${c.status}</td>
                      <td>${(c.duration_ms / 1000).toFixed(2)}s</td>
                      <td>${c.message_count}</td>
                      <td>${c.trace_count}</td>
                      <td>${new Date(c.created_at).toLocaleString()}</td>
                    </tr>`).join("")}
                </tbody>
              </table>`}
        </div>
      `;

      const startBtn = document.getElementById("start-call");
      const endBtn   = document.getElementById("end-call");
      const pttBtn   = document.getElementById("ptt-btn");
      const muteBtn  = document.getElementById("mute-btn");
      const sendBtn  = document.getElementById("call-send");
      const textInput = document.getElementById("call-text");
      const statusEl = document.getElementById("call-status");
      const logEl    = document.getElementById("call-log");
      const panel    = document.getElementById("call-panel");
      const autoPlayEl = document.getElementById("auto-play");

      autoPlayEl.addEventListener("change", () => { autoPlay = autoPlayEl.checked; });

      function setStatus(s) { statusEl.textContent = s; }

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

      function playAudioFromBase64(b64, mime) {
        try {
          const blob = b64ToBlob(b64, mime);
          const url = URL.createObjectURL(blob);
          if (!audioPlayer) audioPlayer = new Audio();
          audioPlayer.src = url;
          audioPlayer.play().catch(() => {});
        } catch (e) { console.warn("audio play failed", e); }
      }

      startBtn.addEventListener("click", async () => {
        const agentId = document.getElementById("call-agent").value;
        if (!agentId) return;
        const token = State.token;
        const proto = location.protocol === "https:" ? "wss" : "ws";
        const url = `${proto}://${location.host}/api/ws/calls/${agentId}?token=${encodeURIComponent(token)}`;
        setStatus("Connecting…");
        ws = new WebSocket(url);

        ws.onopen = () => { setStatus("Connected (waiting for greeting)…"); };

        ws.onmessage = (ev) => {
          const msg = JSON.parse(ev.data);
          if (msg.type === "call_started") {
            currentCallId = msg.call_id;
            setStatus(`🟢 Connected — call ${currentCallId.slice(0,8)}…`);
            panel.classList.remove("hidden");
            startBtn.classList.add("hidden");
            pttBtn.classList.remove("hidden");
            muteBtn.classList.remove("hidden");
            endBtn.classList.remove("hidden");
            addBubble("assistant", msg.greeting);
          } else if (msg.type === "llm_started") {
            setStatus("🤔 Thinking…");
          } else if (msg.type === "stt_started") {
            setStatus("📝 Transcribing…");
          } else if (msg.type === "transcript") {
            addBubble("user", msg.content);
            setStatus("🤔 Thinking…");
          } else if (msg.type === "tool_call") {
            setStatus(`🔧 ${msg.tool} (${msg.status})`);
          } else if (msg.type === "assistant_message") {
            setStatus(`🟢 Connected — call ${currentCallId.slice(0,8)}…`);
            addBubble("assistant", msg.content, msg.tool_traces);
            if (autoPlay && msg.audio) {
              playAudioFromBase64(msg.audio, "audio/wav");
            }
          } else if (msg.type === "call_ended") {
            setStatus("Call ended");
          } else if (msg.type === "error") {
            addBubble("assistant", "[error] " + msg.detail);
          }
        };

        ws.onerror = () => setStatus("Connection error");
        ws.onclose = () => {
          setStatus("Disconnected");
          startBtn.classList.remove("hidden");
          pttBtn.classList.add("hidden");
          muteBtn.classList.add("hidden");
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

      function sendText() {
        const text = textInput.value.trim();
        if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
        textInput.value = "";
        ws.send(JSON.stringify({ type: "user_message", content: text }));
      }
      sendBtn.addEventListener("click", sendText);
      textInput.addEventListener("keydown", (ev) => {
        if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); sendText(); }
      });

      // ---------- Push-to-talk ----------
      async function startRecording() {
        if (!ws || ws.readyState !== WebSocket.OPEN) return;
        if (recording) return;
        recording = true;
        recordStartTs = Date.now();
        pttBtn.textContent = "🔴 Recording… release to send";
        try {
          await Voice.start({
            onChunk: async (blob) => {
              const b64 = await blobToBase64(blob);
              ws.send(JSON.stringify({ type: "audio_chunk", audio: b64 }));
            },
            onEnd: () => {},
          });
        } catch (e) {
          recording = false;
          pttBtn.textContent = "🎙️ Hold to Talk";
          addBubble("assistant", "[error] mic: " + e.message);
        }
      }
      async function stopRecording() {
        if (!recording) return;
        const durationMs = Date.now() - recordStartTs;
        recording = false;
        pttBtn.textContent = "??? Hold to Talk";
        try {
          await Voice.stop();
          if (durationMs < 300) {
            addBubble("assistant", "Please hold the button a bit longer while speaking.");
            ws.send(JSON.stringify({ type: "audio_cancel" }));
            return;
          }
          ws.send(JSON.stringify({ type: "audio_end" }));
        } catch (e) { console.warn(e); }
      }
      function bindHold(btn) {
        btn.addEventListener("mousedown", startRecording);
        btn.addEventListener("mouseup", stopRecording);
        btn.addEventListener("mouseleave", stopRecording);
        btn.addEventListener("touchstart", (e) => { e.preventDefault(); startRecording(); });
        btn.addEventListener("touchend",   (e) => { e.preventDefault(); stopRecording(); });
      }
      bindHold(pttBtn);

      muteBtn.addEventListener("click", () => {
        const m = !Voice.isMuted();
        Voice.setMuted(m);
        muteBtn.textContent = m ? "🔊 Unmute" : "🔇 Mute";
      });

    } catch (e) {
      el.innerHTML = `<h2>Calls</h2><p style="color:var(--error)">${e.message}</p>`;
    }
  }

  return { render };
})();