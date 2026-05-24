"""
工具管理服务。

负责：
- 列出所有可用工具及其启用状态
- 启用/禁用指定工具（修改配置中的 enabled_tools 列表）
"""

from app.core.config import get_config, update_config
from app.tools import list_available_tools


def get_tools_status() -> list[dict]:
    """获取所有可用工具及其当前启用状态。"""
    enabled = get_config().get("enabled_tools", [])
    return list_available_tools(enabled)


def set_tool_enabled(tool_name: str, enabled: bool) -> bool:
    """
    启用或禁用指定工具。

    Args:
        tool_name: 工具模块文件名（不含 .py）。
        enabled: True 启用，False 禁用。

    Returns:
        bool: 操作是否成功。
    """
    config = get_config()
    enabled_tools = config.get("enabled_tools", [])

    # 先校验工具是否存在
    all_tools = list_available_tools()
    all_names = [t["name"] for t in all_tools]
    if tool_name not in all_names:
        return False

    if enabled:
        if tool_name not in enabled_tools:
            enabled_tools.append(tool_name)
    else:
        if tool_name in enabled_tools:
            enabled_tools.remove(tool_name)

    update_config({"enabled_tools": enabled_tools})
    return True
