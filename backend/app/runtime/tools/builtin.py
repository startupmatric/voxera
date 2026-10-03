import ast
import operator as _op
from datetime import datetime, timezone

from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ...models import CalendarEvent, Customer, Lead

# ------------------------------------------------------------------
# get_current_time
# ------------------------------------------------------------------


class _TimeInput(BaseModel):
    pass


def _time_handler(_: _TimeInput, ctx: dict) -> dict:
    return {"now": datetime.now(timezone.utc).isoformat()}


# ------------------------------------------------------------------
# calculate
# ------------------------------------------------------------------

_OPS = {
    ast.Add: _op.add, ast.Sub: _op.sub, ast.Mult: _op.mul,
    ast.Div: _op.truediv, ast.Mod: _op.mod, ast.Pow: _op.pow,
    ast.USub: _op.neg, ast.UAdd: _op.pos,
}


def _eval_expr(node):
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.BinOp):
        return _OPS[type(node.op)](_eval_expr(node.left), _eval_expr(node.right))
    if isinstance(node, ast.UnaryOp):
        return _OPS[type(node.op)](_eval_expr(node.operand))
    raise ValueError("unsupported expression")


class _CalcInput(BaseModel):
    expression: str = Field(..., description="Arithmetic expression, e.g. '2 + 3 * 4'")


def _calc_handler(inp: _CalcInput, ctx: dict) -> dict:
    tree = ast.parse(inp.expression, mode="eval")
    return {"result": _eval_expr(tree.body)}


# ------------------------------------------------------------------
# calendar.create_event
# ------------------------------------------------------------------


class _CreateEventInput(BaseModel):
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
        return n


def _create_event_handler(inp: _CreateEventInput, ctx: dict) -> dict:
    db: Session = ctx["db"]
    tenant_id: str = ctx["tenant_id"]

    # Robust ISO parsing: accept Z, missing offset, or slight variations
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
    end = start + timedelta(minutes=duration)

    ev = CalendarEvent(
        tenant_id=tenant_id,
        title=inp.title,
        start_at=start,
        end_at=end,
        notes=inp.notes,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)

    return {
        "id": ev.id,
        "title": ev.title,
        "start_at": ev.start_at.isoformat(),
        "end_at": ev.end_at.isoformat(),
    }


# ------------------------------------------------------------------
# crm.search_contact
# ------------------------------------------------------------------


class _SearchContactInput(BaseModel):
    query: str = Field(..., description="Name fragment or email to match")


def _search_contact_handler(inp: _SearchContactInput, ctx: dict) -> dict:
    db: Session = ctx["db"]
    tenant_id: str = ctx["tenant_id"]

    q = inp.query.strip().lower()
    rows = (
        db.query(Customer)
        .filter(
            Customer.tenant_id == tenant_id,
            (Customer.email.ilike(f"%{q}%")) | (Customer.name.ilike(f"%{q}%")),
        )
        .limit(5)
        .all()
    )
    return {
        "count": len(rows),
        "results": [
            {"id": c.id, "name": c.name, "email": c.email, "phone": c.phone}
            for c in rows
        ],
    }


# ------------------------------------------------------------------
# crm.create_lead
# ------------------------------------------------------------------


class _CreateLeadInput(BaseModel):
    name: str
    email: str | None = None
    source: str | None = Field(None, description="e.g. 'website', 'phone', 'referral'")
    notes: str | None = None


def _create_lead_handler(inp: _CreateLeadInput, ctx: dict) -> dict:
    db: Session = ctx["db"]
    tenant_id: str = ctx["tenant_id"]

    lead = Lead(
        tenant_id=tenant_id,
        name=inp.name,
        email=inp.email,
        source=inp.source,
        status="new",
        notes=inp.notes,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return {"id": lead.id, "name": lead.name, "status": lead.status}
