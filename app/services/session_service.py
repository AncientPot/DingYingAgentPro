"""
会话管理服务。

负责会话的创建、查询、删除，维护 SQLite 检查点与 JSON 映射的一致性。
封装了原 CLI 程序中的会话管理逻辑，对外提供同步 API。
"""

import json
import os
import uuid
from typing import Optional

SESSION_NAMESPACE = uuid.UUID("12345678-1234-5678-1234-567812345678")
SESSION_MAP_FILE = "sessions.json"


class SessionService:
    """会话管理服务，封装 SQLite + JSON 的会话持久化逻辑。"""

    def __init__(self, checkpointer):
        """
        Args:
            checkpointer: LangGraph 的 SqliteSaver 实例。
        """
        self._checkpointer = checkpointer
        self._name_to_tid: dict[str, str] = {}
        self._db_tids: set[str] = set()
        self._loaded = False

    def _ensure_loaded(self):
        """懒加载：首次使用时从 SQLite 和 JSON 加载数据。"""
        if self._loaded:
            return

        # 从 SQLite 加载所有 thread_id
        for checkpoint_tuple in self._checkpointer.list(None):
            tid = checkpoint_tuple.config["configurable"]["thread_id"]
            self._db_tids.add(tid)

        # 从 JSON 加载名称映射
        if os.path.exists(SESSION_MAP_FILE):
            with open(SESSION_MAP_FILE, "r", encoding="utf-8") as f:
                self._name_to_tid = json.load(f)

        # 同步一致性
        self._sync()
        self._loaded = True

    def _sync(self):
        """同步数据库与 JSON 会话映射。"""
        json_tids = set(self._name_to_tid.values())

        if self._db_tids > json_tids:
            # 数据库中有孤儿记录，删除
            for tid in self._db_tids - json_tids:
                self._checkpointer.delete_thread(tid)
                self._db_tids.discard(tid)

        elif self._db_tids < json_tids:
            # JSON 中有孤儿记录，移除
            for tid in json_tids - self._db_tids:
                name_to_remove = next(k for k, v in self._name_to_tid.items() if v == tid)
                del self._name_to_tid[name_to_remove]
            self._save_json()

    def _save_json(self):
        """持久化名称映射到 JSON。"""
        with open(SESSION_MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(self._name_to_tid, f, ensure_ascii=False, indent=2)

    # ── 公开 API ──

    def list_sessions(self) -> list[dict]:
        """列出所有会话。"""
        self._ensure_loaded()
        return [
            {"name": name, "thread_id": tid}
            for name, tid in sorted(self._name_to_tid.items())
        ]

    def get_or_create_session(self, name: str) -> dict:
        """
        获取或创建会话。不存在则自动创建。

        Returns:
            dict: {"name": str, "thread_id": str, "config": dict, "created": bool}
        """
        self._ensure_loaded()

        if name in self._name_to_tid:
            tid = self._name_to_tid[name]
            created = False
        else:
            tid = str(uuid.uuid5(SESSION_NAMESPACE, name))
            self._name_to_tid[name] = tid
            self._db_tids.add(tid)
            self._save_json()
            created = True

        return {
            "name": name,
            "thread_id": tid,
            "config": {"configurable": {"thread_id": tid}},
            "created": created,
        }

    def delete_session(self, name: str) -> bool:
        """
        删除指定会话。

        Returns:
            bool: 是否成功删除（会话不存在返回 False）。
        """
        self._ensure_loaded()

        if name not in self._name_to_tid:
            return False

        tid = self._name_to_tid[name]
        self._checkpointer.delete_thread(tid)
        self._db_tids.discard(tid)
        del self._name_to_tid[name]
        self._save_json()
        return True
