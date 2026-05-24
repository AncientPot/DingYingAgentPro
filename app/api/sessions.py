"""会话管理接口。"""

import logging

from fastapi import APIRouter, HTTPException, Request

from app.models.schemas import (
    MessageResponse,
    SessionCreateRequest,
    SessionInfo,
    SessionListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
def list_sessions(request: Request):
    """列出所有会话。"""
    session_svc = request.app.state.session_service
    sessions = session_svc.list_sessions()
    return SessionListResponse(
        sessions=[SessionInfo(**s) for s in sessions]
    )


@router.post("", response_model=SessionInfo)
def create_session(req: SessionCreateRequest, request: Request):
    """创建新会话（若同名已存在则返回已有会话）。"""
    session_svc = request.app.state.session_service
    result = session_svc.get_or_create_session(req.name)
    return SessionInfo(name=result["name"], thread_id=result["thread_id"])


@router.delete("/{session_name}", response_model=MessageResponse)
def delete_session(session_name: str, request: Request):
    """删除指定会话。"""
    session_svc = request.app.state.session_service
    success = session_svc.delete_session(session_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"会话 '{session_name}' 不存在。")
    return MessageResponse(detail=f"会话 '{session_name}' 已删除。")
