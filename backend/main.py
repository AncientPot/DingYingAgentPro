import json
import os
from contextlib import asynccontextmanager
import aiosqlite
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_database
from backend.api.router import api_router
from backend.modules.config_manager import SessionConfigManager, GlobalSettingsManager
from backend.modules.tool_registry import ToolRegistry
from backend.modules.llm_provider import LLMProvider
from backend.modules.session_store import SessionStore
from backend.modules.agent_core import AgentCore
from backend.config import settings
from langchain_tavily import TavilySearch


async def migrate_sessions_json(app: FastAPI) -> None:
    json_path = "sessions.json"
    if not os.path.exists(json_path):
        return

    cursor = await app.state.db.execute("SELECT COUNT(*) FROM sessions")
    row = await cursor.fetchone()
    if row and row[0] > 0:
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            name_to_tid = json.load(f)
    except Exception:
        return

    for name, tid in name_to_tid.items():
        try:
            await app.state.db.execute(
                "INSERT INTO sessions (id, name) VALUES (?, ?)", (tid, name)
            )
            await app.state.db.execute(
                "INSERT INTO session_configs (session_id) VALUES (?)", (tid,)
            )
        except Exception:
            pass

    await app.state.db.commit()
    try:
        os.rename(json_path, json_path + ".migrated")
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()

    app.state.db = await aiosqlite.connect("app.db")
    app.state.db.row_factory = aiosqlite.Row
    await init_database(app.state.db)

    app.state.config_manager = SessionConfigManager(app.state.db)
    app.state.global_settings = GlobalSettingsManager(app.state.db)

    app.state.llm_provider = LLMProvider()

    scan_path = await app.state.global_settings.get("tools_scan_path")
    app.state.tool_registry = ToolRegistry(scan_path=scan_path or "./custom_tools")
    app.state.tool_registry.register_builtin(TavilySearch(max_results=2))
    app.state.tool_registry.scan_and_load()

    app.state.session_store = SessionStore(
        app.state.db, None, app.state.config_manager
    )

    await migrate_sessions_json(app)

    app.state.agent_core = AgentCore(
        app.state.tool_registry, app.state.llm_provider
    )
    await app.state.agent_core.initialize()

    app.state.session_store.memory = app.state.agent_core.memory

    yield

    await app.state.db.close()
    if app.state.agent_core.memory is not None:
        # aiosqlite connection is managed by AgentCore; close it via the saver
        pass


app = FastAPI(
    title="DingYingAgentPro",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "name": "DingYingAgentPro",
        "version": "0.2.0",
        "docs": "/docs",
        "api_prefix": "/api/v1",
        "endpoints": {
            "sessions": "/api/v1/sessions",
            "chat": "/api/v1/chat/stream",
            "tools": "/api/v1/tools",
            "models": "/api/v1/models",
            "settings": "/api/v1/settings",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


app.include_router(api_router)
