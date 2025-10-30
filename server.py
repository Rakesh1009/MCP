from __future__ import annotations
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AnyMessage
from chatbot_graph import GRAPH_APP

app = FastAPI(title="Local LangGraph Chat (Ollama + uv)")

SESSIONS: Dict[str, List[AnyMessage]] = {}

class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatOut(BaseModel):
    reply: str
    session_id: str

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/chat", response_model=ChatOut)
def chat(body: ChatIn):
    sid = body.session_id or str(uuid.uuid4())
    history = SESSIONS.setdefault(sid, [])
    history.append(HumanMessage(content=body.message))
    result = GRAPH_APP.invoke({"messages": history})
    ai_msg = result["messages"][-1]
    history.append(ai_msg)
    return ChatOut(reply=str(ai_msg.content), session_id=sid)
