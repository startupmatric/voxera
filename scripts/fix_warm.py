from pathlib import Path

content = '{"model":"llama3.2:3b","messages":[{"role":"user","content":"hi"}],"stream":false}'
Path("warm.json").write_text(content, encoding="utf-8")
print("Wrote warm.json")