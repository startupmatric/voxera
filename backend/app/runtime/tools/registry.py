from .base import ToolDef
from .builtin import (
    _CalcInput,
    _CreateEventInput,
    _CreateLeadInput,
    _KnowledgeSearchInput,
    _SearchContactInput,
    _TimeInput,
    _calc_handler,
    _create_event_handler,
    _create_lead_handler,
    _knowledge_search_handler,
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
    _register(ToolDef(
        name="knowledge.search",
        description="Search the tenant's knowledge base for relevant documents. Use this when the user asks a question that may be covered by uploaded documents.",
        input_model=_KnowledgeSearchInput,
        handler=_knowledge_search_handler,
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
