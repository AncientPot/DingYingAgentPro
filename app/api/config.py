"""配置/设置接口 —— 供前端设置页面调用。"""

import logging

from fastapi import APIRouter

from app.models.schemas import ConfigItem, ConfigResponse, ConfigUpdateRequest
from app.services.config_service import get_settings, update_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=ConfigResponse)
def get_config():
    """获取当前配置（API Key 等敏感字段已脱敏）。"""
    items = get_settings()
    return ConfigResponse(configs=[ConfigItem(**item) for item in items])


@router.put("", response_model=ConfigResponse)
def update_config(req: ConfigUpdateRequest):
    """
    更新配置。只更新请求中提供的字段，其余保持不变。
    配置变更后 Agent 图会自动重建，无需重启服务。
    """
    update_settings(req.model_dump(exclude_none=True))
    items = get_settings()
    return ConfigResponse(configs=[ConfigItem(**item) for item in items])
