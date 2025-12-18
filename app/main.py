import logging
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
import httpx

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AnyMessage

from core.config import get_settings
from core.logging import setup_logging
from services.chatbot import GRAPH_APP

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# Simple in-memory session store (Refactored)
# -------------------------------------------------------------------

class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, List[AnyMessage]] = {}

    def get_history(self, session_id: str) -> List[AnyMessage]:
        return self._sessions.setdefault(session_id, [])

    def set_history(self, session_id: str, history: List[AnyMessage]) -> None:
        self._sessions[session_id] = history

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> List[str]:
        return list(self._sessions.keys())

store = SessionStore()
DEFAULT_SESSION_ID = "dev"

# -------------------------------------------------------------------
# Lifecycle
# -------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Startup: Warming LLM...")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": "ping",
                    "stream": False,
                },
                timeout=60.0
            )
            resp.raise_for_status()
        logger.info("Startup: LLM ready.")
    except Exception as e:
        logger.warning(f"Startup: LLM warm-up failed: {e}")
    
    yield
    # Shutdown
    logger.info("Shutdown: cleaning up.")

# -------------------------------------------------------------------
# API Models
# -------------------------------------------------------------------

class ChatIn(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(None, description="Optional session id.")

class ChatOut(BaseModel):
    reply: str
    session_id: str
    history: List[Dict[str, str]]
    debug_info: Optional[Dict[str, Any]] = None

# -------------------------------------------------------------------
# Helper
# -------------------------------------------------------------------

def _serialize_history(messages: List[AnyMessage]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for m in messages:
        role = getattr(m, "type", "unknown")
        content = str(m.content)
        if role == "ai":
            role = "assistant"
        elif role == "human":
            role = "user"
        out.append({"role": role, "content": content})
    return out

# -------------------------------------------------------------------
# App Factory
# -------------------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

@app.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn) -> ChatOut:
    session_id = body.session_id or DEFAULT_SESSION_ID

    history = store.get_history(session_id)
    history.append(HumanMessage(content=body.message))

    # Invoke graph (async)
    result = await GRAPH_APP.ainvoke({"messages": history})
    ai_msg = result["messages"][-1]

    history.append(ai_msg)
    store.set_history(session_id, history)
    
    # Extract debug info from graph state
    debug_info = {
        "intent": result.get("intent"),
        "search_query": result.get("search_query"),
        "filters": {
            "genre": result.get("genre"),
            "sort_by": result.get("sort_by"),
            "platform": result.get("platform"),
        },
        # Truncate context if too long, or send full depending on usage
        "igdb_context_preview": (result.get("igdb_context") or "")[:500] + "..." if result.get("igdb_context") else None
    }

    return ChatOut(
        reply=str(ai_msg.content),
        session_id=session_id,
        history=_serialize_history(history),
        debug_info=debug_info
    )

@app.post("/reset")
async def reset_session(session_id: Optional[str] = None) -> Dict[str, str]:
    sid = session_id or DEFAULT_SESSION_ID
    store.reset(sid)
    return {"status": "ok", "session_id": sid}

@app.get("/sessions")
async def list_sessions() -> Dict[str, List[str]]:
    return {"sessions": store.list_sessions()}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
