# CLAUDE.md — DingYingAgentPro

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> 各子包有独立的 `CLAUDE.md`，从根向叶子逐级深入：
> - [app/CLAUDE.md](app/CLAUDE.md) — 应用入口与生命周期
> - [app/core/CLAUDE.md](app/core/CLAUDE.md) — 配置系统
> - [app/agent/CLAUDE.md](app/agent/CLAUDE.md) — Agent 图引擎
> - [app/tools/CLAUDE.md](app/tools/CLAUDE.md) — 插件式工具系统
> - [app/models/CLAUDE.md](app/models/CLAUDE.md) — 请求/响应模型
> - [app/services/CLAUDE.md](app/services/CLAUDE.md) — 业务逻辑层
> - [app/api/CLAUDE.md](app/api/CLAUDE.md) — HTTP API 路由
> - [frontend/CLAUDE.md](frontend/CLAUDE.md) — Vue3 前端
> - [README_API.md](README_API.md) — 面向使用者的 API 接口文档

## 常用命令

```bash
# 后端启动
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 前端启动（另一个终端）
cd frontend && npm run dev          # 开发服务器 http://127.0.0.1:5173
cd frontend && npm run build        # 生产构建到 dist/

# 安装依赖
pip install -e .                    # Python（在 .venv 中）
cd frontend && npm install          # 前端

# 快速验证
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/tools
```

前端 Vite 开发服务器将 `/api/*` 代理到 `localhost:8000`，开发时无需 CORS 配置。生产部署时需要后端 CORS 或反向代理。

## 架构

### 分层设计

```
前端(Vue3) → HTTP/SSE → FastAPI路由 → 服务层 → Agent图(LangGraph) → DeepSeek LLM
                                               ↓
                                         工具插件系统(自动发现)
```

- **`app/api/`** — FastAPI 路由，仅做请求解析和响应格式化，不包含业务逻辑
- **`app/services/`** — 业务逻辑层：会话CRUD、配置读写、工具管理
- **`app/agent/graph.py`** — LangGraph 图构建与缓存。版本计数器（epoch）驱动配置热重载，`_build_graph()` 在首次请求或配置变更后重建
- **`app/tools/`** — 插件式工具目录，`__init__.py` 的加载器自动扫描 `.py` 文件

### 配置系统

三层优先级：`config.json` > 环境变量 > `_DEFAULT_CONFIG`（在 `core/config.py` 中）。

- `get_masked_config()` 返回脱敏版用于 API 响应（`api_key` 中间位替换为 `*`）
- `update_config()` 写入 `config.json` → 触发 `on_config_changed` 回调 → `invalidate_graph()` 递增 epoch
- `get_settings()` 返回**原生类型**（`int`/`float`/`list`，不是全字符串），前端依赖此行为
- 保存设置时前端须检查 `api_key` 值是否含脱敏标记 `*`，若是则跳过发送（防止脱敏值覆盖真实密钥）

### 工具插件规范

`app/tools/` 下每个 `.py` 文件需暴露两个函数：

| 函数 | 必须 | 签名 | 说明 |
|------|:--:|------|------|
| `get_tool()` | ✅ | `() -> BaseTool` | 返回 LangChain 工具实例 |
| `test_tool()` | 推荐 | `() -> dict` | `{"ok": bool, "message": str, "details": str}` |

加载器导入失败时静默跳过（平台不兼容/缺依赖），`test_tool()` 未提供时回退到验证 `get_tool()` 可调用。

### 会话持久化

- SQLite `checkpoints.sqlite` 存 LangGraph 对话检查点（历史上下文）
- `sessions.json` 存名称→thread_id 映射
- `SessionService._sync()` 独立处理两侧孤儿记录，使用集合差集而非严格子集判断
- 同名会话自动复用，`SessionService` 懒加载首次使用时初始化

### 流式传输关键约束

- 后端 `chat.py` SSE 事件类型：`chunk`(文本+tool_calls)、`tool`(含 `tool_call_id`)、`done`、`error`
- 前端 ChatView 消息数组元素是 **Vue 响应式代理**，必须 `messages.value.push(...)` 后再取引用：`const aiMsg = messages.value[messages.value.length - 1]`
- 工具结果按 `tool_call_id` 匹配（非数组位置），后端 `_serialize_stream_event` 须输出此字段
- 前端 `api/index.js` 的 SSE 生成器中 `JSON.parse` 须 try-catch，畸形行跳过而非终止流

### 图缓存机制

- `get_graph()` 使用 epoch 版本计数器（`_config_epoch` / `_graph_epoch`）
- 快速路径无锁比较 epoch（存在极低概率 TOCTOU 窗口，单用户场景可忽略）
- `invalidate_graph()` 在 `graph._lock` 内递增 `_config_epoch` 并置 `_graph = None`
- `_build_graph()` 内部直接调用 `get_config()` 读取最新值，不依赖外部传参

### 锁使用

两个独立的 `threading.Lock`：`core/config.py` 的 `_lock` 和 `agent/graph.py` 的 `_lock`。回调机制确保 `update_config()` 释放 `config._lock` 后才调用 `graph._lock`，不会形成锁顺序死锁。`get_config()` 因缓存命中率高（首次后不触发内部锁）在 `_build_graph` 持有 `graph._lock` 时调用安全。

## 前端架构

- Vue 3 Composition API + `<script setup>`，Pinia 状态管理，Vue Router 懒加载
- `keep-alive` 包裹 `router-view` 缓存 ChatView 消息历史
- CSS 全局样式在 `style.css`（玻璃面板 `.glass`、toggle 开关 `.toggle-track/.toggle-thumb`、消息动画 `.msg-enter`）
- Tailwind 自定义色板：`base-{900..700}` 背景层次，`accent` 电光青，`amber-tool` 工具调用色
- 字体使用系统原生（微软雅黑/苹方），不依赖 Google Fonts
