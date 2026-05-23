import aiosqlite

DDL_STATEMENTS = [
    """CREATE TABLE IF NOT EXISTS sessions (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL,
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS session_configs (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id      TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
        system_prompt   TEXT NOT NULL DEFAULT '你是一个AI助手，请尽你所能回答我的问题。',
        model_name      TEXT NOT NULL DEFAULT 'deepseek-chat',
        temperature     REAL NOT NULL DEFAULT 0.7,
        max_tokens      INTEGER NOT NULL DEFAULT 4096,
        enabled_tools   TEXT NOT NULL DEFAULT '[]',
        version         INTEGER NOT NULL DEFAULT 1,
        created_at      TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS global_settings (
        key         TEXT PRIMARY KEY,
        value       TEXT NOT NULL,
        updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    """CREATE TABLE IF NOT EXISTS chat_messages (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        role        TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'tool')),
        content     TEXT NOT NULL,
        tool_name   TEXT,
        token_count INTEGER DEFAULT 0,
        created_at  TEXT NOT NULL DEFAULT (datetime('now'))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_chat_messages_session ON chat_messages(session_id, created_at)",
]

SEED_SETTINGS = {
    "default_model": '"deepseek-chat"',
    "default_temperature": "0.7",
    "default_max_tokens": "4096",
    "default_system_prompt": '"你是一个AI助手，请尽你所能回答我的问题。"',
    "tools_scan_path": '"./custom_tools"',
}


async def init_database(db: aiosqlite.Connection) -> None:
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    for stmt in DDL_STATEMENTS:
        await db.execute(stmt)

    for key, value in SEED_SETTINGS.items():
        await db.execute(
            "INSERT OR IGNORE INTO global_settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    await db.commit()
