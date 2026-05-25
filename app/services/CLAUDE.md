# services — 业务逻辑层

所有 API 路由通过此层访问数据和模型，不直接操作底层存储。

## session_service.py

会话管理服务。封装 SQLite + JSON 双存储。

- `SessionService(checkpointer)` — 构造函数，传入 `SqliteSaver` 实例
- **懒加载**：首次调用 `_ensure_loaded()` 时才从 SQLite 和 JSON 加载数据
- `_sync()` — 用集合差集独立处理两侧孤儿记录
- `list_sessions()` — 返回 `[{name, thread_id}]`
- `get_or_create_session(name)` — 同名自动复用，返回 `{name, thread_id, config, created}`
- `delete_session(name)` — 删除 SQLite 检查点 + JSON 映射
- `_save_json()` — 持久化名称映射到 `sessions.json`

## config_service.py

配置读写服务，封装 `core/config.py`。

- `get_settings()` — 返回原生类型列表 `[{key, value, description}]`
- `update_settings(partial)` — 过滤未知键和 None 值后调用 `update_config`
- `CONFIG_DESCRIPTIONS` — 配置项中文说明映射

## tool_service.py

工具管理服务。

- `get_tools_status()` — 列出所有工具及启用状态
- `set_tool_enabled(name, enabled)` — 修改 `enabled_tools` 列表 → `update_config` → 触发图重建
- `test_tool(name)` — 代理到 `tools/__init__.py` 的 `test_tool`
