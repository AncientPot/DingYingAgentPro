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


class UIElementError(RuntimeError):
    """UI 控件操作失败异常，用于精确异常匹配，避免字符串耦合。"""
    pass


def _safe_invoke(element, desc, retries=2):
    """安全调用 UI 元素的 invoke()，失败时重试并给出友好错误。"""
    last_error = None
    for attempt in range(retries + 1):
        try:
            element.wait('enabled', timeout=0.5)
            element.invoke()
            return
        except Exception as e:
            last_error = e
            if attempt < retries:
                time.sleep(0.3)
    raise UIElementError(f"无法操作{desc}（重试{retries}次后仍失败）")


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

        # 尝试将窗口置于前台以确保控件可交互
        try:
            if hasattr(dlg, 'set_focus'):
                dlg.set_focus()
        except Exception:
            pass

        if operation == "play_pause":
            dlg.wait('exists', timeout=1.0)
            play = dlg.child_window(auto_id="btn_pc_minibar_play", control_type="Button")
            _safe_invoke(play, "播放/暂停按钮")
            return "已执行播放/暂停操作。"

        elif operation == "next":
            dlg.wait('exists', timeout=1.0)
            next_button = dlg.child_window(title="next", control_type="Button")
            _safe_invoke(next_button, "下一首按钮")
            return "已切换到下一首。"

        elif operation == "previous":
            dlg.wait('exists', timeout=1.0)
            prev_button = dlg.child_window(title="pre", control_type="Button")
            _safe_invoke(prev_button, "上一首按钮")
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
            _safe_invoke(play_button, "播放按钮")
            return f"已搜索并播放歌曲: {song_name}。"

        elif operation == "like":
            dlg.wait('exists', timeout=1.0)
            like_btn = dlg.child_window(title_re=r"^like_number\s.*", control_type="Button")
            _safe_invoke(like_btn, "喜欢按钮")
            return '已将当前歌曲添加到"我喜欢的音乐"。'

        elif operation == "unlike":
            dlg.wait('exists', timeout=1.0)
            not_like_btn = dlg.child_window(title_re=r"^likenumber_red\s.*", control_type="Button")
            _safe_invoke(not_like_btn, "取消喜欢按钮")
            return '已将当前歌曲从"我喜欢的音乐"中移除。'

        elif operation == "play_liked":
            dlg.wait('exists', timeout=1.0)
            my_like = dlg.child_window(
                title="sidebar_like 我喜欢的音乐 sidebar_heartbeat",
                control_type="Group"
            )
            _safe_invoke(my_like, "我喜欢的音乐入口")
            time.sleep(0.5)
            dlg.wait('exists', timeout=1.0)
            play_like = dlg.child_window(title="play 播放全部", control_type="Button")
            _safe_invoke(play_like, "播放全部按钮")
            return '正在播放"我喜欢的音乐"列表。'

        elif operation == "switch_mode":
            dlg.wait('exists', timeout=1.0)
            switch_btn = dlg.child_window(
                title_re=r"^(singleloop|loop|order|shuffle|infinite|heartbeat)$",
                control_type="Button",
            )
            current_title = switch_btn.window_text()
            _safe_invoke(switch_btn, "播放模式切换按钮")

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

    except UIElementError as e:
        return f"操作失败，网易云音乐窗口可能处于不可交互状态: {e}"
    except RuntimeError as e:
        error_msg = str(e)
        if "未找到目标窗口" in error_msg or "首次启动" in error_msg:
            return "网易云音乐正在启动中，请稍后再试，或再次调用本工具。"
        return f"操作执行失败: {error_msg}"
    except FileNotFoundError as e:
        return f"未找到网易云音乐程序: {e}"
    except Exception as e:
        error_msg = str(e)
        # 过滤 pywinauto 内部对象信息，只保留有意义的错误
        if error_msg.startswith("{") and "control_type" in error_msg:
            return "网易云音乐控件未能正常响应，请确认客户端窗口处于活跃状态后重试。"
        if "未找到目标窗口" in error_msg or "首次启动" in error_msg:
            return "网易云音乐正在启动中，请稍后再试，或再次调用本工具。"
        return f"操作执行失败: {error_msg}"


def get_tool():
    """返回网易云音乐控制工具实例。"""
    return control_netease_cloud_music


def test_tool() -> dict:
    """自检：验证可执行文件是否存在、窗口能否定位。"""
    if os.name != "nt":
        return {"ok": False, "message": "网易云音乐控制仅支持 Windows 平台", "details": f"当前平台: {os.name}"}

    exe_path = r"D:\CloudMusic\cloudmusic.exe"
    CLASS_NAME = "OrpheusBrowserHost"

    if not os.path.exists(exe_path):
        return {
            "ok": False,
            "message": f"未找到网易云音乐程序: {exe_path}",
            "details": "请确认网易云音乐已安装，或修改工具代码中的 exe_path",
        }

    # 检查是否已运行
    try:
        import win32gui
        import win32process

        hwnd = None

        def _callback(found_hwnd, _extra):
            nonlocal hwnd
            if hwnd is None and win32gui.IsWindowVisible(found_hwnd) and win32gui.GetParent(found_hwnd) == 0:
                try:
                    if win32gui.GetClassName(found_hwnd) == CLASS_NAME:
                        hwnd = found_hwnd
                        return False
                except Exception:
                    pass
            return True

        win32gui.EnumWindows(_callback, None)

        if hwnd is None:
            return {
                "ok": True,
                "message": "网易云音乐程序存在但未运行（调用时会自动启动）",
                "details": f"程序路径: {exe_path}",
            }

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return {
            "ok": True,
            "message": f"网易云音乐正在运行（PID: {pid}），窗口可定位",
            "details": f"程序路径: {exe_path}, PID: {pid}, Class: {CLASS_NAME}",
        }
    except ImportError:
        return {"ok": False, "message": "缺少 pywin32 依赖", "details": "请安装: pip install pywin32"}
    except Exception as e:
        return {"ok": False, "message": f"检测失败: {e}", "details": str(e)}
