import json
from datetime import datetime, timezone
import aiosqlite


class SessionConfigManager:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def get_config(self, session_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM session_configs WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return self._row_to_dict(row)

    async def create_config(self, session_id: str) -> dict:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        await self.db.execute(
            """INSERT INTO session_configs (session_id, created_at, updated_at)
               VALUES (?, ?, ?)""",
            (session_id, now, now),
        )
        await self.db.commit()
        config = await self.get_config(session_id)
        assert config is not None
        return config

    async def update_config(
        self, session_id: str, updates: dict, expected_version: int
    ) -> dict:
        current = await self.get_config(session_id)
        if current is None:
            raise ValueError(f"Config not found for session {session_id}")
        if current["version"] != expected_version:
            raise VersionConflictError(
                f"Version mismatch: expected {expected_version}, "
                f"current {current['version']}"
            )

        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        set_clauses = ["updated_at = ?", "version = ?"]
        params: list = [now, expected_version + 1]

        for field in ("system_prompt", "model_name", "temperature", "max_tokens"):
            if field in updates and updates[field] is not None:
                set_clauses.append(f"{field} = ?")
                params.append(updates[field])

        if "enabled_tools" in updates and updates["enabled_tools"] is not None:
            set_clauses.append("enabled_tools = ?")
            params.append(json.dumps(updates["enabled_tools"], ensure_ascii=False))

        params.append(session_id)
        params.append(expected_version)
        await self.db.execute(
            f"UPDATE session_configs SET {', '.join(set_clauses)} WHERE session_id = ? AND version = ?",
            params,
        )
        await self.db.commit()
        return await self.get_config(session_id)

    async def delete_config(self, session_id: str) -> None:
        await self.db.execute(
            "DELETE FROM session_configs WHERE session_id = ?", (session_id,)
        )
        await self.db.commit()

    async def get_effective_config(self, session_id: str) -> dict:
        config = await self.get_config(session_id)
        if config is None:
            config = {}

        globals_map = await self._get_all_globals()

        def _fallback(key: str, default):
            if key in config and config[key] is not None:
                return config[key]
            if key in globals_map:
                return globals_map[key]
            default_key = f"default_{key}"
            if default_key in globals_map:
                return globals_map[default_key]
            return default

        tools_raw = config.get("enabled_tools", "[]")
        if isinstance(tools_raw, str):
            enabled_tools = json.loads(tools_raw)
        else:
            enabled_tools = tools_raw

        return {
            "system_prompt": _fallback("system_prompt", "你是一个AI助手，请尽你所能回答我的问题。"),
            "model_name": _fallback("model_name", "deepseek-chat"),
            "temperature": float(_fallback("temperature", 0.7)),
            "max_tokens": int(_fallback("max_tokens", 4096)),
            "enabled_tools": enabled_tools,
        }

    async def _get_all_globals(self) -> dict:
        cursor = await self.db.execute("SELECT key, value FROM global_settings")
        rows = await cursor.fetchall()
        result = {}
        for row in rows:
            try:
                result[row[0]] = json.loads(row[1])
            except (json.JSONDecodeError, TypeError):
                result[row[0]] = row[1]
        return result

    @staticmethod
    def _row_to_dict(row) -> dict:
        return {
            "id": row[0],
            "session_id": row[1],
            "system_prompt": row[2],
            "model_name": row[3],
            "temperature": row[4],
            "max_tokens": row[5],
            "enabled_tools": json.loads(row[6]) if isinstance(row[6], str) else row[6],
            "version": row[7],
            "created_at": row[8],
            "updated_at": row[9],
        }


class GlobalSettingsManager:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def get_all(self) -> dict:
        cursor = await self.db.execute("SELECT key, value FROM global_settings")
        rows = await cursor.fetchall()
        result = {}
        for row in rows:
            try:
                result[row[0]] = json.loads(row[1])
            except (json.JSONDecodeError, TypeError):
                result[row[0]] = row[1]
        return result

    async def get(self, key: str):
        cursor = await self.db.execute(
            "SELECT value FROM global_settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        try:
            return json.loads(row[0])
        except (json.JSONDecodeError, TypeError):
            return row[0]

    async def set(self, key: str, value) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        value_str = json.dumps(value, ensure_ascii=False)
        await self.db.execute(
            """INSERT INTO global_settings (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value = excluded.value,
                                             updated_at = excluded.updated_at""",
            (key, value_str, now),
        )
        await self.db.commit()


class VersionConflictError(Exception):
    pass
