# models — Pydantic 请求/响应模型

## schemas.py

所有 API 的数据契约定义在此。前端依赖这些类型进行请求构造和响应解析。

### 聊天
- `ChatRequest` — `session_name` + `message`
- `ChatResponse` — `session_name`, `role`, `content`, `tool_calls`, `tokens`

### 会话
- `SessionCreateRequest` — `name`
- `SessionInfo` — `name`, `thread_id`
- `SessionListResponse` — `sessions: list[SessionInfo]`

### 设置
- `ConfigItem` — `key: str`, `value: Any`（注意是 Any 不是 str，保留原生类型）
- `ConfigResponse` — `configs: list[ConfigItem]`
- `ConfigUpdateRequest` — 所有字段 Optional，允许部分更新
  - 字段：`model_name`, `temperature`, `api_key`, `base_url`, `system_prompt`, `max_search_results`, `enabled_tools`
  - `enabled_tools` 类型为 `list[str]`，前端保存时须排除此字段（在工具管理页维护）

### 工具
- `ToolInfo` — `name`, `display_name`, `description`, `enabled`
- `ToolListResponse` — `tools: list[ToolInfo]`
- `ToolToggleRequest` — `enabled: bool`
- `ToolTestResponse` — `ok: bool`, `message: str`, `details: str`

### 通用
- `MessageResponse` — `detail: str`
