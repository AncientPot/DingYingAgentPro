"""
工具自动发现与加载器。

扫描 tools/ 目录下所有 .py 文件（排除 __init__.py），每新增一个 .py 文件
即新增一个工具，删除 .py 文件即移除工具。每个工具模块需暴露：

    def get_tool() -> BaseTool:
        ...

导入失败的模块（如缺少平台依赖）会被自动跳过并记录警告。
"""

import importlib
import logging
import os
import pkgutil
from typing import Optional

logger = logging.getLogger(__name__)

_package_dir = os.path.dirname(__file__)


def _discover_modules():
    """发现 tools/ 目录下所有可导入的工具模块名。"""
    modules = []
    for module_info in pkgutil.iter_modules([_package_dir]):
        if module_info.name.startswith("_"):
            continue
        modules.append(module_info.name)
    return sorted(modules)


def load_tools(enabled_tools: Optional[list[str]] = None):
    """
    加载并返回工具列表。

    Args:
        enabled_tools: 启用的工具模块名列表，None 表示加载全部可用工具。

    Returns:
        list[BaseTool]: 成功加载的 LangChain 工具对象列表。
    """
    available = _discover_modules()
    tools = []

    for module_name in available:
        if enabled_tools is not None and module_name not in enabled_tools:
            continue
        try:
            module = importlib.import_module(f"app.tools.{module_name}")
            if hasattr(module, "get_tool"):
                tool = module.get_tool()
                tools.append(tool)
                logger.info(f"已加载工具: {module_name}")
            else:
                logger.warning(f"工具模块 {module_name} 缺少 get_tool() 函数，已跳过")
        except Exception as e:
            logger.warning(f"加载工具 {module_name} 失败: {e}")

    return tools


def test_tool(module_name: str) -> dict:
    """
    测试指定工具是否可用。

    Returns:
        dict: {"ok": bool, "message": str, "details": str}
    """
    available = _discover_modules()
    if module_name not in available:
        return {"ok": False, "message": f"工具 '{module_name}' 不存在", "details": ""}

    try:
        module = importlib.import_module(f"app.tools.{module_name}")
    except Exception as e:
        return {"ok": False, "message": f"导入失败: {e}", "details": str(e)}

    # 如果工具模块提供了 test_tool 函数，优先使用
    if hasattr(module, "test_tool"):
        try:
            return module.test_tool()
        except Exception as e:
            return {"ok": False, "message": f"工具自检失败: {e}", "details": str(e)}

    # 否则只验证 get_tool() 能否正常调用
    if not hasattr(module, "get_tool"):
        return {"ok": False, "message": "工具模块缺少 get_tool() 函数", "details": ""}

    try:
        tool = module.get_tool()
        return {
            "ok": True,
            "message": f"工具 '{getattr(tool, 'name', module_name)}' 加载正常",
            "details": getattr(tool, "description", ""),
        }
    except Exception as e:
        return {"ok": False, "message": f"工具实例化失败: {e}", "details": str(e)}


def list_available_tools(enabled_tools: Optional[list[str]] = None) -> list[dict]:
    """
    列出所有可用工具及其元信息。

    Returns:
        list[dict]: 每个工具包含 name, display_name, description, enabled 字段。
    """
    available = _discover_modules()
    enabled_set = set(enabled_tools) if enabled_tools is not None else set(available)
    result = []

    for module_name in available:
        try:
            module = importlib.import_module(f"app.tools.{module_name}")
            tool = module.get_tool()
            result.append({
                "name": module_name,
                "display_name": getattr(tool, "name", module_name),
                "description": getattr(tool, "description", ""),
                "enabled": module_name in enabled_set,
            })
        except Exception as e:
            logger.warning(f"读取工具 {module_name} 元信息失败: {e}")
            result.append({
                "name": module_name,
                "display_name": module_name,
                "description": f"加载失败: {e}",
                "enabled": False,
            })

    return result
