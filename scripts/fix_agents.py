from pathlib import Path

content = '''from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth.dependencies import get_current_tenant, require_roles
from ..database import get_db
from ..models import Agent, AgentVersion, Tenant, User
from ..schemas.agent import AgentCreate, AgentOut, AgentUpdate
from ..schemas.agent_version import AgentVersionOut

router = APIRouter(prefix="/agents", tags=["agents"])


def _snapshot_agent(agent: Agent) -> dict:
    return {
        "system_prompt": agent.system_prompt,
        "model_name": agent.model_name,
        "temperature": agent.temperature,
        "configuration": {
            "model_provider": agent.model_provider,
            "voice_language": agent.voice_language,
            "stt_provider": agent.stt_provider,
            "tts_provider": agent.tts_provider,
        },
    }


def _next_version_number(db: Session, agent_id: str) -> int:
    current_max = (
        db.query(func.max(AgentVersion.version))
        .filter(AgentVersion.agent_id == agent_id)
        .scalar()
    )
    return (current_max or 0) + 1


def _deactivate_all_versions(db: Session, agent_id: str) -> None:
    db.query(AgentVersion).filter(
        AgentVersion.agent_id == agent_id, AgentVersion.is_active.is_(True)
    ).update({"is_active": False})


def _load_agent_for_user(db: Session, agent_id: str, tenant: Tenant) -> Agent:
    agent = (
        db.query(Agent)
        .filter(Agent.id == agent_id, Agent.tenant_id == tenant.id)
        .first()
    )
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("", response_model=AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    tenant = (
        db.query(Tenant)
        .filter(
            Tenant.id == payload.tenant_id,
            Tenant.organization_id == user.organization_id,
            Tenant.is_active.is_(True),
        )
        .first()
    )
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    exists = (
        db.query(Agent)
        .filter(Agent.tenant_id == tenant.id, Agent.name == payload.name)
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="Agent with this name already exists")

    agent = Agent(**payload.model_dump())
    db.add(agent)
    db.flush()

    v1 = AgentVersion(
        agent_id=agent.id,
        version=1,
        is_active=True,
        **_snapshot_agent(agent),
    )
    db.add(v1)

    db.commit()
    db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentOut])
def list_agents(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return (
        db.query(Agent)
        .filter(Agent.tenant_id == tenant.id)
        .order_by(Agent.created_at.desc())
        .all()
    )


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(
    agent_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return _load_agent_for_user(db, agent_id, tenant)


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    user: User = Depends(require_roles("owner", "admin")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    agent = _load_agent_for_user(db, agent_id, tenant)

    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        return agent

    # Apply the updates to the agent FIRST
    for k, v in updates.items():
        setattr(agent, k, v)

    # Then snapshot the NEW state into a new draft version
    next_n = _next_version_number(db, agent.id)
    draft = AgentVersion(
        agent_id=agent.id,
        version=next_n,
        is_active=False,
        **_snapshot_agent(agent),
    )
    db.add(draft)

    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(
    agent_id: str,
    user: User = Depends(require_roles("owner", "admin")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    agent = _load_agent_for_user(db, agent_id, tenant)
    db.delete(agent)
    db.commit()
    return None


# ---------------------- Versions ----------------------


@router.get("/{agent_id}/versions", response_model=list[AgentVersionOut])
def list_versions(
    agent_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_agent_for_user(db, agent_id, tenant)
    return (
        db.query(AgentVersion)
        .filter(AgentVersion.agent_id == agent_id)
        .order_by(AgentVersion.version.desc())
        .all()
    )


@router.get("/{agent_id}/versions/{version_id}", response_model=AgentVersionOut)
def get_version(
    agent_id: str,
    version_id: str,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    _load_agent_for_user(db, agent_id, tenant)
    v = (
        db.query(AgentVersion)
        .filter(AgentVersion.id == version_id, AgentVersion.agent_id == agent_id)
        .first()
    )
    if not v:
        raise HTTPException(status_code=404, detail="Version not found")
    return v


@router.post("/{agent_id}/versions/{version_id}/activate", response_model=AgentVersionOut)
def activate_version(
    agent_id: str,
    version_id: str,
    user: User = Depends(require_roles("owner", "admin")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    agent = _load_agent_for_user(db, agent_id, tenant)
    target = (
        db.query(AgentVersion)
        .filter(AgentVersion.id == version_id, AgentVersion.agent_id == agent_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")

    _deactivate_all_versions(db, agent.id)
    target.is_active = True

    agent.system_prompt = target.system_prompt
    agent.model_name = target.model_name
    agent.temperature = target.temperature
    cfg = target.configuration or {}
    if "model_provider" in cfg:
        agent.model_provider = cfg["model_provider"]
    if "voice_language" in cfg:
        agent.voice_language = cfg["voice_language"]
    if "stt_provider" in cfg:
        agent.stt_provider = cfg["stt_provider"]
    if "tts_provider" in cfg:
        agent.tts_provider = cfg["tts_provider"]

    db.commit()
    db.refresh(target)
    return target


@router.post("/{agent_id}/versions/{version_id}/rollback", response_model=AgentVersionOut)
def rollback_version(
    agent_id: str,
    version_id: str,
    user: User = Depends(require_roles("owner", "admin")),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return activate_version(agent_id, version_id, user, tenant, db)
'''

p = Path("backend/app/routers/agents.py")
p.write_text(content, encoding="utf-8")
print(f"Wrote {p}")
print("First 10 chars:", content[:10])
print("Contains marker:", "Apply the updates to the agent FIRST" in content)