"""
游戏工具模板 — 新建游戏工具时参考此文件。

实际游戏工具应命名为有意义的名字（不含下划线前缀），
并实现 get_meta() 和 get_tool() 两个函数。
"""

from langchain_core.tools import tool


def get_meta() -> dict:
    """返回游戏工具的元信息（用于前端展示）。"""
    return {
        "name": "_template",
        "display": "模板游戏",
        "description": "这是一个游戏工具模板，不含实际游戏内容。新建游戏工具时参考此文件。",
    }


@tool
def _template_game_action(action: str, data: str = "") -> str:
    """
    模板游戏工具。根据 action 执行不同的游戏操作。

    action: 操作类型，如 move / attack / use_item 等
    data: 操作附加数据
    """
    return f"模板游戏: {action} {data}"


def get_tool():
    """返回 LangChain 工具实例。"""
    return _template_game_action
