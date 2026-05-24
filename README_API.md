# DingYingAgentPro API

基于 **LangGraph + FastAPI** 的智能助手后端，支持插件式工具系统、流式对话、会话管理和运行时配置。

## 目录结构

```
app/
├── main.py                  # FastAPI 入口，CORS，生命周期
├── core/
│   └── config.py            # 运行时配置管理（JSON 持久化 + 热重载）
├── agent/
│   └── graph.py             # LangGraph 图构建（单例，配置变更自动重建）
├── tools/                   # 🔧 插件式工具目录
│   ├── __init__.py          # 工具自动发现加载器
│   ├── calculator.py        # 计算器工具
│   ├── tavily_search.py     # 联网搜索工具
│   └── netease_cloud_music.py  # 网易云音乐控制（仅 Windows）
├── models/
│   └── schemas.py           # Pydantic 请求/响应模型
├── services/
│   ├── session_service.py   # 会话 CRUD（SQLite + JSON）
│   ├── config_service.py    # 配置读写服务
│   └── tool_service.py      # 工具发现与启用管理
└── api/
    ├── chat.py              # 聊天接口（流式 SSE + 非流式）
    ├── sessions.py          # 会话管理接口
    ├── config.py            # 设置接口
    └── tools.py             # 工具管理接口
```

## 快速启动

```bash
# 1. 确保 .env 中配置了必要的 API Key
#    DEEPSEEK_API_KEY=...
#    TAVILY_API_KEY=...

# 2. 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 3. 访问
#    API 文档: http://localhost:8000/docs
#    健康检查: http://localhost:8000/api/health
```

## API 接口一览

### 聊天

| 方法 | 路由 | 说明 |
|------|------|------|
| `POST` | `/api/chat` | 非流式聊天，等待完整响应后返回 |
| `POST` | `/api/chat/stream` | SSE 流式聊天，逐字推送 |

**请求体：**
```json
{
  "session_name": "my-session",
  "message": "你好，请帮我算一下 3 + 5"
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

**流式 SSE 事件类型：**
```
data: {"type":"chunk","content":"3","tool_calls":null}
data: {"type":"chunk","content":" + 5 = 8","tool_calls":null}
data: {"type":"tool","tool_name":"calculator","content":"8"}
data: {"type":"done","tokens":150}
```

前端消费示例：
```javascript
const response = await fetch('/api/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ session_name: 'default', message: '你好' })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const text = decoder.decode(value);
  // 解析 SSE 格式: "data: {...}\n\n"
  const lines = text.split('\n');
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const event = JSON.parse(line.slice(6));
      // event.type: "chunk" | "tool" | "done" | "error"
    }
  }
}
```

### 会话管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/sessions` | 列出所有会话 |
| `POST` | `/api/sessions` | 创建新会话 |
| `DELETE` | `/api/sessions/{name}` | 删除指定会话 |

### 设置

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/config` | 获取当前配置（密钥脱敏） |
| `PUT` | `/api/config` | 更新配置（修改后 Agent 自动重建） |

可配置项：
| 键 | 说明 | 默认值 |
|----|------|--------|
| `model_name` | 模型名称 | `deepseek-chat` |
| `temperature` | 模型温度 (0-2) | `0.7` |
| `api_key` | DeepSeek API 密钥 | 从环境变量读取 |
| `base_url` | API 基础地址 | 留空使用默认 |
| `system_prompt` | 系统提示词 | 通用助手提示词 |
| `max_search_results` | 搜索最大结果数 | `2` |
| `enabled_tools` | 启用的工具列表 | 全部启用 |

### 工具管理

| 方法 | 路由 | 说明 |
|------|------|------|
| `GET` | `/api/tools` | 列出所有可用工具及启用状态 |
| `PUT` | `/api/tools/{name}` | 启用/禁用指定工具 |

请求体：
```json
{ "enabled": true }
```

## 工具插件开发指南

在 `app/tools/` 下新建 `.py` 文件，实现 `get_tool()` 函数即可。**拖入即生效，删除即移除。**

### 最简示例

```python
# app/tools/my_tool.py
from langchain_core.tools import tool

@tool
def my_tool(param: str) -> str:
    """工具描述——这会被 LLM 阅读来决定何时调用。"""
    return f"处理结果: {param}"

def get_tool():
    return my_tool
```

### 规范

1. 文件名即工具 ID（如 `weather.py` → 工具名为 `weather`）
2. 必须暴露 `def get_tool()` 返回 LangChain BaseTool 对象
3. 导入失败（缺依赖、平台不兼容）时加载器自动跳过并记录警告
4. 工具默认全部启用，可通过 API 或配置文件的 `enabled_tools` 控制

### 完整示例参见

- `app/tools/calculator.py` — 简单 @tool 装饰器
- `app/tools/tavily_search.py` — 带外部 API 的工具
- `app/tools/netease_cloud_music.py` — 平台特定工具，含辅助函数

## 会话持久化

- SQLite 管理 LangGraph 检查点（对话历史）
- JSON 文件管理会话名称 → ID 映射
- 两个数据源自动同步一致性
- 同名会话自动复用，无需手动管理 ID

## 配置热重载

通过 `PUT /api/config` 修改配置后：
1. 配置写入 `config.json` 持久化
2. Agent 图缓存自动失效
3. 下次请求时使用新配置重建图（新模型、新温度、新工具集即时生效）
4. **无需重启服务**

## 前端集成要点

1. **设置页面**：`GET /api/config` 加载表单 → 用户修改 → `PUT /api/config` 保存
2. **工具管理**：`GET /api/tools` 展示工具卡片 → 切换开关 → `PUT /api/tools/{name}`
3. **聊天页面**：`POST /api/chat/stream` 搭配 SSE 实现打字机效果
4. **会话列表**：`GET /api/sessions` 展示历史会话，点击切换 `session_name`
5. **健康监控**：轮询 `GET /api/health` 判断服务状态
