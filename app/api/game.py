"""游戏模式接口。"""

import json
import asyncio
from queue import Queue as ThreadQueue

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage, ToolMessage

from app.agent.graph import get_graph
from app.core.config import get_config, update_config
from app.services.game_service import get_game_state, set_game_mode, set_sub_mode, get_thread_for
from app.tools.game_tools import list_game_tools, load_game_tool

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
    active = config.get("game_active_tool")
    tool_cfg = config.get("game_tool_settings", {}).get(active, {}) if active else {}
    return {
        "auto_reply_interval": config.get("game_auto_reply_interval", 0),
        "active_game_tool": active,
        "game_think_prompt": config.get("game_think_prompt", ""),
        # 当前工具的专属设置
        "tool_think_prompt": tool_cfg.get("think_prompt", ""),
        "tool_obstacle_count": tool_cfg.get("obstacle_count", 3),
    }


@router.put("/settings")
def update_game_settings(payload: dict):
    partial = {}
    if "auto_reply_interval" in payload:
        partial["game_auto_reply_interval"] = max(0, min(300, int(payload["auto_reply_interval"])))
    if "active_game_tool" in payload:
        val = payload["active_game_tool"]
        if val is None: partial["game_active_tool"] = None
        elif isinstance(val, str) and val.strip():
            available = [t["name"] for t in list_game_tools()]
            if val.strip() in available: partial["game_active_tool"] = val.strip()
    if "game_think_prompt" in payload and isinstance(payload["game_think_prompt"], str):
        partial["game_think_prompt"] = payload["game_think_prompt"].strip()
    # 工具专属设置保存到 game_tool_settings
    tool_name = payload.get("active_game_tool") or get_config().get("game_active_tool")
    if tool_name and ("tool_think_prompt" in payload or "tool_obstacle_count" in payload):
        all_tool_cfg = dict(get_config().get("game_tool_settings", {}))
        cur = dict(all_tool_cfg.get(tool_name, {}))
        if "tool_think_prompt" in payload:
            cur["think_prompt"] = str(payload["tool_think_prompt"]).strip()
        if "tool_obstacle_count" in payload:
            cur["obstacle_count"] = max(0, min(20, int(payload["tool_obstacle_count"])))
        all_tool_cfg[tool_name] = cur
        partial["game_tool_settings"] = all_tool_cfg
    if partial: update_config(partial)
    config = get_config()
    active = config.get("game_active_tool")
    tool_cfg = config.get("game_tool_settings", {}).get(active, {}) if active else {}
    return {
        "auto_reply_interval": config.get("game_auto_reply_interval", 0),
        "active_game_tool": active,
        "game_think_prompt": config.get("game_think_prompt", ""),
        "tool_think_prompt": tool_cfg.get("think_prompt", ""),
        "tool_obstacle_count": tool_cfg.get("obstacle_count", 3),
    }


@router.post("/chat")
def game_chat(payload: dict):
    """准备中子模式对话：使用 /prep 线程，与正常对话隔离。"""
    state = get_game_state()
    if not state["game_mode"]:
        raise HTTPException(400, "当前不在游戏模式")

    # 如果 prep 线程未初始化，用 base_tid 初始化
    prep_tid = get_thread_for("prep")
    if not prep_tid:
        base_tid = payload.get("base_tid", "")
        if base_tid:
            from app.services.game_service import set_game_mode as _sgm
            _sgm(True, state.get("game_type"), base_tid)
            prep_tid = get_thread_for("prep")
        if not prep_tid:
            raise HTTPException(400, "需要先设置线程（传入 base_tid 启动游戏）")

    message = payload.get("message", "")
    if not message:
        raise HTTPException(400, "需要 message 参数")

    graph = get_graph()
    if graph is None:
        raise HTTPException(503, "Agent 未就绪")

    from langchain_core.messages import HumanMessage
    config = {"configurable": {"thread_id": prep_tid}}
    input_state = {"messages": [HumanMessage(content=message)]}

    # 收集 AI 完整回复
    full_response = ""
    for r in graph.stream(input_state, stream_mode="values", config=config):
        msg = r["messages"][-1]
        if hasattr(msg, "content") and msg.content:
            full_response = msg.content

    return {"ok": True, "response": full_response}


