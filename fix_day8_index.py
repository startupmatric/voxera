from pathlib import Path

p = Path("frontend/index.html")
text = p.read_text(encoding="utf-8")

old = '''  <script src="js/views/placeholder.js"></script>
  <script src="js/views/settings.js"></script>'''

new = '''  <script src="js/views/placeholder.js"></script>
  <script src="js/views/calls.js"></script>
  <script src="js/views/settings.js"></script>'''

if "js/views/calls.js" in text:
    print("calls.js is already in index.html — nothing to do")
elif old not in text:
    print("WARNING: expected block not found. Current script block:")
    for i, line in enumerate(text.splitlines(), 1):
        if "views/" in line:
            print(f"  {i}: {line}")
else:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("Patched index.html — added calls.js after placeholder.js")