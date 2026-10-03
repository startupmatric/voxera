from pathlib import Path

p = Path("backend/app/runtime/tools/builtin.py")
text = p.read_text(encoding="utf-8")

old = '''class _CreateEventInput(BaseModel):
    title: str
    start_at: str = Field(..., description="ISO 8601 datetime in UTC, e.g. '2026-10-04T15:00:00+00:00'")
    duration_minutes: int = Field(60, ge=0, le=1440, description="Length in minutes. Use 60 for one hour. If unsure, use 60.")
    notes: str | None = None'''

new = '''class _CreateEventInput(BaseModel):
    model_config = {"coerce_numbers_to_str": False}

    title: str
    start_at: str = Field(..., description="ISO 8601 datetime in UTC, e.g. '2026-10-04T15:00:00+00:00'")
    duration_minutes: int = Field(60, description="Length in minutes. Use 60 for one hour.")
    notes: str | None = None

    @field_validator("duration_minutes", mode="before")
    @classmethod
    def _coerce_duration(cls, v):
        # Accept int, str, float, or None; default to 60 for anything unusable
        if v is None or v == "":
            return 60
        try:
            n = int(float(v))
        except (TypeError, ValueError):
            return 60
        if n <= 0:
            return 60
        if n > 1440:
            return 1440
        return n'''

if old not in text:
    print("WARNING: old block not found.")
    print("--- current lines with duration_minutes ---")
    for i, line in enumerate(text.splitlines(), 1):
        if "duration_minutes" in line:
            print(f"{i}: {line}")
else:
    text = text.replace(old, new)
    # ensure field_validator is imported
    if "field_validator" not in text.split("\n")[0:20].__str__():
        text = text.replace(
            "from pydantic import BaseModel, Field",
            "from pydantic import BaseModel, Field, field_validator",
        )
    p.write_text(text, encoding="utf-8")
    print("Patched _CreateEventInput with coercion validator")