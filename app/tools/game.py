"""游戏中心工具 —— 进入/退出游戏模式。"""

from langchain_core.tools import tool

from app.services.game_service import get_game_state, set_game_mode


@tool
def game_center(action: str) -> str:
    """
    游戏中心。当用户明确表示想要玩游戏、开始游戏、进入游戏时调用此工具。

    action 参数:
    - 'start': 进入游戏模式。前端界面将切换到游戏视图。
    - 'stop': 退出游戏模式，返回正常对话界面。

    调用此工具后，告知用户游戏模式已切换即可，无需多言。
    """
    if action == "start":
        set_game_mode(True)
        return (
            "GAME_MODE_ACTIVE\n游戏模式已启动！界面已切换到游戏视图。\n"
            "你现在可以和用户讨论游戏内容、规则，或者直接开始游戏。"
        )
    elif action == "stop":
        set_game_mode(False)
        return "GAME_MODE_INACTIVE\n游戏模式已退出，界面已恢复为正常对话模式。"
    else:
        return f"不支持的游戏操作: {action}。支持: start / stop"


def get_tool():
    """返回 game_center 工具实例。"""
    return game_center


def test_tool() -> dict:
    """自检：验证状态切换。"""
    try:
        set_game_mode(True, "test")
        state = get_game_state()
        assert state["game_mode"] is True
        set_game_mode(False)
        assert get_game_state()["game_mode"] is False
        return {"ok": True, "message": "游戏中心工具正常（状态切换测试通过）", "details": ""}
    except Exception as e:
        return {"ok": False, "message": f"自检失败: {e}", "details": str(e)}
