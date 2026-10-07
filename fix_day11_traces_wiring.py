from pathlib import Path

idx = Path("frontend/index.html")
text = idx.read_text(encoding="utf-8")

if "js/views/traces.js" not in text:
    old = '  <script src="js/views/evaluations.js"></script>'
    new = '  <script src="js/views/evaluations.js"></script>\n  <script src="js/views/traces.js"></script>'
    if old in text:
        text = text.replace(old, new, 1)
        idx.write_text(text, encoding="utf-8")
        print("Added traces.js to index.html")
    else:
        print("WARNING: evaluations.js script tag not found")
else:
    print("traces.js already in index.html")

ph = Path("frontend/js/views/placeholder.js")
pt = ph.read_text(encoding="utf-8")

# Remove both placeholder lines if still present
for marker in [
    'window.Views.Traces      = makePlaceholder("Traces", "Step-by-step execution traces for every agent turn -- LLM calls, tool invocations, and timings.");\n',
    'window.Views.Traces = makePlaceholder("Traces", "Step-by-step execution traces for every agent turn -- LLM calls, tool invocations, and timings.");\n',
]:
    if marker in pt:
        pt = pt.replace(marker, "")
        ph.write_text(pt, encoding="utf-8")
        print("Removed Traces placeholder")
        break
else:
    print("Traces placeholder already removed or pattern differs")

print("Done")
