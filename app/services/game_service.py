"""游戏模式状态管理。"""

_game_mode: bool = False
_game_type: str | None = None
_sub_mode: str = "preparing"

# 线程隔离：三个 conversation 上下文
_base_tid: str = ""           # 对话模式 thread_id
_prep_tid: str = ""           # 准备中 thread_id（= base_tid + "/prep"）
_play_tid: str = ""           # 游戏中 thread_id（= base_tid + "/play"）


def set_game_mode(active: bool, game_type: str | None = None, base_tid: str = ""):
    global _game_mode, _game_type, _sub_mode, _base_tid, _prep_tid, _play_tid
    _game_mode = active
    _game_type = game_type if active else None
    _sub_mode = "preparing"
    if active and base_tid:
        _base_tid = base_tid
        _prep_tid = base_tid + "/prep"
        _play_tid = base_tid + "/play"
    else:
        _base_tid = ""
        _prep_tid = ""
        _play_tid = ""


def set_sub_mode(mode: str):
    global _sub_mode
    if mode in ("preparing", "playing"):
        _sub_mode = mode


def get_thread_for(mode: str) -> str:
    """获取指定模式的 thread_id。"""
    if mode == "prep":
        return _prep_tid
    elif mode == "play":
        return _play_tid
    return _base_tid


def get_game_state() -> dict:
    return {
        "game_mode": _game_mode,
        "game_type": _game_type or "default",
        "sub_mode": _sub_mode,
    }
