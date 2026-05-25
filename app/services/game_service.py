"""游戏模式状态管理。"""

_game_mode: bool = False
_game_type: str | None = None
_sub_mode: str = "preparing"  # preparing | playing


def set_game_mode(active: bool, game_type: str | None = None):
    global _game_mode, _game_type, _sub_mode
    _game_mode = active
    _game_type = game_type if active else None
    _sub_mode = "preparing"  # 每次进入游戏模式从"准备中"开始


def set_sub_mode(mode: str):
    """切换子模式: preparing / playing"""
    global _sub_mode
    if mode in ("preparing", "playing"):
        _sub_mode = mode


def get_game_state() -> dict:
    return {
        "game_mode": _game_mode,
        "game_type": _game_type or "default",
        "sub_mode": _sub_mode,
    }
