# core — 运行时配置管理

## config.py

配置系统的唯一入口，所有模块通过 `get_config()` 读取配置。

### 优先级

`config.json` > 环境变量 > `_DEFAULT_CONFIG`

### 关键函数

| 函数 | 用途 |
|------|------|
| `get_config()` | 读取当前配置（有锁缓存，首次后零开销） |
| `get_masked_config()` | 同上，但 `api_key` 中间位替换为 `*` |
| `update_config(partial)` | 部分更新 → 写 `config.json` → 通知回调 |
| `on_config_changed(callback)` | 注册变更回调 |
| `reset_cache()` | 强制下次重载（删除 config.json 后使用） |

### 锁

`threading.Lock()` 保护 `_config_cache`。`get_config()` 两次检查（无锁缓存读取 + 有锁加载），`update_config()` 全程持锁直到写完回调前释放。

### 变更通知

`update_config()` 释放锁后遍历 `_on_config_changed` 调用回调。当前注册的回调：
- `agent/graph.py`: `invalidate_graph()` 递增 epoch 触发图重建
- `tools/tavily_search.py`: 重置搜索实例缓存

### 默认配置项

```python
_DEFAULT_CONFIG = {
    "model_name": "deepseek-chat",
    "temperature": 0.7,
    "system_prompt": "...",
    "max_search_results": 2,
    "enabled_tools": ["calculator", "netease_cloud_music", "tavily_search", "md_file_manager"],
}
```