@router.post("/start")
def start_playing(payload: dict = {}):
    """从准备中切换到游戏中，设置线程隔离。"""
    state = get_game_state()
    if not state["game_mode"]:
        raise HTTPException(400, "当前不在游戏模式")
    if state["sub_mode"] != "preparing":
        raise HTTPException(400, f"当前子模式为 {state['sub_mode']}，无法开始")
    # 设置线程隔离（前端传入当前会话的 base_tid）
    base_tid = payload.get("base_tid", "")
    if base_tid:
        from app.services.game_service import set_game_mode as _sgm
        _sgm(True, state.get("game_type"), base_tid)
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
    """AI 自主思考（仅在 playing 子模式下可用）。支持传入 game_state 上下文。"""
    state = get_game_state()
    if state["sub_mode"] != "playing":
        raise HTTPException(400, "仅在游戏中子模式下可用")

    # 使用 playing 专用线程（与正常对话隔离）
    play_tid = get_thread_for("play")
    if not play_tid:
        raise HTTPException(400, "需要先启动游戏")
    config = {"configurable": {"thread_id": play_tid}}
    graph = get_graph()
    if graph is None:
        raise HTTPException(503, "Agent 未就绪")

    # 构建游戏自主思考提示词
    context = request.get("context", "")
    if context:
        full_prompt = (
            f"[游戏自主推进]\n"
            f"你正在与用户进行互动游戏。以下是当前游戏的实时状态数据。\n"
            f"请根据这些数据决定是否调用游戏工具（如生成食物、障碍物等）。\n"
            f"工具的具体用法见各工具的函数说明。保持回复简短，直接行动。\n\n"
            f"当前游戏状态:\n{context}"
        )
    else:
        full_prompt = "[游戏自主推进] 请根据当前游戏状态自主推进游戏进程。"

    input_state = {"messages": [HumanMessage(content=full_prompt)]}

    # 动态加载活跃游戏工具（如果存在）
    active_tool = get_config().get("game_active_tool")
    game_tool = None
    if active_tool:
        game_tool = load_game_tool(active_tool)

    async def event_generator():
        sync_queue: ThreadQueue = ThreadQueue()

        def run_stream():
            try:
                if game_tool:
                    from app.tools import load_tools
                    from langchain_deepseek import ChatDeepSeek
                    gcfg = get_config()
                    llm = ChatDeepSeek(model=gcfg.get("model_name", "deepseek-chat"), temperature=gcfg.get("temperature", 0.7))
                    if gcfg.get("api_key"): llm.api_key = gcfg["api_key"]
                    if gcfg.get("base_url"): llm.api_base = gcfg["base_url"]
                    all_tools = load_tools(gcfg.get("enabled_tools")) + [game_tool]
                    llm_with_tools = llm.bind_tools(all_tools)

                    # 构建消息
                    from app.agent.graph import get_checkpointer
                    memory = get_checkpointer()
                    tup = memory.get_tuple(config)
                    history = list(tup.checkpoint["channel_values"]["messages"]) if tup else []
                    gcfg = get_config()
                    # 优先用工具专属提示词，否则用全局游戏提示词
                    active_tool_now = gcfg.get("game_active_tool")
                    tool_cfg = gcfg.get("game_tool_settings", {}).get(active_tool_now, {}) if active_tool_now else {}
                    game_prompt = tool_cfg.get("think_prompt") or gcfg.get("game_think_prompt", "根据游戏状态决策。")
                    system = SystemMessage(content=game_prompt)
                    msgs = [system] + history[-6:] + input_state["messages"]  # 仅保留最近6条历史

                    # LLM 调用 → 可能返回 tool_calls（思考过程不发送到前端）
                    response = llm_with_tools.invoke(msgs)

                    # 执行工具调用（仅发送 tool 事件和最终回复）
                    tool_calls = getattr(response, 'tool_calls', None) or []
                    if tool_calls:
                        msgs.append(response)  # 循环外只追加一次
                    for tc in tool_calls:
                        tc_name = tc.get('name', '')
                        tc_args = tc.get('args', {})
                        tc_id = tc.get('id', '')
                        tool_obj = None
                        for t in all_tools:
                            if getattr(t, 'name', '') == tc_name:
                                tool_obj = t
                                break
                        if tool_obj:
                            try:
                                result = tool_obj.invoke(tc_args)
                                sync_queue.put(("tool", {"name": tc_name, "id": tc_id, "content": str(result)}))
                                from langchain_core.messages import ToolMessage
                                msgs.append(ToolMessage(content=str(result), tool_call_id=tc_id))
                            except Exception as e:
                                sync_queue.put(("tool", {"name": tc_name, "id": tc_id, "content": f"ERROR:{e}"}))
                        else:
                            sync_queue.put(("error", f"工具 '{tc_name}' 未找到"))

                    # 所有工具执行完后，让 LLM 统一回应
                    if tool_calls:
                        final = llm.invoke(msgs)
                        if final.content:
                            sync_queue.put(("chunk", final.content))
                else:
                    for event in graph.stream(input_state, stream_mode="messages", config=config):
                        message = event[0]
                        if hasattr(message, 'content') and message.content:
                            sync_queue.put(("chunk", message.content))
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
            elif msg_type == "chunk":
                yield f"data: {json.dumps({'type': 'chunk', 'content': msg_data})}\n\n"
            elif msg_type == "tool":
                yield f"data: {json.dumps({'type': 'tool', 'tool_name': msg_data['name'], 'tool_call_id': msg_data['id'], 'content': msg_data['content']})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/gameover")
def game_over(payload: dict):
    """游戏结束：将总结发送到准备中对话，切换到准备中子模式。"""
    state = get_game_state()
    if state["sub_mode"] != "playing":
        raise HTTPException(400, "仅在游戏中子模式下可用")

    summary = payload.get("summary", "游戏已结束。")
    prep_tid = get_thread_for("prep")
    if prep_tid:
        from app.agent.graph import get_graph
        graph = get_graph()
        if graph:
            config = {"configurable": {"thread_id": prep_tid}}
            for _ in graph.stream(
                {"messages": [HumanMessage(content=f"[游戏结束总结]\n{summary}")]},
                stream_mode="values", config=config
            ):
                pass  # 消费生成器以执行图运行

    set_sub_mode("preparing")
    return {"ok": True, "message": "已切换到准备中子模式", "sub_mode": "preparing"}


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
