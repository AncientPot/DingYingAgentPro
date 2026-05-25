# frontend — Vue3 前端

Vue 3 + Vite + Pinia + Vue Router + TailwindCSS v3。

## 启动

```bash
cd frontend && npm run dev    # http://127.0.0.1:5173
npm run build                  # 生产构建到 dist/
```

Vite 将 `/api/*` 代理到后端 `localhost:8000`（`vite.config.js`）。

## 路由 (router/index.js)

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | → `/chat` | 重定向 |
| `/chat` | ChatView | 对话主页 |
| `/tools` | ToolsView | 工具管理 |
| `/settings` | SettingsView | 设置页 |

`keep-alive` 包裹 `router-view` 缓存 ChatView。

## 状态管理 (stores/)

| Store | 文件 | 职责 |
|-------|------|------|
| `useSessionStore` | stores/session.js | 会话列表、当前会话、创建/删除 |
| `useConfigStore` | stores/config.js | 配置读写、保存状态、错误反馈 |
| `useToolsStore` | stores/tools.js | 工具列表、启用/禁用开关 |

## API 层 (api/index.js)

所有后端接口封装，基于 `fetch`。

- `request(method, path, body)` — 通用请求函数，自动 JSON 序列化
- `streamMessage(sessionName, message, signal)` — SSE 异步生成器，`getReader()` + `TextDecoder` 逐行解析
- `getSessionMessages(name)` — 获取会话历史消息

## 视图 (views/)

### ChatView.vue
对话主页，左右布局：SessionSidebar + 消息区。

- **消息交织渲染**: `{type:'user'|'ai'|'tool'}` 数组，AI 文本段 → tool 卡片 → AI 文本段交替
- **流式接收**: `for await (evt of streamMessage(...))`，chunk 追加到当前 AI 段，tool_call 触发新 tool 卡片 + 新 AI 段
- **历史加载**: `loadHistory(name)` 切换/刷新时从 `/sessions/{name}/messages` 拉取
- **tool 卡片匹配**: 按 `tool_call_id` 精确匹配工具结果

### SettingsView.vue
6 项配置：model_name(select)、temperature(range)、api_key(password)、base_url(text)、system_prompt(textarea)、max_search_results(number)。

保存时 `api_key` 含 `*` 跳过（防止脱敏值覆盖），数字字段还原类型。

### ToolsView.vue
工具卡片网格，每卡含"测试"按钮（`POST /tools/{name}/test`）和 toggle 开关。

## 组件 (components/)

| 组件 | 功能 |
|------|------|
| TopNav | 顶栏 Logo + 导航链接（对话/工具/设置） |
| SessionSidebar | 左侧会话列表 + 新建/删除 |
| ChatMessage | 消息气泡，渲染 `**粗体**`，流式时显示光标 |
| ChatInput | 自动伸缩 textarea + 发光发送按钮 |
| ToolCallCard | 琥珀色边框，默认折叠，点击展开 |
| GameCanvas | 游戏视图：准备中(设置面板)+游戏中(游戏画面) |
| GameSettings | 游戏设置：间隔滑块、游戏工具单选、每工具专属设置 |
| SnakeGame | Canvas 贪吃蛇：40x40网格，键盘操控，AI放置食物/障碍物 |

### 游戏模式 (stores/game.js)

- `gameMode` / `subMode` (`preparing`|`playing`) 双状态
- **准备中**: 设置面板为主体，底部"开始游戏"+"退出游戏模式"
- **游戏中**: 输入框禁用，AI 自主回复，设置不可调
- 进入游戏时侧边栏自动折叠
- `checkState()` 刷新后恢复游戏状态
- 三层提示词：全局 system_prompt → game_think_prompt → 工具 docstring
- 三线程隔离：`{base_tid}` / `{base_tid}/prep` / `{base_tid}/play`

## 样式 (style.css)

- **暗色主题**: `base-{900..700}` 背景层次，`accent` 电光青 `#00e5ff`，`amber-tool` 琥珀 `#ffb74d`
- **玻璃面板**: `.glass` — `rgba(255,255,255,0.05)` + `blur(12px)`
- **背景**: 60px 网格纹理 + 扫描线叠加
- **动画**: `.msg-enter` 消息滑入，`.loading-dot` 加载脉冲
- **字体**: 微软雅黑/苹方（系统原生），不加载 Google Fonts
