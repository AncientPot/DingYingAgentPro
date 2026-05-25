# tools — 插件式工具系统

## 设计原则

`app/tools/` 下每个 `.py` 文件是一个独立工具。**增删 .py 即增删工具，无需重启服务**。

## 加载器 (__init__.py)

### load_tools(enabled_tools=None)

- `pkgutil.iter_modules` 扫描目录
- `importlib.import_module` 动态加载
- 调用 `module.get_tool()` 获取 LangChain BaseTool 实例
- 导入失败时静默跳过（平台不兼容/缺依赖）
- `enabled_tools=None` 加载全部，传入列表则按列表加载

### list_available_tools(enabled_tools=None)

返回工具的元信息列表，每个含 `name`, `display_name`, `description`, `enabled`。

注意：`enabled_tools=[]`（空列表）与 `None`（全部启用）的行为不同——使用 `is not None` 检查。

### test_tool(module_name)

调用模块的 `test_tool()` 自检函数，未提供则验证 `get_tool()` 可调用。

返回 `{"ok": bool, "message": str, "details": str}`。

## 工具开发规范

每个工具模块需暴露：

| 函数 | 必须 | 说明 |
|------|:--:|------|
| `get_tool()` | ✅ | 返回 LangChain BaseTool 实例 |
| `test_tool()` | 推荐 | 自检，返回 `{"ok": bool, "message": str, "details": str}` |

## 现有工具

| 模块 | 工具名 | 功能 |
|------|--------|------|
| `calculator.py` | calculator | 加减乘运算 |
| `tavily_search.py` | tavily_search | 联网搜索（需 TAVILY_API_KEY） |
| `netease_cloud_music.py` | control_netease_cloud_music | 网易云音乐桌面控制（仅 Windows） |
| `md_file_manager.py` | file_manager | 创建文件夹/创建读写备份恢复 .md 文件 |
| `game.py` | game_center | 进入/退出游戏模式 |

### 游戏工具（game_tools/ 子目录）

独立于标准工具，仅在游戏模式设置中可见，单选启用。

- `list_game_tools()` — 发现 game_tools/ 下所有非 `_` 前缀模块
- `load_game_tool(name)` — 加载指定游戏工具
- 每个游戏工具需 `get_meta()`（元信息）+ `get_tool()`（工具实例）

## 添加新工具

1. 在 `app/tools/` 下新建 `.py` 文件
2. 实现 `get_tool()`（返回 `@tool` 装饰的函数）
3. 可选实现 `test_tool()` 自检
4. 将模块名加入 `core/config.py` 的 `enabled_tools` 默认列表
5. 重启服务即可使用
