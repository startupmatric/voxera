from pathlib import Path

p = Path("backend/app/runtime/ollama_client.py")
text = p.read_text(encoding="utf-8")

old = '''        "options": {"temperature": temperature},'''
new = '''        "options": {
            "temperature": temperature,
            "num_predict": 200,   # cap response length; keeps CPU latency sane
            "num_ctx": 4096,      # context window
        },'''

if old not in text:
    print("WARNING: options block not found. Current file has:")
    for i, line in enumerate(text.splitlines(), 1):
        if '"options"' in line or "temperature" in line.lower():
            print(f"{i}: {line}")
else:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("Patched: num_predict=200, num_ctx=4096")