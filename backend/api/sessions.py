from fastapi import APIRouter, Depends, HTTPException
from backend.modules.session_store import SessionStore
from backend.modules.config_manager import SessionConfigManager
from backend.dependencies import get_session_store, get_config_manager
from backend.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionDetailResponse,
    ChatMessageResponse,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions(store: SessionStore = Depends(get_session_store)):
    return await store.list_sessions()


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(
    body: SessionCreate, store: SessionStore = Depends(get_session_store)
):
    return await store.create_session(body.name)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
    config_mgr: SessionConfigManager = Depends(get_config_manager),
):
    session = await store.get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    config = await config_mgr.get_config(session_id)
    return {**session, "config": config}


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str, store: SessionStore = Depends(get_session_store)
):
    await store.delete_session(session_id)


@router.get("/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    session_id: str,
    store: SessionStore = Depends(get_session_store),
    limit: int = 100,
):
    return await store.get_messages(session_id, limit=limit)
