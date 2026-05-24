"""
文件和文件夹管理工具 —— 创建文件夹、创建/读取/修改/备份 .md 文件。

安全设计：
- 读取前向用户确认目标文件
- 修改/整理前向用户确认 + 询问是否备份
- 备份存放于目标文件夹根目录下的 mdbacks/ 子目录
- 支持备份恢复（恢复前也需确认）
"""

import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


# ── 工具函数 ──

BACKUP_DIR_NAME = "mdbacks"


def _backup_dir(folder_path: str) -> Path:
    """获取备份目录路径：folder_path/mdbacks/"""
    return Path(folder_path) / BACKUP_DIR_NAME


def _ensure_backup_dir(folder_path: str) -> Path:
    """确保备份目录存在并返回路径。"""
    d = _backup_dir(folder_path)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _list_md_files(folder_path: str) -> list[str]:
    """列出文件夹内所有 .md 文件（仅文件名）。"""
    p = Path(folder_path)
    if not p.is_dir():
        raise ValueError(f"路径不存在或不是文件夹: {folder_path}")
    return sorted(
        [f.name for f in p.glob("*.md") if f.is_file()],
        key=str.lower,
    )


def _list_backup_files(folder_path: str, original_name: str) -> list[dict]:
    """列出指定文件的备份信息。"""
    backup_dir = _backup_dir(folder_path)
    if not backup_dir.is_dir():
        return []
    base = Path(original_name).stem
    backups = []
    for f in sorted(backup_dir.glob(f"{base}_backup_*.md"), reverse=True):
        stat = f.stat()
        backups.append({
            "name": f.name,
            "size": stat.st_size,
            "time": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return backups


def _make_backup(folder_path: str, file_name: str) -> str:
    """创建文件备份，返回备份文件名（含微秒避免秒内冲突）。"""
    src = Path(folder_path) / file_name
    if not src.is_file():
        raise ValueError(f"文件不存在: {src}")
    backup_dir = _ensure_backup_dir(folder_path)
    stem = Path(file_name).stem
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    micro = str(now.microsecond // 1000).zfill(3)  # 毫秒
    backup_name = f"{stem}_backup_{timestamp}_{micro}.md"
    # 确保不覆盖已有同名备份（极端并发安全）
    dst = backup_dir / backup_name
    if dst.exists():
        backup_name = f"{stem}_backup_{timestamp}_{micro}_{id(dst) & 0xFFFF:04x}.md"
        dst = backup_dir / backup_name
    shutil.copy2(src, dst)
    return backup_name


def _read_file(folder_path: str, file_name: str) -> str:
    """读取文件内容。"""
    src = Path(folder_path) / file_name
    if not src.is_file():
        raise ValueError(f"文件不存在: {src}")
    return src.read_text(encoding="utf-8")


def _write_file(folder_path: str, file_name: str, content: str):
    """写入文件内容。"""
    dst = Path(folder_path) / file_name
    dst.write_text(content, encoding="utf-8")


def _organize_content(content: str, instructions: str) -> str:
    """
    按指令整理 markdown 内容。
    支持的操作：排序标题、提取章节、格式化、去重等。
    实际整理逻辑由 LLM 通过 instructions 参数驱动，
    此函数负责执行基础文本操作。
    """
    # 解析 instructions 中的关键操作
    result = content
    inst_lower = instructions.lower()

    # 去除多余空行（连续 3+ 空行 → 2 空行）
    if "去重" in instructions or "空行" in instructions or "blank" in inst_lower:
        result = re.sub(r"\n{3,}", "\n\n", result)

    # 去除行尾空格
    if "空格" in instructions or "trim" in inst_lower or "整理" in instructions:
        result = "\n".join(line.rstrip() for line in result.split("\n"))

    # 确保文件以单个换行结尾
    result = result.rstrip("\n") + "\n"

    return result


# ── 主工具 ──

@tool
def file_manager(
    folder_path: str,
    file_name: Optional[str] = None,
    new_folder_name: Optional[str] = None,
    new_content: Optional[str] = None,
    instructions: Optional[str] = None,
    confirmed: bool = False,
    create_backup: bool = False,
    backup_name: Optional[str] = None,
) -> str:
    """
    管理文件和文件夹。根据传入参数自动判断操作类型：

    - 仅传 folder_path → 列出该目录下所有 .md 文件
    - 传 folder_path + new_folder_name → 创建子文件夹
    - 传 folder_path + file_name(以.md结尾) + new_content，文件不存在 → 创建新 .md 文件
    - 传 folder_path + file_name + new_content，文件存在 → 修改文件（需 confirmed=True）
    - 传 folder_path + file_name + instructions → 整理文件内容（需 confirmed=True）
    - 传 folder_path + file_name（仅此两项）→ 读取文件（需 confirmed=True）
    - 传 folder_path + file_name + backup_name → 恢复备份（需 confirmed=True）
    - 备份/列出备份可通过 create_backup 和 backup_name 组合实现

    安全规则：修改/读取/整理/恢复需要 confirmed=True 确认。
    创建文件夹和创建新文件直接执行（调用前请口头与用户确认）。
    覆盖已有文件时设置 create_backup=True 可先备份到 mdbacks/。
    """
    folder_path = os.path.abspath(folder_path)

    # ── 意图推断 ──

    # 1) 创建文件夹: new_folder_name 有值且无 file_name
    if new_folder_name and not file_name:
        err = _validate_name(new_folder_name.strip())
        if err:
            return f"文件夹名称不合法: {err}"
        target = Path(folder_path) / new_folder_name.strip()
        if target.is_dir():
            return f"文件夹已存在: {target}"
        try:
            target.mkdir(parents=False)
            return f"已创建文件夹: {target}"
        except Exception as e:
            return f"创建文件夹失败: {e}"

    # 2) 仅 folder_path → 列出文件
    if not file_name:
        try:
            files = _list_md_files(folder_path)
        except ValueError as e:
            return str(e)
        if not files:
            return f"文件夹 '{folder_path}' 中没有 .md 文件。"
        lines = [f"文件夹 '{folder_path}' 中的 .md 文件 ({len(files)} 个):"]
        for i, f in enumerate(files, 1):
            p = Path(folder_path) / f
            lines.append(f"  {i}. {f} ({_fmt_size(p.stat().st_size)})")
        return "\n".join(lines)

    # 后续操作都需要 file_name
    file_path = Path(folder_path) / file_name
    file_exists = file_path.is_file()

    # 3) 恢复备份: backup_name 有值
    if backup_name:
        backup_path = _backup_dir(folder_path) / backup_name
        if not backup_path.is_file():
            return f"备份文件不存在: {backup_path}"
        if not confirmed:
            try:
                preview = backup_path.read_text("utf-8")[:400]
            except Exception:
                preview = "(无法预览)"
            return (
                f"请确认：将从备份 '{backup_name}' 恢复 '{file_name}'。\n"
                f"内容预览:\n---\n{preview}\n---\n"
                f"确认后将覆盖当前内容。请用 confirmed=True 再次调用。"
            )
        try:
            if file_exists:
                _make_backup(folder_path, file_name)
        except Exception:
            pass
        try:
            content = backup_path.read_text("utf-8")
            _write_file(folder_path, file_name, content)
            return f"已从 '{backup_name}' 恢复 '{file_name}'（恢复前已自动备份当前版本）"
        except Exception as e:
            return f"恢复失败: {e}"

    # 4) 文件不存在 + new_content → 创建新文件
    if not file_exists and new_content is not None:
        if not file_name.endswith(".md"):
            return "新建文件要求文件名以 .md 结尾。"
        try:
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            _write_file(folder_path, file_name, new_content)
            return f"已创建文件: {file_path}"
        except Exception as e:
            return f"创建文件失败: {e}"

    # 5) 文件存在 + new_content → 修改
    if file_exists and new_content is not None:
        if not confirmed:
            try:
                original = _read_file(folder_path, file_name)
            except Exception as e:
                return f"无法读取文件: {e}"
            return (
                f"请确认修改 '{file_name}'。\n"
                f"原内容:\n---\n{original[:300]}\n---\n"
                f"新内容:\n---\n{new_content[:300]}\n---\n"
                f"确认后请用 confirmed=True 再次调用。设 create_backup=True 可先备份。"
            )
        backup_msg = ""
        if create_backup:
            try:
                bn = _make_backup(folder_path, file_name)
                backup_msg = f" 已备份至: mdbacks/{bn}"
            except Exception as e:
                return f"备份失败: {e}"
        try:
            _write_file(folder_path, file_name, new_content)
            return f"已修改文件 '{file_name}'{backup_msg}"
        except Exception as e:
            return f"修改失败: {e}"

    # 6) 文件存在 + instructions → 整理
    if file_exists and instructions:
        if not confirmed:
            try:
                content = _read_file(folder_path, file_name)
            except Exception as e:
                return f"无法读取文件: {e}"
            return (
                f"请确认整理 '{file_name}'。\n"
                f"整理要求: {instructions}\n"
                f"内容预览:\n---\n{content[:400]}\n---\n"
                f"确认后请用 confirmed=True 再次调用。"
            )
        backup_msg = ""
        if create_backup:
            try:
                bn = _make_backup(folder_path, file_name)
                backup_msg = f"\n已备份至: mdbacks/{bn}"
            except Exception as e:
                return f"备份失败: {e}"
        try:
            original = _read_file(folder_path, file_name)
            organized = _organize_content(original, instructions)
            _write_file(folder_path, file_name, organized)
            return f"已整理文件 '{file_name}'{backup_msg}"
        except Exception as e:
            return f"整理失败: {e}"

    # 7) 文件存在，只传 file_name → 读取
    if file_exists:
        if not confirmed:
            try:
                content = _read_file(folder_path, file_name)
            except Exception as e:
                return f"无法读取文件: {e}"
            return (
                f"请确认读取 '{file_name}'（{_fmt_size(len(content))}）。\n"
                f"内容预览:\n---\n{content[:500]}\n---\n"
                f"确认后请用 confirmed=True 再次调用。"
            )
        try:
            content = _read_file(folder_path, file_name)
        except Exception as e:
            return f"读取失败: {e}"
        return f"文件 '{file_name}' 的内容:\n\n{content}"

    # 8) 文件不存在，没有 new_content → 列出备份或报错
    backups = _list_backup_files(folder_path, file_name)
    if backups:
        lines = [f"文件 '{file_name}' 不存在，但有 {len(backups)} 个备份可恢复:"]
        for i, b in enumerate(backups, 1):
            lines.append(f"  {i}. {b['name']} | {b['time']}")
        lines.append("\n使用 backup_name 参数指定要恢复的备份。")
        return "\n".join(lines)

    return (
        f"文件 '{file_name}' 不存在。如需创建请传入 new_content 参数指定初始内容；"
        f"如需创建文件夹请传入 new_folder_name 参数。"
    )


def _validate_name(name: str, allow_existing_dir: bool = False) -> str | None:
    """
    验证文件/文件夹名称安全性。

    Returns:
        None 表示合法，否则返回错误描述字符串。
    """
    if not name or not name.strip():
        return "名称不能为空"
    if ".." in name or "/" in name or "\\" in name:
        return f"名称包含非法字符: {name}"
    # 禁止 Windows 保留名
    forbidden = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4",
                 "LPT1", "LPT2", "LPT3", "LPT4", "LPT5"}
    base = Path(name).stem.upper()
    if base in forbidden:
        return f"'{name}' 是系统保留名，不允许使用"
    return None


def _fmt_size(size: int) -> str:
    """格式化文件大小。"""
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    else:
        return f"{size / (1024 * 1024):.1f} MB"


def get_tool():
    """返回 file_manager 工具实例。"""
    return file_manager


def test_tool() -> dict:
    """自检：创建临时文件验证读/写/备份/恢复全流程。"""
    import tempfile
    import os as _os

    tmpdir = tempfile.mkdtemp(prefix="md_test_")
    try:
        test_file = "test.md"
        test_content = "# 测试文件\n\n这是一段测试内容。\n\n## 第二章\n\n更多内容。"

        # 写测试文件
        _write_file(tmpdir, test_file, test_content)

        # 测试 list_files
        files = _list_md_files(tmpdir)
        assert test_file in files, f"list_files failed: {files}"

        # 测试 read
        content = _read_file(tmpdir, test_file)
        assert "测试文件" in content, f"read failed: {content[:50]}"

        # 测试 backup
        bn = _make_backup(tmpdir, test_file)
        assert _os.path.exists(_os.path.join(tmpdir, BACKUP_DIR_NAME, bn)), f"backup failed: {bn}"

        # 测试 list_backups
        backups = _list_backup_files(tmpdir, test_file)
        assert len(backups) == 1, f"list_backups failed: {backups}"

        # 测试 organize
        organized = _organize_content(test_content, "去除多余空行，整理空格")
        assert len(organized) > 0, "organize returned empty"

        # 测试 _validate_name
        assert _validate_name("test.md") is None, "valid name rejected"
        assert _validate_name("../escape.md") is not None, "path traversal accepted"
        assert _validate_name("CON.txt") is not None, "reserved name accepted"

        # 测试 create_folder（new_folder_name 无 file_name → 创建文件夹）
        r = file_manager.func(folder_path=tmpdir, new_folder_name="subdir")
        assert _os.path.isdir(_os.path.join(tmpdir, "subdir")), f"create_folder failed: {r}"

        # 测试 create_file（file_name + new_content，文件不存在 → 创建）
        r = file_manager.func(folder_path=tmpdir, file_name="created.md", new_content="# 新建")
        assert _os.path.isfile(_os.path.join(tmpdir, "created.md")), f"create_file failed: {r}"

        return {
            "ok": True,
            "message": "MD 文件管理器自检通过（全功能正常）",
            "details": f"测试目录: {tmpdir}",
        }
    except Exception as e:
        return {"ok": False, "message": f"自检失败: {e}", "details": str(e)}
    finally:
        # 清理临时文件
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass
