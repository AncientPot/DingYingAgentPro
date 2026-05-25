"""
游戏工具加载器 — 扫描 game_tools/ 目录，发现可用的游戏工具。

每个游戏工具模块需暴露:
  get_tool() -> BaseTool  返回 LangChain 工具实例
  get_meta() -> dict      返回 {"name": str, "display": str, "description": str}
"""

import importlib
import logging
import os
import pkgutil
from typing import Optional

logger = logging.getLogger(__name__)
_package_dir = os.path.dirname(__file__)


def _discover_modules() -> list[str]:
    modules = []
    for info in pkgutil.iter_modules([_package_dir]):
        if not info.name.startswith("_"):
            modules.append(info.name)
    return sorted(modules)


def list_game_tools() -> list[dict]:
    """列出所有可用的游戏工具元信息。"""
    result = []
    for name in _discover_modules():
        try:
            mod = importlib.import_module(f"app.tools.game_tools.{name}")
            if hasattr(mod, "get_meta"):
                meta = mod.get_meta()
            else:
                tool = mod.get_tool()
                meta = {
                    "name": name,
                    "display": getattr(tool, "name", name),
                    "description": getattr(tool, "description", ""),
                }
            result.append(meta)
        except Exception as e:
            logger.warning(f"加载游戏工具 {name} 失败: {e}")
    return result


def load_game_tool(name: str):
    """加载指定的游戏工具，返回 BaseTool 实例或 None。"""
    try:
        mod = importlib.import_module(f"app.tools.game_tools.{name}")
        return mod.get_tool()
    except Exception as e:
        logger.warning(f"加载游戏工具 {name} 失败: {e}")
        return None
