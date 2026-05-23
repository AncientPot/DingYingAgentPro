import uuid
import logging
from datetime import datetime, timezone
import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from backend.modules.config_manager import SessionConfigManager

logger = logging.getLogger(__name__)


class SessionStore:
    def __init__(
        self,
        db: aiosqlite.Connection,
        memory: AsyncSqliteSaver,
        config_manager: SessionConfigManager,
    ) -> None:
        self.db = db
        self.memory = memory
        self.config_manager = config_manager

    async def create_session(self, name: str) -> dict:
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        await self.db.execute("BEGIN")
        try:
            await self.db.execute(
                "INSERT INTO sessions (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, name, now, now),
            )
            await self.db.execute(
                """INSERT INTO session_configs (session_id, created_at, updated_at)
                   VALUES (?, ?, ?)""",
                (session_id, now, now),
            )
            await self.db.commit()
        except Exception:
            await self.db.execute("ROLLBACK")
            raise

        return {"id": session_id, "name": name, "created_at": now, "updated_at": now}

    async def get_session(self, session_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT id, name, created_at, updated_at FROM sessions WHERE id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()
        return (
            {"id": row[0], "name": row[1], "created_at": row[2], "updated_at": row[3]}
            if row
            else None
        )

    async def list_sessions(self) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT id, name, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "name": r[1], "created_at": r[2], "updated_at": r[3]}
            for r in rows
        ]

    async def delete_session(self, session_id: str) -> None:
        session = await self.get_session(session_id)
        if session is None:
            return

        await self.db.execute("BEGIN")
        try:
            await self.db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await self.db.commit()
        except Exception:
            await self.db.execute("ROLLBACK")
            raise

        try:
            await self.memory.adelete_thread(session_id)
        except Exception:
            logger.warning(
                "Failed to delete checkpoint thread for session %s", session_id, exc_info=True
            )

    async def get_messages(self, session_id: str, limit: int = 100) -> list[dict]:
        cursor = await self.db.execute(
            """SELECT id, session_id, role, content, tool_name, token_count, created_at
               FROM chat_messages
               WHERE session_id = ?
               ORDER BY created_at ASC
               LIMIT ?""",
            (session_id, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "session_id": r[1],
                "role": r[2],
                "content": r[3],
                "tool_name": r[4],
                "token_count": r[5],
                "created_at": r[6],
            }
            for r in rows
        ]

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_name: str | None = None,
        token_count: int = 0,
    ) -> None:
        await self.db.execute(
            """INSERT INTO chat_messages (session_id, role, content, tool_name, token_count)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, role, content, tool_name, token_count),
        )
        await self.db.commit()

    async def touch_session(self, session_id: str) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        await self.db.execute(
            "UPDATE sessions SET updated_at = ? WHERE id = ?", (now, session_id)
        )
        await self.db.commit()
