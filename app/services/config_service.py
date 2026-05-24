"""
配置服务。

对 core/config.py 的业务层封装，提供：
- 脱敏后的配置读取（用于 API 返回）
- 部分更新校验
- 配置项的说明文案
"""

from app.core.config import get_config, get_masked_config, update_config

# 配置项说明（用于前端设置页面展示）
CONFIG_DESCRIPTIONS = {
    "model_name": "模型名称",
    "temperature": "模型温度（0-2），越高越随机",
    "api_key": "DeepSeek API 密钥",
    "base_url": "API 基础地址（留空使用默认）",
    "system_prompt": "系统提示词，定义 AI 助手的行为风格",
    "max_search_results": "联网搜索返回最大结果数",
    "enabled_tools": "启用的工具列表",
}


def get_settings() -> list[dict]:
    """获取所有可配置项及其当前值（敏感字段已脱敏，保留原生类型）。"""
    config = get_masked_config()
    result = []
    for key in CONFIG_DESCRIPTIONS:
        raw = config.get(key, "")
        # 保留原生类型（list 不转 str），仅对前端展示不友好的类型做转换
        result.append({
            "key": key,
            "value": raw,
            "description": CONFIG_DESCRIPTIONS.get(key, ""),
        })
    return result


def update_settings(partial: dict) -> dict:
    """
    更新配置。会自动过滤掉未知的键和 None 值。

    Returns:
        dict: 更新后的完整配置（脱敏版）。
    """
    allowed_keys = set(CONFIG_DESCRIPTIONS.keys())
    filtered = {k: v for k, v in partial.items() if k in allowed_keys and v is not None}
    if filtered:
        update_config(filtered)
    return get_masked_config()
