from pathlib import Path

idx = Path("frontend/index.html")
text = idx.read_text(encoding="utf-8")

if "js/views/debug.js" not in text:
    old = '  <script src="js/views/call-detail.js"></script>'
    new = '  <script src="js/views/call-detail.js"></script>\n  <script src="js/views/debug.js"></script>'
    if old in text:
        text = text.replace(old, new, 1)
        idx.write_text(text, encoding="utf-8")
        print("Added debug.js to index.html")
    else:
        print("WARNING: call-detail.js tag not found")
else:
    print("debug.js already in index.html")
