# DingYingAgentPro API

基于 **LangGraph + FastAPI** 的智能助手后端 —— 插件式工具系统、流式对话、会话管理、运行时配置热重载。

## 目录结构

```
DingYingAgentPro/
├── app/
│   ├── main.py                  # FastAPI 入口，CORS，生命周期
│   ├── core/
│   │   └── config.py            # 运行时配置（JSON持久化 + 热重载 + 脱敏）
│   ├── agent/
│   │   └── graph.py             # LangGraph 图（版本式缓存，配置变更自动重建）
│   ├── tools/                   # 🔧 插件式工具目录
│   │   ├── __init__.py          # 工具加载器 + 测试器
│   │   ├── calculator.py        # 计算器工具
│   │   ├── tavily_search.py     # 联网搜索工具
│   │   └── netease_cloud_music.py  # 网易云音乐控制
│   ├── models/
│   │   └── schemas.py           # Pydantic 请求/响应模型
│   ├── services/
│   │   ├── session_service.py   # 会话 CRUD（SQLite + JSON）
│   │   ├── config_service.py    # 配置读写
│   │   └── tool_service.py      # 工具发现、启用管理、连通性测试
│   └── api/
│       ├── chat.py              # 聊天（流式SSE + 非流式）
│       ├── sessions.py          # 会话管理
│       ├── config.py            # 设置
│       └── tools.py             # 工具管理 + 测试
├── frontend/                    # Vue 3 前端
├── 基础代码.py                   # 原 CLI 程序（保留）
└── README_API.md                # 本文档
```

## 快速启动

```bash
# 1. 确保 .env 中配置了 API Key
#    DEEPSEEK_API_KEY=sk-...
#    TAVILY_API_KEY=tvly-...

# 2. 启动后端
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 启动前端（可选）
cd frontend && npm install && npm run dev

# 4. 访问
#    API 文档: http://localhost:8000/docs
#    前端界面: http://localhost:5173
#    健康检查: http://localhost:8000/api/health
```

## API 接口

### 1. 聊天

| 方法 | 路由 | 说明 |
|------|------|------|
| `POST` | `/api/chat` | 非流式聊天，完整响应 |
| `POST` | `/api/chat/stream` | SSE 流式聊天，逐字推送 |

**请求体：**
```json
{
  "session_name": "my-session",
  "message": "你好，请计算 3 + 5"
}
```

**非流式响应：**
```json
{
  "session_name": "my-session",
  "role": "assistant",
  "content": "3 + 5 = 8",
  "tool_calls": [{"name": "calculator", "args": {"a": 3, "b": 5, "op": "add"}}],
  "tokens": 150
}
```

**SSE 流式事件：**

| event.type | 含义 | 字段 |
|------------|------|------|
| `chunk` | AI 文本片段 | `content`, `tool_calls` |
| `tool` | 工具返回结果 | `tool_name`, `content` |
| `done` | 响应完成 | `tokens` |
| `error` | 发生错误 | `content` |

```
data: {"type":"chunk","content":"3","tool_calls":null}
data: {"type":"chunk","content":" + 5 = 8","tool_calls":null}
data: {"type":"tool","tool_name":"calculator","content":"8"}
data: {"type":"done","tokens":150}
```

前端消费：
```javascript
const r = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ session_name: 'default', message: '你好' })
})
const reader = r.body.getReader()
const decoder = new TextDecoder()
let buffer = ''
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  buffer += decoder.decode(value, { stream: true })
  for (const line of buffer.split('\n')) {
    if (line.startsWith('data: ')) {
      const evt = JSON.parse(line.slice(6))
      // evt.type: chunk | tool | done | error
    }
  }
}
```

### 2. 会话管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/sessions` | 列出所有会话 |
| `POST` | `/api/sessions` | 创建/复用会话 |
| `DELETE` | `/api/sessions/{name}` | 删除会话 |
| `GET` | `/api/sessions/{name}/messages` | 获取会话历史消息 |

```json
// POST /api/sessions
{ "name": "新会话" }

// 响应
{ "name": "新会话", "thread_id": "uuid..." }
```

**历史消息响应：**
```json
{
  "messages": [
    {"role": "user", "content": "你好"},
    {"role": "assistant", "content": "你好！有什么可以帮助你的？"},
    {"role": "assistant", "content": "15 × 8 = 120", "tool_calls": [{"name": "calculator", "args": {...}, "id": "..."}]},
    {"role": "tool", "name": "calculator", "tool_call_id": "...", "content": "120"}
  ]
}
```
前端刷新页面后调用此接口恢复对话历史。

### 3. 设置

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/config` | 获取配置（API Key 脱敏） |
| `PUT` | `/api/config` | 更新配置（Agent 自动重建） |

**可配置项：**

| 键 | 类型 | 说明 | 默认值 |
|----|------|------|--------|
| `model_name` | string | 模型名称 | `deepseek-chat` |
| `temperature` | float | 模型温度 (0-2) | `0.7` |
| `api_key` | string | DeepSeek API 密钥 | 从 .env 读取 |
| `base_url` | string | API 基础地址 | 默认 DeepSeek |
| `system_prompt` | string | 系统提示词 | 通用助手 |
| `max_search_results` | int | 搜索最大结果数 | `2` |
| `enabled_tools` | list | 启用的工具模块名 | 全部启用 |

```json
// PUT /api/config
{ "temperature": 0.5, "system_prompt": "你是一个专业的音乐助手。" }
```

### 4. 工具管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/tools` | 列出工具及启用状态 |
| `PUT` | `/api/tools/{name}` | 启用/禁用工具 |
| `POST` | `/api/tools/{name}/test` | **测试工具连通性** |

**工具测试接口（POST /api/tools/{name}/test）：**

