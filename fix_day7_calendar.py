from pathlib import Path

p = Path("backend/app/runtime/tools/builtin.py")
text = p.read_text(encoding="utf-8")

old = '''class _CreateEventInput(BaseModel):
    title: str
    start_at: str = Field(..., description="ISO 8601 datetime, e.g. '2026-10-04T15:00:00+00:00'")
    duration_minutes: int = Field(60, ge=1, le=1440)
    notes: str | None = None'''

new = '''class _CreateEventInput(BaseModel):
    title: str
    start_at: str = Field(..., description="ISO 8601 datetime in UTC, e.g. '2026-10-04T15:00:00+00:00'")
    duration_minutes: int = Field(60, ge=0, le=1440, description="Length in minutes. Use 60 for one hour. If unsure, use 60.")
    notes: str | None = None'''

if old not in text:
    print("WARNING: old block not found — aborting")
else:
    text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print("Patched builtin.py — duration_minutes now accepts 0 and defaults to 60")