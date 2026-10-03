from pathlib import Path

FILES = {}

FILES["backend/app/runtime/tools/__init__.py"] = '''from .registry import TOOLS, register_all

__all__ = ["TOOLS", "register_all"]
'''

FILES["backend/app/runtime/tools/base.py"] = '''from dataclasses import dataclass
from typing import Any, Callable

from pydantic import BaseModel


@dataclass
class ToolDef:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Callable[..., Any]

    def schema(self) -> dict:
        """OpenAI-compatible tool schema for Ollama."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_model.model_json_schema(),
            },
        }
'''

FILES["backend/app/runtime/tools/builtin.py"] = '''import ast
import operator as _op
from datetime import datetime, timezone

from pydantic import BaseModel, Field
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
    title: str
    start_at: str = Field(..., description="ISO 8601 datetime, e.g. '2026-10-04T15:00:00+00:00'")
    duration_minutes: int = Field(60, ge=1, le=1440)
    notes: str | None = None


def _create_event_handler(inp: _CreateEventInput, ctx: dict) -> dict:
    db: Session = ctx["db"]
    tenant_id: str = ctx["tenant_id"]

    start = datetime.fromisoformat(inp.start_at)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    from datetime import timedelta
    end = start + timedelta(minutes=inp.duration_minutes)

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
'''

FILES["backend/app/runtime/tools/registry.py"] = '''from .base import ToolDef
from .builtin import (
    _CalcInput,
    _CreateEventInput,
    _CreateLeadInput,
    _SearchContactInput,
    _TimeInput,
    _calc_handler,
    _create_event_handler,
    _create_lead_handler,
    _search_contact_handler,
    _time_handler,
)

TOOLS: dict[str, ToolDef] = {}


def _register(t: ToolDef) -> None:
    TOOLS[t.name] = t


def register_all() -> None:
    if TOOLS:
        return

    _register(ToolDef(
        name="get_current_time",
        description="Return the current UTC time in ISO 8601 format.",
        input_model=_TimeInput,
        handler=_time_handler,
    ))
    _register(ToolDef(
        name="calculate",
        description="Evaluate a simple arithmetic expression like '2 + 3 * 4'.",
        input_model=_CalcInput,
        handler=_calc_handler,
    ))
    _register(ToolDef(
        name="calendar.create_event",
        description="Create a calendar event for the current tenant.",
        input_model=_CreateEventInput,
        handler=_create_event_handler,
    ))
    _register(ToolDef(
        name="crm.search_contact",
        description="Search customers by partial name or email.",
        input_model=_SearchContactInput,
        handler=_search_contact_handler,
    ))
    _register(ToolDef(
        name="crm.create_lead",
        description="Create a sales lead in the CRM.",
        input_model=_CreateLeadInput,
        handler=_create_lead_handler,
    ))


def all_schemas() -> list[dict]:
    register_all()
    return [t.schema() for t in TOOLS.values()]


def execute_tool(name: str, arguments: dict, ctx: dict) -> dict:
    register_all()
    tool = TOOLS.get(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")

    validated = tool.input_model(**arguments)
    return tool.handler(validated, ctx)
'''

for path, content in FILES.items():
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"wrote {path}")

print(f"\nTotal: {len(FILES)} files")