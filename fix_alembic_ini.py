from pathlib import Path
import re

p = Path("backend/alembic.ini")
text = p.read_text(encoding="utf-8")

# Replace the sqlalchemy.url line with an empty value
new_text, n = re.subn(
    r"^sqlalchemy\.url\s*=.*$",
    "sqlalchemy.url =",
    text,
    flags=re.MULTILINE,
)

if n == 0:
    # Key not present — append it in the [alembic] section
    new_text = text.replace("[alembic]", "[alembic]\nsqlalchemy.url =", 1)

p.write_text(new_text, encoding="utf-8")
print("Patched alembic.ini")
print("---")
for line in new_text.splitlines():
    if line.startswith("sqlalchemy.url"):
        print("Found:", repr(line))