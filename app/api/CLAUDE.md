# api — HTTP API 路由层

仅负责请求解析和响应格式化，不含业务逻辑。通过 `request.app.state.session_service` 获取服务实例。

## 端点总览

| 路由 | 方法 | 文件 |
|------|------|------|
| `/api/chat` | POST | chat.py |
| `/api/chat/stream` | POST | chat.py |
| `/api/sessions` | GET, POST | sessions.py |
| `/api/sessions/{name}` | DELETE | sessions.py |
| `/api/sessions/{name}/messages` | GET | sessions.py |
| `/api/config` | GET, PUT | config.py |
| `/api/tools` | GET | tools.py |
| `/api/tools/{name}` | PUT | tools.py |
| `/api/tools/{name}/test` | POST | tools.py |
| `/api/health` | GET | main.py |

## chat.py

- `POST /api/chat` — 非流式，`stream_mode="values"`，收集完整 AIMessage 后返回
- `POST /api/chat/stream` — SSE 流式，`stream_mode="messages"`，`ThreadQueue` 桥接同步 LangGraph 流到异步生成器
- `_serialize_stream_event(event)` — 将 `AIMessageChunk` / `ToolMessage` 序列化为 JSON
  - chunk: `{type, content, tool_calls}`
  - tool: `{type, tool_name, tool_call_id, content}`
  - done: `{type, tokens}`
  - error: `{type, content}`

## sessions.py

- `GET /sessions` — 列出全部会话
- `POST /sessions` — 创建/复用会话
- `DELETE /sessions/{name}` — 删除会话
- `GET /sessions/{name}/messages` — 从 LangGraph checkpoints 读取历史消息并序列化
  - HumanMessage → `{role: "user", content}`
  - AIMessage → `{role: "assistant", content, tool_calls}`
  - ToolMessage → `{role: "tool", name, tool_call_id, content}`

## config.py

- `GET /config` — 调用 `get_settings()` 返回配置列表
- `PUT /config` — 接收 `ConfigUpdateRequest`，调用 `update_settings()` 更新

## tools.py

- `GET /tools` — 调用 `get_tools_status()` 返回工具列表
- `PUT /tools/{name}` — 接收 `ToolToggleRequest`，调用 `set_tool_enabled()` 切换启用状态
- `POST /tools/{name}/test` — 调用 `test_tool()` 执行连通性检测

## game.py — 游戏模式

- `GET /game/state` — 游戏状态（game_mode, sub_mode）
- `GET /game/settings` — 游戏设置（间隔、提示词、当前游戏工具）
- `PUT /game/settings` — 更新游戏设置
- `GET /game/tools` — 列出可用游戏工具（game_tools/ 目录）
- `POST /game/start` — 准备中→游戏中
- `POST /game/stop` — 游戏中→准备中
- `POST /game/chat` — 准备中对话（使用 /prep 线程，与正常对话隔离）
- `POST /game/think` — AI 自主思考 SSE（仅 playing，含游戏工具调用+执行）
- `POST /game/gameover` — 游戏结束总结 → prep 线程 → 切换到准备中
- `POST /game/exit` — 退出游戏模式
