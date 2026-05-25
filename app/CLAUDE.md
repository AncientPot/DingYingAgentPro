# app — 后端应用

基于 FastAPI + LangGraph + DeepSeek 的智能助手后端。

## 启动

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 分层架构

```
HTTP 请求
  │
  ▼
api/          ← 路由层：请求解析、响应格式化，不含业务逻辑
  │
  ▼
services/     ← 服务层：会话CRUD、配置读写、工具管理
  │
  ▼
agent/        ← Agent 引擎：LangGraph 图构建、LLM 调用、检查点持久化
  │  ▲
  ▼  │
tools/        ← 工具插件：自动发现、动态加载、连通性测试
  │
  ▼
models/       ← 数据模型：Pydantic 请求/响应 Schema
  │
  ▼
core/         ← 基础设施：配置管理（JSON+热重载+脱敏）
```

各层通过 `core/config.py` 读取配置，不跨层直接访问存储。

## 子包索引

| 包 | 文档 | 职责 |
|----|------|------|
| `core/` | [CLAUDE.md](core/CLAUDE.md) | 配置管理、缓存、锁、变更回调 |
| `agent/` | [CLAUDE.md](agent/CLAUDE.md) | LangGraph 图构建、epoch 缓存、检查点 |
| `tools/` | [CLAUDE.md](tools/CLAUDE.md) | 工具插件加载器、开发规范、自检 |
| `models/` | [CLAUDE.md](models/CLAUDE.md) | Pydantic Schema 定义 |
| `services/` | [CLAUDE.md](services/CLAUDE.md) | 会话/配置/工具业务逻辑 |
| `api/` | [CLAUDE.md](api/CLAUDE.md) | 全部 HTTP 路由（含游戏模式 10 个端点） |

## main.py — 应用入口

- **CORS**: `allow_origins=["*"]`，允许前端跨域开发
- **startup 事件**: 初始化 `SessionService`（注入 `SqliteSaver`）→ 预热 `get_graph()`
- **app.state.session_service**: 全局单例，路由层通过 `request.app.state.session_service` 获取
- **路由注册**: 4 个 router 挂载到 `/api` 前缀

## 关键约束

- 配置热重载：修改配置 → `config.json` 持久化 → 回调通知 → Agent 图自动重建，无需重启
- 会话持久化：SQLite 存对话检查点，JSON 存名称映射，同名自动复用
- 工具加载：导入失败静默跳过（平台不兼容/缺依赖），增删 `.py` 即生效
- 锁安全：`core/config.py` 和 `agent/graph.py` 各持独立 `threading.Lock`，回调在锁外执行避免死锁
- 流式传输：SSE 事件类型 `chunk/tool/done/error`，`tool_call_id` 精确匹配工具结果
