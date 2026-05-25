"""
贪吃蛇游戏工具 — AI 可调用以生成食物和障碍物。

两个操作:
- generate_food: 在指定坐标生成食物
- generate_obstacle: 在指定坐标生成障碍物
"""

from langchain_core.tools import tool


@tool
def snake_game(action: str, x: int = 0, y: int = 0) -> str:
    """
    贪吃蛇游戏控制。在 40x40 网格放置食物/障碍物。

    规则：食物:无时必须生成。蛇前进方向 3-5 格放食物。坐标确保不在蛇身上。每次只生成一个。

    action: 'generate_food' 或 'generate_obstacle'
    x,y: 0-39 坐标

    回复必须精简：只说明放了什么在哪个坐标，5字以内。示例："食物(25,20)"
    """
    if action == "generate_food":
        return f"FOOD:{x},{y}"
    elif action == "generate_obstacle":
        return f"OBSTACLE:{x},{y}"
    else:
        return f"ERROR: unknown action '{action}'"


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
        r1 = snake_game.invoke({"action": "generate_food", "x": 5, "y": 5})
        assert "FOOD:5,5" in r1, f"unexpected: {r1}"
        r2 = snake_game.invoke({"action": "generate_obstacle", "x": 10, "y": 10})
        assert "OBSTACLE:10,10" in r2, f"unexpected: {r2}"
        return {"ok": True, "message": "贪吃蛇工具正常", "details": ""}
    except Exception as e:
        return {"ok": False, "message": str(e), "details": ""}
