import importlib.util
import sys
from pathlib import Path
from langchain_core.tools import BaseTool
from backend.schemas.tool import ToolMetaResponse

HIGH_TRUST_MODULES = {"pywinauto", "pywin32", "win32gui", "win32process", "subprocess"}


class ToolRegistry:
    def __init__(self, scan_path: str = "./custom_tools") -> None:
        self.scan_path = Path(scan_path)
        self._tools: dict[str, BaseTool] = {}
        self._builtin_tools: dict[str, BaseTool] = {}
        self._metadata: dict[str, dict] = {}
        self._disabled: set[str] = set()

    def register_builtin(self, tool: BaseTool) -> None:
        self._builtin_tools[tool.name] = tool
        self._metadata[tool.name] = {
            "name": tool.name,
            "description": tool.description,
            "source_file": "<builtin>",
            "trust_level": "low",
            "is_active": True,
        }

    def scan_and_load(self) -> None:
        if not self.scan_path.exists():
            return

        for py_file in sorted(self.scan_path.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            self._load_file(py_file)

    def reload(self) -> dict:
        old_custom = set(self._tools.keys()) - set(self._builtin_tools.keys())

        for name in list(old_custom):
            del self._tools[name]
            self._metadata.pop(name, None)

        self._disabled.clear()
        self.scan_and_load()

        new_custom = set(self._tools.keys()) - set(self._builtin_tools.keys())
        return {
            "added": sorted(new_custom - old_custom),
            "removed": sorted(old_custom - new_custom),
            "unchanged": sorted(
                set(self._builtin_tools.keys()) | (old_custom & new_custom)
            ),
        }

    def get_all_tools(self) -> list[BaseTool]:
        all_tools = list(self._builtin_tools.values())
        for name, tool in self._tools.items():
            if name not in self._builtin_tools and name not in self._disabled:
                all_tools.append(tool)
        return all_tools

    def get_tools_by_names(self, names: list[str]) -> list[BaseTool]:
        result = []
        for name in names:
            if name in self._disabled:
                continue
            tool = self._tools.get(name) or self._builtin_tools.get(name)
            if tool is not None:
                result.append(tool)
        return result

    def get_all_metadata(self) -> list[dict]:
        result = []
        for meta in self._metadata.values():
            meta_copy = dict(meta)
            meta_copy["is_active"] = meta_copy["name"] not in self._disabled
            result.append(meta_copy)
        return result

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name) or self._builtin_tools.get(name)

    def enable_tool(self, name: str) -> bool:
        if name in self._disabled:
            self._disabled.discard(name)
            return True
        return False

    def disable_tool(self, name: str) -> bool:
        if name in self._tools or name in self._builtin_tools:
            self._disabled.add(name)
            return True
        return False

    def _load_file(self, py_file: Path) -> None:
        module_name = py_file.stem
        full_name = f"custom_tools.{module_name}"

        # Remove from cache to enable hot-reload
        if full_name in sys.modules:
            del sys.modules[full_name]

        spec = importlib.util.spec_from_file_location(full_name, py_file)
        if spec is None or spec.loader is None:
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_name] = module
        spec.loader.exec_module(module)

        trust_level = self._detect_trust_level(py_file)

        for attr_name in dir(module):
            obj = getattr(module, attr_name)
            if isinstance(obj, BaseTool):
                self._tools[obj.name] = obj
                self._metadata[obj.name] = {
                    "name": obj.name,
                    "description": obj.description,
                    "source_file": str(py_file),
                    "trust_level": trust_level,
                    "is_active": True,
                }

    def _detect_trust_level(self, py_file: Path) -> str:
        try:
            source = py_file.read_text(encoding="utf-8")
            for mod in HIGH_TRUST_MODULES:
                if mod in source:
                    return "high"
        except Exception:
            pass
        return "medium"
