"""
Agent 图构建与生命周期管理。

构建 LangGraph 有状态图，支持：
- 根据运行时配置动态重建（模型参数、系统提示词、启用工具集变更时自动重建）
- 单例缓存，避免重复构建
"""

from __future__ import annotations

import logging
import threading
from typing import Annotated, Optional, Any

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from app.core.config import get_config, on_config_changed
from app.tools import load_tools

logger = logging.getLogger(__name__)

# ── 状态 ──

class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# ── 单例缓存 ──

_lock = threading.Lock()
_graph: Optional[Any] = None
_config_hash: int = 0


def _compute_config_hash(config: dict) -> int:
    """计算配置组合的哈希值，判断是否需要重建图。"""
    key_parts = (
        config.get("model_name", ""),
        config.get("temperature", 0),
        config.get("api_key", ""),
        config.get("base_url", ""),
        config.get("system_prompt", ""),
        tuple(sorted(config.get("enabled_tools", []))),
    )
    return hash(key_parts)


def _build_graph(config: dict) -> Any:
    """根据配置构建并编译图（不缓存）。"""
    # 加载启用的工具
    tool_list = load_tools(config.get("enabled_tools"))
    logger.info(f"构建图 — 模型: {config['model_name']}, 温度: {config['temperature']}, 工具数: {len(tool_list)}")

    # 创建 LLM
    llm_kwargs = {"model": config["model_name"], "temperature": config["temperature"]}
    if config.get("api_key"):
        llm_kwargs["api_key"] = config["api_key"]
    if config.get("base_url"):
        llm_kwargs["api_base"] = config["base_url"]
    llm = ChatDeepSeek(**llm_kwargs)

    system_prompt = config.get("system_prompt", "你是一个AI助手。")

    # 定义 Agent 节点
    def dingyingagent(state: State) -> dict:
        llm_with_tools = llm.bind_tools(tool_list)
        response = llm_with_tools.invoke([SystemMessage(content=system_prompt)] + state["messages"])
        return {"messages": [response]}

    # 构建图
    builder = StateGraph(State)
    builder.add_node("Agent", dingyingagent)
    builder.add_node("tools", ToolNode(tools=tool_list))
    builder.add_conditional_edges("Agent", tools_condition)
    builder.add_edge("tools", "Agent")
    builder.add_edge(START, "Agent")

    # 编译（使用内存检查点，SQLite 在 get_graph 中处理）
    memory = _get_or_create_memory()
    return builder.compile(checkpointer=memory)


# ── SQLite 检查点持久化 ──

_memory: SqliteSaver | None = None


def get_checkpointer() -> SqliteSaver:
    """获取 SQLite 检查点持久化实例（单例）。"""
    global _memory
    if _memory is None:
        import sqlite3
        conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
        _memory = SqliteSaver(conn)
        _memory.setup()
    return _memory


def _get_or_create_memory() -> SqliteSaver:
    """内部使用：获取检查点实例。"""
    return get_checkpointer()


# ── 公开接口 ──

def get_graph() -> Any:
    """
    获取当前编译好的图（单例复用，配置变更时自动重建）。
    此函数保证线程安全。
    """
    global _graph, _config_hash
    config = get_config()
    current_hash = _compute_config_hash(config)

    if _graph is None or current_hash != _config_hash:
        with _lock:
            # 双重检查
            if _graph is None or current_hash != _config_hash:
                _graph = _build_graph(config)
                _config_hash = current_hash
                logger.info("图已重建（配置变更）")

    return _graph


def invalidate_graph():
    """强制下次调用 get_graph 时重建图。"""
    global _config_hash
    with _lock:
        _config_hash = 0
        logger.info("图缓存已失效，下次请求时将重建")


# ── 注册配置变更回调 ──
on_config_changed(lambda _: invalidate_graph())
