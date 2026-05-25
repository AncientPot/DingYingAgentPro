"""
贪吃蛇游戏工具 — AI 可调用以批量生成食物和障碍物。

一次调用可放置多个物品（食物+障碍物），无需多次调用。
"""

from langchain_core.tools import tool


@tool
def snake_game(items: list[str] = []) -> str:
    """
    贪吃蛇游戏控制。在 40x40 网格放置食物和障碍物，一次可放置多个。

    items: 放置项列表。每项格式为 "类型:x,y"
      - FOOD:x,y  — 在坐标 (x,y) 生成食物（x,y 为 0-39 整数）
      - OBSTACLE:x,y — 在坐标 (x,y) 生成障碍物
      例: ["FOOD:15,10", "OBSTACLE:5,5", "FOOD:30,20", "OBSTACLE:20,15"]

    规则：
    - 可同时放置多个食物和多个障碍物，分布在网格各处
    - 坐标避开蛇身和已有物品
    - 一次调用放置所有需要的物品，无需多次调用

    回复≤10字，直接说放了什么。
    """
    results = []
    for item in (items or []):
        item = str(item).strip()
        if item.startswith("FOOD:") or item.startswith("OBSTACLE:"):
            results.append(item)
    return "\n".join(results) if results else "OK"


def get_meta() -> dict:
    return {
        "name": "snake_game",
        "display": "贪吃蛇",
        "description": "经典贪吃蛇游戏。AI 可在网格中放置食物和障碍物，玩家操控蛇吃掉食物并避开障碍物。",
    }


def get_tool():
    return snake_game


def test_tool() -> dict:
    try:
        r1 = snake_game.invoke({"items": ["FOOD:5,5", "OBSTACLE:10,10"]})
        assert "FOOD:5,5" in r1, f"unexpected: {r1}"
        assert "OBSTACLE:10,10" in r1, f"unexpected: {r1}"
        # 测试空列表
        r2 = snake_game.invoke({"items": []})
        assert r2 == "OK", f"expected OK, got: {r2}"
        return {"ok": True, "message": "贪吃蛇工具正常（批量放置通过）", "details": ""}
    except Exception as e:
        return {"ok": False, "message": str(e), "details": ""}
