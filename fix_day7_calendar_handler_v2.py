from pathlib import Path

p = Path("backend/app/runtime/tools/builtin.py")
text = p.read_text(encoding="utf-8")

old = '''    start = datetime.fromisoformat(inp.start_at)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    from datetime import timedelta
    duration = inp.duration_minutes or 60  # treat 0 or None as 1 hour
    end = start + timedelta(minutes=duration)'''

new = '''    # Robust ISO parsing: accept Z, missing offset, or slight variations
    raw = inp.start_at.strip().replace("Z", "+00:00")
    try:
        start = datetime.fromisoformat(raw)
    except ValueError:
        # Fallback: try without timezone suffix
        start = datetime.fromisoformat(raw.replace("+00:00", ""))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)

    from datetime import timedelta
    duration = int(inp.duration_minutes or 60)
    if duration <= 0:
        duration = 60
    end = start + timedelta(minutes=duration)'''

if old not in text:
    print("WARNING: old handler block not found.")
    print("--- current lines around end =  ---")
    for i, line in enumerate(text.splitlines(), 1):
        if "timedelta" in line or "end =" in line:
            print(f"{i}: {line}")
else:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("Patched handler with robust ISO parsing")