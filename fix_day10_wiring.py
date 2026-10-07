from pathlib import Path

idx = Path("frontend/index.html")
text = idx.read_text(encoding="utf-8")

if "js/views/evaluations.js" not in text:
    old = '  <script src="js/views/placeholder.js"></script>'
    new = '  <script src="js/views/placeholder.js"></script>\n  <script src="js/views/evaluations.js"></script>'
    if old in text:
        text = text.replace(old, new, 1)
        idx.write_text(text, encoding="utf-8")
        print("Added evaluations.js to index.html")
    else:
        print("WARNING: placeholder.js script tag not found")
else:
    print("evaluations.js already in index.html")

ph = Path("frontend/js/views/placeholder.js")
pt = ph.read_text(encoding="utf-8")
old = 'window.Views.Evaluations = makePlaceholder("Evaluations", "Automated quality scoring and regression tests against agent versions.");\n'
if old in pt:
    pt = pt.replace(old, "")
    ph.write_text(pt, encoding="utf-8")
    print("Removed Evaluations placeholder")
else:
    print("Evaluations placeholder already removed or not found")

print("Done")
