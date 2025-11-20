#!/usr/bin/env python3
"""
chatbot_graph.py

Minimal LangGraph setup for a single-node LLM chat flow.
Later we can grow this into a multi-node graph with tools (IGDB, etc.).
"""

from __future__ import annotations

import os
from typing import TypedDict, Annotated, List
from operator import add

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AnyMessage, SystemMessage
from langchain_ollama import ChatOllama

# ---- System prompt ----

SYSTEM = (
    "You are a helpful AI assistant specialized in VIDEO GAMES.\n"
    "\n"
    "Your main job is to help the user decide what to PLAY next, and how to get the most out of their games.\n"
    "\n"
    "When the user asks for recommendations, always think about:\n"
    "- Platform (PC, console, mobile) if they mention it\n"
    "- Mood (chill, comfy, story-heavy, sweaty/competitive, horror, etc.)\n"
    "- Time budget (short sessions vs long sessions)\n"
    "- Difficulty tolerance (casual vs hardcore)\n"
    "- Budget (cheap / on sale / AAA full price) if they mention money\n"
    "\n"
    "If the user is vague, ask 1-2 short follow-up questions to clarify their taste.\n"
    "If they are clear, go straight to recommendations.\n"
    "\n"
    "Do NOT invent exact prices or fake store URLs for now. You can mention platforms and very rough price tiers "
    "(e.g. 'budget', 'mid', 'full price') but no made-up numbers.\n"
    "Be concise but friendly, and briefly explain WHY each suggested game fits their preferences."
)

# ---- LLM config ----

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b-instruct")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://llm:11434")

LLM = ChatOllama(
    model=OLLAMA_MODEL,
    base_url=OLLAMA_BASE_URL,
    temperature=0.2,
)

# ---- Graph state ----

class ChatState(TypedDict):
    messages: Annotated[List[AnyMessage], add]


# ---- Node function ----

def call_model(state: ChatState) -> ChatState:
    msgs = state["messages"]

    # Ensure our SYSTEM prompt is always the first message
    if not msgs or not isinstance(msgs[0], SystemMessage):
        msgs = [SystemMessage(content=SYSTEM)] + msgs

    ai = LLM.invoke(msgs)
    return {"messages": [ai]}


# ---- Build the graph ----

def build_graph():
    g = StateGraph(ChatState)
    g.add_node("llm", call_model)
    g.add_edge(START, "llm")
    g.add_edge("llm", END)
    return g.compile()


GRAPH_APP = build_graph()
