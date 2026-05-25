# agent — LangGraph 图引擎

## graph.py

构建并缓存 LangGraph 有状态图，是 Agent 的核心。

### State

```python
class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
```

### 缓存机制（epoch 版本计数）

两个全局计数器和一把锁：

- `_config_epoch` — 每次 `invalidate_graph()` 递增，表示"有新配置"
- `_graph_epoch` — 上次 `_build_graph()` 时的 epoch，表示"图所用的配置版本"
- `get_graph()` 比较两者：不等则重建

快速路径无锁检查 epoch（存在极低概率 TOCTOU 窗口，单用户场景可忽略）。

### _build_graph()

1. `get_config()` 读取最新配置
2. `load_tools()` 加载启用工具
3. `ChatDeepSeek(model, temperature, api_key...)` 创建 LLM
4. 定义 `dingyingagent` 节点（闭包捕获 system_prompt + tool_list）
5. 构建 `StateGraph` → compile 并返回

`system_prompt` 通过闭包捕获，每次重建图都会重新闭包最新值。

### 检查点

`get_checkpointer()` 返回 `SqliteSaver` 单例（SQLite `checkpoints.sqlite`）。图形编译时注入 `checkpointer=memory` 实现对话持久化。

### 配置变更联动

`on_config_changed(lambda _: invalidate_graph())` — 模块导入时自动注册回调。前端/API 修改配置 → `update_config` → 回调 → 图缓存失效 → 下次请求重建。
