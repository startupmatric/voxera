from pathlib import Path
import re

p = Path("backend/app/routers/calls.py")
text = p.read_text(encoding="utf-8")

# Locate get_call_latency
m = re.search(r"def get_call_latency\(([\s\S]*?)\n\n(@router|def |$)", text)
if not m:
    print("WARNING: get_call_latency function not found")
else:
    body = m.group(0)
    print("--- current get_call_latency ---")
    print(body[:800])

    # Replace the traces query inside it
    old_query = '''    rows = (
        db.query(Trace)
        .filter(Trace.call_id == call_id)
        .all()
    )'''

    new_query = '''    # Match traces by call_id OR by time window (for legacy calls with null call_id)
    rows = (
        db.query(Trace)
        .filter(
            (Trace.call_id == call_id) |
            (
                (Trace.call_id.is_(None)) &
                (Trace.agent_id == call.agent_id) &
                (Trace.created_at >= call.created_at) &
                (Trace.created_at <= call.updated_at)
            )
        )
        .all()
    )'''

    if old_query in text:
        text = text.replace(old_query, new_query)
        print("Patched get_call_latency trace query")
    else:
        # try alternate formatting
        alt = '''    rows = db.query(Trace).filter(Trace.call_id == call_id).all()'''
        if alt in text:
            text = text.replace(alt, new_query)
            print("Patched get_call_latency (alternate form)")
        else:
            print("WARNING: could not match the trace query. Paste the file and I'll fix by hand.")

p.write_text(text, encoding="utf-8")
print("Done")