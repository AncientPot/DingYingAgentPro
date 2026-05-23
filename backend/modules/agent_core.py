import json
import asyncio
from typing import Annotated, AsyncIterator
from langchain_core.messages import (
    BaseMessage,
    SystemMessage,
    HumanMessage,
    AIMessageChunk,
    ToolMessage,
    AIMessage,
)
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, START, add_messages
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.config import get_config
from typing_extensions import TypedDict
import aiosqlite

from backend.modules.tool_registry import ToolRegistry
from backend.modules.llm_provider import LLMProvider


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


class AgentCore:
    def __init__(
        self, tool_registry: ToolRegistry, llm_provider: LLMProvider
    ) -> None:
        self.tool_registry = tool_registry
        self.llm_provider = llm_provider
        self.graph = None
        self.memory: AsyncSqliteSaver | None = None
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        conn = await aiosqlite.connect("checkpoints.sqlite")
        self.memory = AsyncSqliteSaver(conn)
        await self.memory.setup()
        self.graph = self._build_graph()

    def _build_graph(self):
        tool_snapshot = self.tool_registry.get_all_tools()
        self._tool_snapshot = {t.name: t for t in tool_snapshot}
        tool_node = ToolNode(tools=tool_snapshot)

        workflow = StateGraph(AgentState)
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", tool_node)
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")
        workflow.add_edge(START, "agent")
        return workflow.compile(checkpointer=self.memory)

    async def rebuild_graph(self) -> None:
        async with self._lock:
            self.graph = self._build_graph()

    def _agent_node(self, state: AgentState) -> dict:
        config = get_config()
        cfg = config.get("configurable", {})

        system_prompt = cfg.get("system_prompt", "你是一个AI助手，请尽你所能回答我的问题。")
        model_name = cfg.get("model_name", "deepseek-chat")
        temperature = float(cfg.get("temperature", 0.7))
        max_tokens_val = int(cfg.get("max_tokens", 4096))
        tool_names = cfg.get("enabled_tools", [])

        if tool_names:
            session_tools = [self._tool_snapshot[n] for n in tool_names if n in self._tool_snapshot]
        else:
            session_tools = list(self._tool_snapshot.values())
        llm = self.llm_provider.get_model(model_name, temperature, max_tokens=max_tokens_val)
        llm_with_tools = llm.bind_tools(session_tools)

        messages = [SystemMessage(content=system_prompt)] + state["messages"]
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    async def stream_chat(
        self, session_id: str, message: str, effective_config: dict
    ) -> AsyncIterator[str]:
        config = {
            "configurable": {
                "thread_id": session_id,
                **effective_config,
            }
        }
        input_state = {"messages": [HumanMessage(content=message)]}
        total_tokens = 0

        async with self._lock:
            graph = self.graph

        async for chunk in graph.astream(
            input_state, stream_mode="messages", config=config
        ):
            if isinstance(chunk, tuple) and len(chunk) >= 1:
                msg = chunk[0]

                if isinstance(msg, AIMessageChunk):
                    content = msg.content
                    if content:
                        yield f"event: content\ndata: {json.dumps({'delta': content}, ensure_ascii=False)}\n\n"
                    if hasattr(msg, "tool_call_chunks") and msg.tool_call_chunks:
                        for tc in msg.tool_call_chunks:
                            if tc.get("name"):
                                yield f"event: tool_call\ndata: {json.dumps({'tool_name': tc.get('name', ''), 'args': tc.get('args', {})}, ensure_ascii=False)}\n\n"
                    if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                        total_tokens += msg.usage_metadata.get("total_tokens", 0)

                elif isinstance(msg, ToolMessage):
                    yield f"event: tool_result\ndata: {json.dumps({'tool_name': msg.name, 'result': msg.content}, ensure_ascii=False)}\n\n"

                elif isinstance(msg, AIMessage):
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for call in msg.tool_calls:
                            yield f"event: tool_call\ndata: {json.dumps({'tool_name': call.get('name', ''), 'args': call.get('args', {})}, ensure_ascii=False)}\n\n"
                    if hasattr(msg, "usage_metadata") and msg.usage_metadata:
                        total_tokens += msg.usage_metadata.get("total_tokens", 0)

        yield f"event: done\ndata: {json.dumps({'total_tokens': total_tokens})}\n\n"
