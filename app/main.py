"""
DingYingAgentPro FastAPI 入口。

启动方式:
    python -m app.main
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.graph import get_checkpointer
from app.services.session_service import SessionService

# ── 加载环境变量 ──
load_dotenv()

# ── 日志 ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── 创建 FastAPI 应用 ──

app = FastAPI(
    title="DingYingAgentPro API",
    description="基于 LangGraph 的智能助手后端，支持插件式工具、会话管理、流式对话。",
    version="0.1.0",
)

# CORS —— 允许前端开发跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 启动事件：初始化服务 ──

@app.on_event("startup")
def on_startup():
    """应用启动时初始化 SessionService 并预热 Agent 图。"""
    logger.info("正在初始化服务...")

    # 重置游戏状态（防止上次运行残留）
    from app.services.game_service import set_game_mode
    set_game_mode(False)
    logger.info("游戏状态已重置")

    # 初始化会话服务（复用 Agent 的 SQLite 检查点）
    checkpointer = get_checkpointer()
    app.state.session_service = SessionService(checkpointer)
    logger.info("SessionService 已就绪")

    # 预热 Agent 图（首次构建可能较慢，提前完成避免首个请求超时）
    from app.agent.graph import get_graph
    get_graph()
    logger.info("Agent 图已就绪")

    logger.info("服务启动完成，等待请求...")


# ── 注册路由 ──

from app.api.chat import router as chat_router
from app.api.sessions import router as sessions_router
from app.api.config import router as config_router
from app.api.tools import router as tools_router
from app.api.game import router as game_router

app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(config_router)
app.include_router(tools_router)
app.include_router(game_router)


# ── 健康检查 ──

@app.get("/api/health", tags=["health"])
def health_check():
    """服务健康检查。"""
    return {"status": "ok", "service": "DingYingAgentPro"}


# ── 根路径重定向 ──

@app.get("/", tags=["root"])
def root():
    """API 根路径，返回基本信息。"""
    return {
        "service": "DingYingAgentPro API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/health",
    }
