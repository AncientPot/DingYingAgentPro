"""游戏模式接口。"""

import json
import asyncio
from queue import Queue as ThreadQueue

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage

from app.agent.graph import get_graph
from app.core.config import get_config, update_config
from app.services.game_service import get_game_state, set_game_mode, set_sub_mode
from app.tools.game_tools import list_game_tools

router = APIRouter(prefix="/api/game", tags=["game"])


@router.get("/tools")
def game_tools_list():
    """列出所有可用的游戏工具。"""
    return {"tools": list_game_tools()}


@router.get("/state")
def game_state():
    return get_game_state()


@router.get("/settings")
def game_settings():
    config = get_config()
    return {
        "auto_reply_interval": config.get("game_auto_reply_interval", 0),
        "think_prompt": config.get("game_think_prompt", ""),
        "active_game_tool": config.get("game_active_tool"),
    }


@router.put("/settings")
def update_game_settings(payload: dict):
    partial = {}
    if "auto_reply_interval" in payload:
        partial["game_auto_reply_interval"] = max(0, min(300, int(payload["auto_reply_interval"])))
    if "think_prompt" in payload and isinstance(payload["think_prompt"], str):
        partial["game_think_prompt"] = payload["think_prompt"].strip()
    if "active_game_tool" in payload:
        val = payload["active_game_tool"]
        if val is None:
            partial["game_active_tool"] = None
        elif isinstance(val, str) and val.strip():
            available = [t["name"] for t in list_game_tools()]
            if val.strip() in available:
                partial["game_active_tool"] = val.strip()
    if partial:
        update_config(partial)
    config = get_config()
    return {
        "auto_reply_interval": config.get("game_auto_reply_interval", 0),
        "think_prompt": config.get("game_think_prompt", ""),
        "active_game_tool": config.get("game_active_tool"),
    }


@router.post("/start")
def start_playing():
    """从准备中切换到游戏中，AI 自主回复开始生效。"""
    state = get_game_state()
    if not state["game_mode"]:
        raise HTTPException(400, "当前不在游戏模式")
    if state["sub_mode"] != "preparing":
        raise HTTPException(400, f"当前子模式为 {state['sub_mode']}，无法开始")
    set_sub_mode("playing")
    return get_game_state()


@router.post("/stop")
def stop_playing():
    """从游戏中切换回准备中，AI 自主回复停止。"""
    state = get_game_state()
    if state["sub_mode"] != "playing":
        raise HTTPException(400, f"当前子模式为 {state['sub_mode']}，无法停止")
    set_sub_mode("preparing")
    return get_game_state()


@router.post("/think")
def game_think(request: dict):
    """AI 自主思考（仅在 playing 子模式下可用）。"""
    state = get_game_state()
    if state["sub_mode"] != "playing":
        raise HTTPException(400, "仅在游戏中子模式下可用")

    thread_id = request.get("thread_id", "")
    if not thread_id:
        raise HTTPException(400, "需要 thread_id")

    config = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()
    if graph is None:
        raise HTTPException(503, "Agent 未就绪")

    app_config = get_config()
    think_prompt = app_config.get("game_think_prompt", "请根据当前游戏状态自主推进游戏进程。")
    input_state = {"messages": [HumanMessage(content=f"[游戏自主推进] {think_prompt}")]}

    async def event_generator():
        sync_queue: ThreadQueue = ThreadQueue()

        def run_stream():
            try:
                for event in graph.stream(input_state, stream_mode="messages", config=config):
                    sync_queue.put(("data", event))
            except Exception as exc:
                sync_queue.put(("error", str(exc)))
            finally:
                sync_queue.put(("done", None))

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, run_stream)

        while True:
            msg_type, msg_data = await loop.run_in_executor(None, sync_queue.get)
            if msg_type == "done":
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                break
            elif msg_type == "error":
                yield f"data: {json.dumps({'type': 'error', 'content': msg_data})}\n\n"
                break
            else:
                message = msg_data[0]
                if isinstance(message, AIMessageChunk):
                    yield f"data: {json.dumps({'type': 'chunk', 'content': message.content or ''})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/exit")
def exit_game():
    """退出游戏模式（仅在准备中子模式下允许）。"""
    state = get_game_state()
    if not state["game_mode"]:
        return {"ok": True, "message": "已不在游戏模式"}
    if state["sub_mode"] == "playing":
        # 如果在游戏中，先切回准备中
        set_sub_mode("preparing")
    set_game_mode(False)
    return {"ok": True, "message": "游戏模式已退出"}
