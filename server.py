from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AnyMessage, SystemMessage

from chatbot_graph import GRAPH_APP, DUMMY_SYSTEM


# ---------------- Session store ----------------

class SessionStore:
    def __init__(self) -> None:
        self._sessions: Dict[str, List[AnyMessage]] = {}

    def get_history(self, session_id: str) -> List[AnyMessage]:
        history = self._sessions.setdefault(session_id, [])
        if not history:
            # seed with system prompt for new sessions
            history.append(SystemMessage(content=DUMMY_SYSTEM))
        return history

    def reset(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list_sessions(self) -> List[str]:
        return list(self._sessions.keys())


store = SessionStore()
DEFAULT_SESSION_ID = "dev"


# ---------------- Models & app ----------------

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatOut(BaseModel):
    reply: str
    session_id: str
    history: List[Dict[str, Any]] = Field(default_factory=list)

class ResetIn(BaseModel):
    session_id: Optional[str] = None

app = FastAPI(title="Local LangGraph Chat (Ollama + uv)")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    sid = body.session_id or DEFAULT_SESSION_ID
    history = store.get_history(sid)

    # full history for LLM
    history.append(HumanMessage(content=body.message))
    result = GRAPH_APP.invoke({"messages": history})
    ai_msg = result["messages"][-1]
    history.append(ai_msg)

    # last 5 messages for response
    window = history[-5:]

    def serialize(msg: AnyMessage) -> Dict[str, Any]:
        return {
            "type": msg.type,     # "system" / "human" / "ai"
            "content": str(msg.content),
        }

    visible_history = [serialize(m) for m in window]

    return ChatOut(
        reply=str(ai_msg.content),
        session_id=sid,
        history=visible_history,
    )

@app.post("/reset")
def reset_session(body: Optional[ResetIn] = None):
    sid = (body.session_id if body and body.session_id else DEFAULT_SESSION_ID)
    store.reset(sid)
    return {"ok": True, "session_id": sid}

@app.get("/sessions")
def list_sessions():
    return {"sessions": store.list_sessions()}