根据工具类型执行不同检测，返回工具是否实际可用：

```json
// POST /api/tools/calculator/test
{
  "ok": true,
  "message": "计算器工具正常（加/减/乘法测试通过）",
  "details": "3+4=7 10-3=7 3*3=9"
}

// POST /api/tools/netease_cloud_music/test
{
  "ok": true,
  "message": "网易云音乐正在运行（PID: 12345），窗口可定位",
  "details": "程序路径: D:\\CloudMusic\\cloudmusic.exe"
}

// POST /api/tools/nonexistent/test
{
  "ok": false,
  "message": "工具 'nonexistent' 不存在",
  "details": ""
}
```

**前端使用建议：** 工具管理页面为每个工具提供"测试"按钮，调用此接口展示绿色通过/红色失败状态，让用户和 AI 都能感知哪个工具当前可用。

---

## 工具插件开发指南

在 `app/tools/` 目录下创建 `.py` 文件，实现两个函数即可。**增删 .py 文件即增删工具，无需重启服务。**

### 最简示例

```python
# app/tools/my_tool.py
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """
    工具描述——这段文字会被 LLM 阅读，
    用于判断何时调用本工具。
    """
    return f"处理结果: {param}"

def get_tool():
    """【必须】返回 LangChain BaseTool 实例。"""
    return my_tool

def test_tool():
    """【可选】自检函数，用于 API 测试接口。"""
    try:
        result = my_tool.invoke({"param": "test"})
        return {"ok": True, "message": "工具正常", "details": str(result)}
    except Exception as e:
        return {"ok": False, "message": str(e), "details": ""}
```

### 接口规范

每个工具模块 (`app/tools/xxx.py`) 应暴露两个函数：

| 函数 | 必须 | 签名 | 说明 |
|------|:--:|------|------|
| `get_tool()` | ✅ 必须 | `() -> BaseTool` | 返回 LangChain 工具对象 |
| `test_tool()` | 推荐 | `() -> dict` | 自检函数，返回 `{"ok": bool, "message": str, "details": str}` |

**`test_tool()` 未提供时**，加载器会回退到验证 `get_tool()` 能否正常调用。

### 完整示例

**带外部 API 的工具（tavily_search）：**

```python
# app/tools/my_search.py
import os
from langchain_community.tools import SomeSearchTool

def get_tool():
    return SomeSearchTool(api_key=os.getenv("MY_API_KEY"))

def test_tool():
    api_key = os.getenv("MY_API_KEY")
    if not api_key:
        return {"ok": False, "message": "未配置 API Key", "details": ""}
    try:
        tool = get_tool()
        result = tool.invoke("test query")
        return {"ok": True, "message": "API 连通正常", "details": result[:200]}
    except Exception as e:
        return {"ok": False, "message": f"API 测试失败: {e}", "details": str(e)}
```

**平台特定工具（仅 Windows）：**

```python
# app/tools/windows_only.py
import sys
from langchain_core.tools import tool

@tool
def windows_tool(action: str) -> str:
    """仅 Windows 平台可用的工具。"""
    ...

def get_tool():
    return windows_tool

def test_tool():
    if sys.platform != "win32":
        return {"ok": False, "message": "此工具仅支持 Windows", "details": f"当前平台: {sys.platform}"}
    # 执行平台检测
    ...
```

### 工作原理

```
tools/__init__.py 启动时扫描目录
        │
        ├─ 发现 xxx.py → importlib.import_module("app.tools.xxx")
        │
        ├─ 有 get_tool()? → 获取 BaseTool 实例 → 加入 LLM 工具列表
        │   否则 → 跳过并警告
        │
        ├─ 导入失败? → 跳过（平台不兼容 / 缺依赖）
        │
        └─ list_available_tools() 列出所有发现的工具元信息
           test_tool()          执行连通性检测
```

### 行为约定

1. **文件名即为工具 ID**：`weather.py` → API 中通过 `weather` 引用
2. **导入失败的模块自动跳过**：平台不兼容（缺少 `pywin32` / 非 Windows）、缺依赖时静默跳过
3. **通过 `enabled_tools` 控制启用**：在设置的 `enabled_tools` 列表中列出启用项
4. **`test_tool()` 异常不影响正常使用**：测试失败仅影响测试接口的返回值

---

## 会话持久化

- **SQLite** (`checkpoints.sqlite`)：LangGraph 对话历史检查点
- **JSON** (`sessions.json`)：会话名称 → thread_id 映射
- 同名会话自动复用，两个数据源自动同步
- 删除会话清除对话历史

## 配置热重载

通过 `PUT /api/config` 修改后：

1. 配置写入 `config.json` 持久化
2. 回调通知 Agent 图缓存失效
3. 下次请求时用新配置重建图 —— 新模型、新温度、新提示词、新工具集全部即时生效
4. **无需重启服务**

## 环境变量 (.env)

| 变量 | 必须 | 说明 |
|------|:--:|------|
| `DEEPSEEK_API_KEY` | ✅ | DeepSeek API 密钥 |
| `TAVILY_API_KEY` | 可选 | Tavily 联网搜索（未配置则搜索工具不可用） |
| `DEEPSEEK_BASE_URL` | 可选 | 自定义 API 地址 |

## 前端集成

| 页面 | API 调用 |
|------|----------|
| 对话主页 | `POST /api/chat/stream` SSE 流式，`GET/POST/DELETE /api/sessions` |
| 设置页 | `GET /api/config` 加载 + `PUT /api/config` 保存 |
| 工具管理 | `GET /api/tools` 列表 + `PUT /api/tools/{name}` 开关 + `POST /api/tools/{name}/test` 测试 |
| 健康监控 | `GET /api/health` 轮询 |
