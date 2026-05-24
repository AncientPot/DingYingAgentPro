"""
聊天接口 —— 流式（SSE）与非流式。
"""

import json
import logging
from queue import Queue as ThreadQueue

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage

from app.agent.graph import get_graph
from app.models.schemas import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


def _serialize_stream_event(event) -> str:
    """将 langgraph 流事件序列化为 JSON 字符串。"""
    message = event[0]
    if isinstance(message, AIMessageChunk):
        return json.dumps({
            "type": "chunk",
            "content": message.content,
            "tool_calls": getattr(message, "tool_calls", None),
        }, ensure_ascii=False)
    elif isinstance(message, ToolMessage):
        return json.dumps({
            "type": "tool",
            "tool_name": getattr(message, "name", "unknown"),
            "content": message.content,
        }, ensure_ascii=False)
    else:
        return json.dumps({"type": "unknown", "content": str(message)}, ensure_ascii=False)


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    """
    非流式聊天：发送消息并等待完整响应后返回。
    适合轮询或无需逐字展示的场景。
    """
    session_svc = request.app.state.session_service
    graph = get_graph()
    if graph is None:
        raise HTTPException(status_code=503, detail="Agent 未就绪，请检查配置。")

    session = session_svc.get_or_create_session(req.session_name)
    input_state = {"messages": [HumanMessage(content=req.message)]}
    total_tokens = 0
    final_content = ""
    tool_calls_result = []

    try:
        for r in graph.stream(input_state, stream_mode="values", config=session["config"]):
            message = r["messages"][-1]
            if isinstance(message, AIMessage):
                final_content = message.content or ""
                if hasattr(message, "usage_metadata") and message.usage_metadata:
                    total_tokens += message.usage_metadata.get("total_tokens", 0)
                if hasattr(message, "tool_calls") and message.tool_calls:
                    tool_calls_result = message.tool_calls
    except Exception as e:
        logger.error(f"聊天请求失败: {e}")
        raise HTTPException(status_code=500, detail=f"处理消息失败: {e}")

    return ChatResponse(
        session_name=req.session_name,
        content=final_content,
        tool_calls=tool_calls_result if tool_calls_result else None,
        tokens=total_tokens,
    )


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    """
    流式聊天：通过 Server-Sent Events 逐字推送响应。
    前端使用 EventSource 或在 fetch 中读取 ReadableStream 消费。
    """
    session_svc = request.app.state.session_service
    graph = get_graph()
    if graph is None:
        raise HTTPException(status_code=503, detail="Agent 未就绪，请检查配置。")

    session = session_svc.get_or_create_session(req.session_name)
    input_state = {"messages": [HumanMessage(content=req.message)]}

    async def event_generator():
        import asyncio
        sync_queue: ThreadQueue = ThreadQueue()

        def run_stream():
            try:
                for event in graph.stream(
                    input_state, stream_mode="messages", config=session["config"]
                ):
                    sync_queue.put(("data", event))
            except Exception as exc:
                sync_queue.put(("error", str(exc)))
            finally:
                sync_queue.put(("done", None))

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, run_stream)

        total_tokens = 0

        while True:
            msg_type, msg_data = await loop.run_in_executor(None, sync_queue.get)

            if msg_type == "done":
                yield f"data: {json.dumps({'type': 'done', 'tokens': total_tokens})}\n\n"
                break
            elif msg_type == "error":
                yield f"data: {json.dumps({'type': 'error', 'content': msg_data})}\n\n"
                break
            else:
                message = msg_data[0]
                if isinstance(message, AIMessageChunk):
                    if hasattr(message, "usage_metadata") and message.usage_metadata:
                        total_tokens += message.usage_metadata.get("total_tokens", 0)
                yield f"data: {_serialize_stream_event(msg_data)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
