"""
运行时配置管理。

配置加载优先级: config.json > 环境变量 > 内置默认值
通过 API 修改配置后会自动持久化到 config.json，并通知 Agent 图层重建。
"""

import json
import os
import threading
from pathlib import Path
from typing import Optional

CONFIG_FILE = Path(__file__).parent.parent.parent / "config.json"

# 配置变更回调列表，图重建函数会注册到这里
_on_config_changed: list = []

_DEFAULT_CONFIG = {
    "model_name": "deepseek-chat",
    "temperature": 0.7,
    "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
    "base_url": os.getenv("DEEPSEEK_BASE_URL", ""),
    "system_prompt": "你是一个AI助手，请尽你所能回答我的问题。",
    "max_search_results": 2,
    "enabled_tools": ["calculator", "netease_cloud_music", "tavily_search"],
}

_lock = threading.Lock()
_config_cache: Optional[dict] = None


def _load_from_file() -> dict:
    """从 config.json 读取配置，文件不存在则返回空字典。"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def get_config() -> dict:
    """获取当前完整配置（合并默认值、环境变量和文件覆盖）。"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    with _lock:
        if _config_cache is not None:
            return _config_cache
        config = dict(_DEFAULT_CONFIG)
        file_overrides = _load_from_file()
        config.update(file_overrides)
        _config_cache = config
        return _config_cache


def update_config(partial: dict) -> dict:
    """部分更新配置，写入文件并触发图重建。"""
    global _config_cache
    with _lock:
        current = get_config()
        current.update(partial)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        _config_cache = None  # 使缓存失效
        new_config = dict(current)

    # 通知所有注册的变更回调
    for callback in _on_config_changed:
        callback(new_config)

    return new_config


def on_config_changed(callback):
    """注册配置变更回调。图重建函数应调用此方法注册自身。"""
    _on_config_changed.append(callback)


def get_masked_config() -> dict:
    """获取脱敏后的配置（隐藏 API Key 中间部分），用于 API 返回。"""
    config = get_config()
    masked = dict(config)
    for key in ("api_key",):
        val = masked.get(key, "")
        if isinstance(val, str) and len(val) > 8:
            masked[key] = val[:4] + "*" * (len(val) - 8) + val[-4:]
    return masked


def reset_cache():
    """强制使缓存失效，下次调用 get_config 会重新加载。"""
    global _config_cache
    with _lock:
        _config_cache = None
