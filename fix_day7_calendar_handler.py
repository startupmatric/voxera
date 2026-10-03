from pathlib import Path

p = Path("backend/app/runtime/tools/builtin.py")
text = p.read_text(encoding="utf-8")

old = '''    start = datetime.fromisoformat(inp.start_at)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    from datetime import timedelta
    end = start + timedelta(minutes=inp.duration_minutes)'''

new = '''    start = datetime.fromisoformat(inp.start_at)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    from datetime import timedelta
    duration = inp.duration_minutes or 60  # treat 0 or None as 1 hour
    end = start + timedelta(minutes=duration)'''

if old not in text:
    print("WARNING: old block not found — aborting")
else:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("Patched handler — 0 becomes 60 minutes")