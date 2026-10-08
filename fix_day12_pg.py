from pathlib import Path

p = Path("docker-compose.yml")
text = p.read_text(encoding="utf-8")

if "pgvector/pgvector" in text:
    print("Already using pgvector image")
else:
    # Replace only the postgres:16-alpine image line for the postgres service
    import re
    old = "image: postgres:16-alpine"
    new = "image: pgvector/pgvector:pg16"
    if old in text:
        text = text.replace(old, new, 1)
        p.write_text(text, encoding="utf-8")
        print("Swapped postgres image to pgvector/pgvector:pg16")
    else:
        print("WARNING: 'image: postgres:16-alpine' not found")

# Also add pgvector to requirements.txt (Python client)
r = Path("backend/requirements.txt")
rt = r.read_text(encoding="utf-8")
if "pgvector" not in rt:
    rt = rt.rstrip() + "\npgvector==0.3.6\n"
    r.write_text(rt, encoding="utf-8")
    print("Added pgvector to requirements.txt")
else:
    print("pgvector already in requirements.txt")