from pathlib import Path
import re

# ---------- 1) calls.py: add call_id=call.id to run_agent ----------
p = Path("backend/app/routers/calls.py")
text = p.read_text(encoding="utf-8")

# Match the run_agent(...) block inside send_message
pattern = re.compile(
    r"result = await run_agent\(\s*"
    r"agent,\s*db,\s*payload\.content,\s*history=history\[:-1\],\s*enable_tools=True\s*"
    r"\)",
    re.DOTALL,
)

replacement = (
    "result = await run_agent(\n"
    "            agent,\n"
    "            db,\n"
    "            payload.content,\n"
    "            history=history[:-1],\n"
    "            enable_tools=True,\n"
    "            call_id=call.id,\n"
    "        )"
)

if pattern.search(text):
    text = pattern.sub(replacement, text)
    p.write_text(text, encoding="utf-8")
    print("Patched calls.py: added call_id=call.id")
else:
    # Try a looser match
    if "call_id=call.id" in text:
        print("calls.py already patched")
    else:
        # find the exact block and print it
        idx = text.find("result = await run_agent(")
        if idx >= 0:
            print("WARNING: pattern didn't match. Current block:")
            print(text[idx:idx + 300])
        else:
            print("WARNING: run_agent call not found")

# ---------- 2) ws_calls.py: same fix ----------
p2 = Path("backend/app/routers/ws_calls.py")
if p2.exists():
    text2 = p2.read_text(encoding="utf-8")
    if "call_id=call.id" not in text2:
        # Find the run_agent call (it uses `content` and `history`)
        pattern2 = re.compile(
            r"result = await run_agent\(\s*"
            r"agent,\s*db,\s*content,\s*history=history\[:-1\],\s*enable_tools=True\s*"
            r"\)",
            re.DOTALL,
        )
        replacement2 = (
            "result = await run_agent(\n"
            "                    agent,\n"
            "                    db,\n"
            "                    content,\n"
            "                    history=history[:-1],\n"
            "                    enable_tools=True,\n"
            "                    call_id=call.id,\n"
            "                )"
        )
        if pattern2.search(text2):
            text2 = pattern2.sub(replacement2, text2)
            p2.write_text(text2, encoding="utf-8")
            print("Patched ws_calls.py: added call_id=call.id")
        else:
            print("WARNING: ws_calls.py run_agent block didn't match")
    else:
        print("ws_calls.py already patched")

# ---------- 3) graph.py: add LLM trace in _llm_node ----------
p3 = Path("backend/app/runtime/graph.py")
text3 = p3.read_text(encoding="utf-8")

if '"kind": "llm"' not in text3 and "'kind': 'llm'" not in text3:
    # Insert an LLM trace right after state["meta"] = {...} in _llm_node
    marker = '    state["meta"] = {'
    idx = text3.find(marker)
    if idx == -1:
        print("WARNING: _llm_node meta block not found")
    else:
        # Find the end of the meta dict
        meta_start = idx + len(marker)
        depth = 1
        i = meta_start
        while i < len(text3) and depth > 0:
            if text3[i] == "{":
                depth += 1
            elif text3[i] == "}":
                depth -= 1
            i += 1
        # i now points just past the closing }
        # find the newline after it
        nl = text3.find("\n", i)
        insert_at = nl + 1 if nl != -1 else len(text3)

        llm_trace = (
            '    # Record an LLM trace for latency attribution\n'
            '    state.setdefault("traces", []).append({\n'
            '        "kind": "llm",\n'
            '        "name": "ollama.generate",\n'
            '        "status": "success",\n'
            '        "input": {"messages": len(messages)},\n'
            '        "output": {"eval_count": result.get("eval_count", 0)},\n'
            '        "error": None,\n'
            '        "latency_ms": float(result.get("total_duration_ms", 0)),\n'
            '    })\n'
        )
        text3 = text3[:insert_at] + llm_trace + text3[insert_at:]
        p3.write_text(text3, encoding="utf-8")
        print("Patched graph.py: added LLM trace")
else:
    print("graph.py already has LLM trace")

print("\nDone.")