"""
Agent 图构建与生命周期管理。

构建 LangGraph 有状态图，支持：
- 根据运行时配置动态重建（模型参数、系统提示词、启用工具集变更时自动重建）
- 单例缓存，避免重复构建
- 使用版本计数器替代内容哈希，消除碰撞风险
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


# ── 版本式缓存（替代哈希） ──

_lock = threading.Lock()
_graph: Optional[Any] = None

# 单调递增的配置版本号，每次 invalidate 自增。
# 初始值 0 表示"从未构建"，1 表示"至少构建过一次"。
_config_epoch: int = 0   # 最近一次 invalidate 写入的版本
_graph_epoch: int = 0    # 最近一次 build 使用的版本


def _build_graph() -> Any:
    """根据当前配置构建并编译图（调用方需持有 _lock）。"""
    # 重新读取最新配置（不从参数传入，确保闭包捕获最新值）
    config = get_config()

    tool_list = load_tools(config.get("enabled_tools"))
    model_name = config.get("model_name", "deepseek-chat")
    temperature = config.get("temperature", 0.7)
    system_prompt = config.get("system_prompt", "你是一个AI助手，请尽你所能回答我的问题。")

    logger.info(
        "构建图 — 模型: %s, 温度: %s, 工具数: %d, 系统提示词: %s",
        model_name, temperature, len(tool_list), system_prompt[:40]
    )

    # 创建 LLM
    llm_kwargs = {"model": model_name, "temperature": temperature}
    if config.get("api_key"):
        llm_kwargs["api_key"] = config["api_key"]
    if config.get("base_url"):
        llm_kwargs["api_base"] = config["base_url"]
    llm = ChatDeepSeek(**llm_kwargs)

    # 定义 Agent 节点 —— system_prompt 通过闭包捕获
    def dingyingagent(state: State) -> dict:
        llm_with_tools = llm.bind_tools(tool_list)
        response = llm_with_tools.invoke(
            [SystemMessage(content=system_prompt)] + state["messages"]
        )
        return {"messages": [response]}

    # 构建图
    builder = StateGraph(State)
    builder.add_node("Agent", dingyingagent)
    builder.add_node("tools", ToolNode(tools=tool_list))
    builder.add_conditional_edges("Agent", tools_condition)
    builder.add_edge("tools", "Agent")
    builder.add_edge(START, "Agent")

    memory = _get_or_create_memory()
    return builder.compile(checkpointer=memory)


# ── SQLite 检查点持久化 ──

_memory: Optional[SqliteSaver] = None


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
    return get_checkpointer()


# ── 公开接口 ──

def get_graph() -> Any:
    """
    获取当前编译好的图（单例复用，配置变更时自动重建）。

    注：快速路径存在 TOCTOU 窗口——在比较 epoch 和 return 之间其他线程
    可能 invalidate 图缓存。此窗口仅影响单次请求（下次请求自愈），单用户
    场景下几乎不可触发。若需严格一致性，将 epoch 比较移入锁内即可。
    """
    global _graph, _graph_epoch, _config_epoch

    # 快速路径：无锁检查（有极低概率的 TOCTOU 窗口）
    if _graph is not None and _graph_epoch == _config_epoch:
        return _graph

    with _lock:
        if _graph is None or _graph_epoch != _config_epoch:
            logger.info("重建 Agent 图（epoch %d → %d）", _graph_epoch, _config_epoch)
            _graph = _build_graph()
            _graph_epoch = _config_epoch

    return _graph


def invalidate_graph():
    """强制下次调用 get_graph 时重建图。配置变更后自动调用。"""
    global _graph, _config_epoch
    with _lock:
        _config_epoch += 1
        # 同时置空 _graph 以缩窄 TOCTOU 窗口
        _graph = None
        logger.info("图缓存已失效（epoch ← %d）", _config_epoch)


# ── 注册配置变更回调 ──
on_config_changed(lambda _: invalidate_graph())
