import json
from fastapi import APIRouter, Depends, HTTPException
from backend.modules.config_manager import (
    SessionConfigManager,
    GlobalSettingsManager,
    VersionConflictError,
)
from backend.dependencies import get_config_manager, get_global_settings
from backend.schemas.session import SessionConfigResponse, SessionConfigUpdate
from backend.schemas.config import GlobalSettingUpdate

router = APIRouter(tags=["configs"])


@router.get("/sessions/{session_id}/config", response_model=SessionConfigResponse)
async def get_session_config(
    session_id: str,
    config_mgr: SessionConfigManager = Depends(get_config_manager),
):
    config = await config_mgr.get_config(session_id)
    if config is None:
        raise HTTPException(404, "Session config not found")
    return config


@router.put("/sessions/{session_id}/config", response_model=SessionConfigResponse)
async def update_session_config(
    session_id: str,
    body: SessionConfigUpdate,
    config_mgr: SessionConfigManager = Depends(get_config_manager),
):
    try:
        updates = body.model_dump(exclude_none=True)
        version = updates.pop("version")
        return await config_mgr.update_config(session_id, updates, version)
    except VersionConflictError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(404, str(e))


settings_router = APIRouter(prefix="/settings", tags=["settings"])


@settings_router.get("")
async def get_all_settings(
    gs: GlobalSettingsManager = Depends(get_global_settings),
):
    return await gs.get_all()


@settings_router.put("/{key}")
async def update_setting(
    key: str,
    body: GlobalSettingUpdate,
    gs: GlobalSettingsManager = Depends(get_global_settings),
):
    value = body.value
    try:
        value = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        pass
    await gs.set(key, value)
    return {"key": key, "value": value}
