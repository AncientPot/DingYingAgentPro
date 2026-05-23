from pydantic import BaseModel, Field


class GlobalSettingUpdate(BaseModel):
    value: str


class GlobalSettingResponse(BaseModel):
    key: str
    value: str
    updated_at: str
