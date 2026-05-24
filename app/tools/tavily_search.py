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


def test_tool() -> dict:
    """自检：验证 API Key 是否配置，并尝试一次搜索请求。"""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return {"ok": False, "message": "未配置 TAVILY_API_KEY 环境变量", "details": "请在 .env 文件中添加 TAVILY_API_KEY"}

    try:
        search = _get_search()
        result = search.invoke("test")
        if result:
            return {"ok": True, "message": "Tavily 搜索工具正常（API 连通测试通过）", "details": f"测试搜索返回了结果，API Key: {api_key[:8]}..."}
        return {"ok": False, "message": "Tavily 搜索返回空结果", "details": "API 连通但搜索无返回"}
    except Exception as e:
        return {"ok": False, "message": f"Tavily 搜索测试失败: {e}", "details": str(e)}


# 配置变更时重置缓存，确保下次获取的是新参数实例
def _on_config_changed(_new_config):
    global _last_max_results
    _last_max_results = None

on_config_changed(_on_config_changed)
