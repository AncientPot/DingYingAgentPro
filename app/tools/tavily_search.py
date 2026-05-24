"""Tavily 联网搜索工具。"""

import logging
import os

from dotenv import load_dotenv
from langchain_tavily import TavilySearch

from app.core.config import get_config, on_config_changed

load_dotenv()

logger = logging.getLogger(__name__)

_search_instance = None
_last_max_results = None


def _get_search():
    """获取或创建 TavilySearch 实例，配置变更时自动重建。"""
    global _search_instance, _last_max_results

    if not os.getenv("TAVILY_API_KEY"):
        raise RuntimeError("未设置 TAVILY_API_KEY 环境变量，Tavily 搜索工具不可用。")

    config = get_config()
    max_results = config.get("max_search_results", 2)

    if _search_instance is not None and max_results == _last_max_results:
        return _search_instance

    _search_instance = TavilySearch(max_results=max_results)
    _last_max_results = max_results
    return _search_instance


def get_tool():
    """返回 Tavily 搜索工具实例。"""
    return _get_search()


# 配置变更时重置缓存，确保下次获取的是新参数实例
def _on_config_changed(_new_config):
    global _last_max_results
    _last_max_results = None

on_config_changed(_on_config_changed)
