from __future__ import annotations
from typing import TypedDict, Annotated, List
from operator import add
import os

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_ollama import ChatOllama

DUMMY_SYSTEM = (
    "You are a friendly, concise chatbot. "
    "Answer directly; avoid fluff. If greeted, greet warmly."
)

# Lock to Qwen 0.5B by default
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b-instruct")
LLM = ChatOllama(model=OLLAMA_MODEL, temperature=0.2)

class ChatState(TypedDict):
    messages: Annotated[List[AnyMessage], add]

def call_model(state: ChatState) -> ChatState:
    msgs = state["messages"]
    if not msgs or not isinstance(msgs[0], SystemMessage):
        msgs = [SystemMessage(content=DUMMY_SYSTEM)] + msgs
    ai = LLM.invoke(msgs)
    return {"messages": [ai]}

def build_graph():
    g = StateGraph(ChatState)
    g.add_node("llm", call_model)
    g.add_edge(START, "llm")
    g.add_edge("llm", END)
    return g.compile()

GRAPH_APP = build_graph()
