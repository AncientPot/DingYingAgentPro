"""会话管理接口。"""

import logging

from fastapi import APIRouter, HTTPException, Request
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from app.agent.graph import get_checkpointer
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


@router.get("/{session_name}/messages")
def get_session_messages(session_name: str, request: Request):
    """获取指定会话的历史消息（从 LangGraph checkpoints 读取）。"""
    session_svc = request.app.state.session_service
    session_svc._ensure_loaded()

    if session_name not in session_svc._name_to_tid:
        return {"messages": []}

    tid = session_svc._name_to_tid[session_name]
    config = {"configurable": {"thread_id": tid}}

    try:
        memory = get_checkpointer()
        tup = memory.get_tuple(config)
    except Exception:
        return {"messages": []}

    if not tup:
        return {"messages": []}

    checkpoint = tup.checkpoint
    raw_msgs = checkpoint.get("channel_values", {}).get("messages", [])

    # 序列化为前端可用的格式
    result = []
    for m in raw_msgs:
        if isinstance(m, HumanMessage):
            result.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            entry = {"role": "assistant", "content": m.content or ""}
            if hasattr(m, "tool_calls") and m.tool_calls:
                entry["tool_calls"] = [
                    {"name": tc.get("name", ""), "args": tc.get("args", {}), "id": tc.get("id", "")}
                    for tc in m.tool_calls
                ]
            result.append(entry)
        elif isinstance(m, ToolMessage):
            result.append({
                "role": "tool",
                "name": getattr(m, "name", ""),
                "tool_call_id": getattr(m, "tool_call_id", ""),
                "content": m.content,
            })

    return {"messages": result}
