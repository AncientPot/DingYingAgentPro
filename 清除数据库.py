import sqlite3
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.constants import START
from langgraph.graph import add_messages, StateGraph

class State(TypedDict):
    messages: Annotated[list[BaseMessage],add_messages]
graph_builder = StateGraph(State)
graph_builder.add_node("node",lambda state:state)
graph_builder.add_edge(START, "node")
conn = sqlite3.connect("checkpoints.sqlite", check_same_thread=False)
memory = SqliteSaver(conn)
memory.setup()
graph = graph_builder.compile(checkpointer=memory)


memory.delete_thread('e076edda-bf70-5105-a9a9-118d7eecd0c4')
