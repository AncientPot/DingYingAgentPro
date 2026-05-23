import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from backend.modules.agent_core import AgentCore
from backend.modules.session_store import SessionStore
from backend.modules.config_manager import SessionConfigManager
from backend.dependencies import get_agent_core, get_session_store, get_config_manager
from backend.schemas.chat import ChatRequest

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/stream")
async def stream_chat(
    body: ChatRequest,
    agent: AgentCore = Depends(get_agent_core),
    store: SessionStore = Depends(get_session_store),
    config_mgr: SessionConfigManager = Depends(get_config_manager),
):
    session = await store.get_session(body.session_id)
    if session is None:
        raise HTTPException(404, "Session not found")

    effective_config = await config_mgr.get_effective_config(body.session_id)

    await store.save_message(body.session_id, "user", body.message)

    async def event_stream_with_save():
        full_response = ""
        try:
            async for sse_event in agent.stream_chat(
                body.session_id, body.message, effective_config
            ):
                if sse_event.startswith("event: content"):
                    try:
                        data_str = sse_event.split("data: ", 1)[1].strip()
                        delta = json.loads(data_str).get("delta", "")
                        full_response += delta
                    except Exception:
                        pass
                yield sse_event
            if full_response:
                await store.save_message(
                    body.session_id, "assistant", full_response
                )
        finally:
            await store.touch_session(body.session_id)

    return StreamingResponse(
        event_stream_with_save(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
