"""网易云音乐桌面客户端控制工具（仅限 Windows 平台）。"""

import os
import time
import subprocess
from typing import Optional

from langchain_core.tools import tool


# ── Windows 平台特定导入 ──
def _import_win32_modules():
    """尝试导入 Windows 特定模块，失败则返回 None。"""
    try:
        import win32gui
        import win32process
        from pywinauto import Application
        return win32gui, win32process, Application
    except ImportError:
        return None, None, None


def get_pid_by_window_class(exe_path: str, class_name: str, wait_time: int = 7) -> int:
    """通过窗口类名获取进程 PID，若程序未运行则启动它。"""
    win32gui, win32process, _ = _import_win32_modules()
    if win32gui is None:
        raise RuntimeError("此工具仅支持 Windows 平台（缺少 pywin32/pywinauto）")

    hwnd = None

    def enum_callback(found_hwnd, extra):
        nonlocal hwnd
        if hwnd is None and win32gui.IsWindowVisible(found_hwnd) and win32gui.GetParent(found_hwnd) == 0:
            try:
                if win32gui.GetClassName(found_hwnd) == class_name:
                    hwnd = found_hwnd
                    return False
            except Exception:
                pass
        return True

    win32gui.EnumWindows(enum_callback, None)

    if not hwnd:
        if os.path.exists(exe_path):
            subprocess.Popen(exe_path)
            time.sleep(wait_time)
            win32gui.EnumWindows(enum_callback, None)
        else:
            raise FileNotFoundError(f"程序路径错误: {exe_path}")

    if not hwnd:
        raise RuntimeError("未找到目标窗口，首次启动可能需要重试。")

    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return pid
    except Exception as e:
        raise RuntimeError(f"获取PID失败: {e}")


@tool
def control_netease_cloud_music(operation: str, song_name: Optional[str] = None) -> str:
    """
    控制本地网易云音乐客户端（仅限 Windows 桌面版）。
    支持的操作有: 'play_pause', 'next', 'previous', 'search_and_play', 'like', 'unlike', 'play_liked', 'switch_mode'。
    对于 'search_and_play' 操作，必须提供 song_name 参数。

    Args:
        operation: 要执行的操作。
        song_name: 当 operation 为 'search_and_play' 时，需要搜索的歌曲名称。

    Returns:
        操作执行后的结果描述。
    """
    if os.name != "nt":
        return "网易云音乐控制工具仅支持 Windows 平台。"

    _, _, Application = _import_win32_modules()
    if Application is None:
        return "缺少必要依赖 pywin32 和 pywinauto，无法控制网易云音乐。"

    exe_path = r"D:\CloudMusic\cloudmusic.exe"
    CLASS_NAME = "OrpheusBrowserHost"

    try:
        pid = get_pid_by_window_class(exe_path, CLASS_NAME)
        app = Application(backend="uia").connect(process=pid)
        dlg = app.window(class_name=CLASS_NAME)

        if operation == "play_pause":
            dlg.wait('exists', timeout=1.0)
            play = dlg.child_window(auto_id="btn_pc_minibar_play", control_type="Button")
            play.invoke()
            return "已执行播放/暂停操作。"

        elif operation == "next":
            dlg.wait('exists', timeout=1.0)
            next_button = dlg.child_window(title="next", control_type="Button")
            next_button.invoke()
            return "已切换到下一首。"

        elif operation == "previous":
            dlg.wait('exists', timeout=1.0)
            prev_button = dlg.child_window(title="pre", control_type="Button")
            prev_button.invoke()
            return "已切换到上一首。"

        elif operation == "search_and_play":
            if not song_name:
                return "搜索并播放操作需要提供 'song_name' 参数。"
            dlg.wait('exists', timeout=1.0)
            edit = dlg.child_window(control_type="Edit", found_index=0)
            edit.type_keys("^a{BACKSPACE}" + song_name + "{ENTER}", with_spaces=True)
            time.sleep(1.5)
            dlg.wait('exists', timeout=2.0)
            play_button = dlg.child_window(title="play 播放", control_type="Button")
            play_button.invoke()
            return f"已搜索并播放歌曲: {song_name}。"

        elif operation == "like":
            dlg.wait('exists', timeout=1.0)
            like_btn = dlg.child_window(title_re=r"^like_number\s.*", control_type="Button")
            like_btn.invoke()
            return '已将当前歌曲添加到"我喜欢的音乐"。'

        elif operation == "unlike":
            dlg.wait('exists', timeout=1.0)
            not_like_btn = dlg.child_window(title_re=r"^likenumber_red\s.*", control_type="Button")
            not_like_btn.invoke()
            return '已将当前歌曲从"我喜欢的音乐"中移除。'

        elif operation == "play_liked":
            dlg.wait('exists', timeout=1.0)
            my_like = dlg.child_window(
                title="sidebar_like 我喜欢的音乐 sidebar_heartbeat",
                control_type="Group"
            )
            my_like.invoke()
            time.sleep(0.5)
            dlg.wait('exists', timeout=1.0)
            play_like = dlg.child_window(title="play 播放全部", control_type="Button")
            play_like.invoke()
            return '正在播放"我喜欢的音乐"列表。'

        elif operation == "switch_mode":
            dlg.wait('exists', timeout=1.0)
            switch_btn = dlg.child_window(
                title_re=r"^(singleloop|loop|order|shuffle|infinite|heartbeat)$",
                control_type="Button",
            )
            current_title = switch_btn.window_text()
            switch_btn.invoke()

            mode_mapping = {
                "singleloop": "单曲循环",
                "loop": "列表循环",
                "order": "顺序播放",
                "shuffle": "随机播放",
                "infinite": "无限循环",
                "heartbeat": "心动模式"
            }
            new_mode_title = switch_btn.window_text()
            new_mode = mode_mapping.get(new_mode_title, "未知模式")
            old_mode = mode_mapping.get(current_title, "未知模式")
            return f"播放模式已从 '{old_mode}' 切换为 '{new_mode}'。"

        else:
            return (
                f"不支持的操作: {operation}。"
                "支持的操作有: play_pause, next, previous, search_and_play, like, unlike, play_liked, switch_mode。"
            )

    except Exception as e:
        error_msg = str(e)
        if "未找到目标窗口" in error_msg or "首次启动" in error_msg:
            return "网易云音乐正在启动中，请稍后再试，或再次调用本工具。"
        return f"操作执行失败: {error_msg}"


def get_tool():
    """返回网易云音乐控制工具实例。"""
    return control_netease_cloud_music
