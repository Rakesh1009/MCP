#!/usr/bin/env python3
"""
server.py

FastAPI app exposing the LangGraph chatbot as an HTTP API.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage, AnyMessage

from chatbot_graph import GRAPH_APP


# ---------------- Session store ----------------

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


# ---------------- Models & app ----------------

class ChatIn(BaseModel):
    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(
        None, description="Optional session id; if not provided, 'dev' is used."
    )


class ChatOut(BaseModel):
    reply: str
    session_id: str
    history: List[Dict[str, str]]  # simple role/content view for the client


app = FastAPI(title="GameBrain Backend", version="0.1.0")


# ---------------- Helpers ----------------

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


# ---------------- Routes ----------------

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn) -> ChatOut:
    session_id = body.session_id or DEFAULT_SESSION_ID

    history = store.get_history(session_id)
    history.append(HumanMessage(content=body.message))

    result = GRAPH_APP.invoke({"messages": history})
    ai_msg = result["messages"][-1]

    history.append(ai_msg)
    store.set_history(session_id, history)

    return ChatOut(
        reply=str(ai_msg.content),
        session_id=session_id,
        history=_serialize_history(history),
    )


@app.post("/reset")
def reset_session(session_id: Optional[str] = None) -> Dict[str, str]:
    sid = session_id or DEFAULT_SESSION_ID
    store.reset(sid)
    return {"status": "ok", "session_id": sid}


@app.get("/sessions")
def list_sessions() -> Dict[str, List[str]]:
    return {"sessions": store.list_sessions()}
