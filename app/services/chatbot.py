import json
from typing import TypedDict, Annotated, List, Optional, Literal
from operator import add
import logging

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langchain_ollama import ChatOllama
from pydantic import BaseModel, ValidationError

from core.config import get_settings
from services.igdb import IGDBClient

settings = get_settings()
logger = logging.getLogger(__name__)

# ---------------- System prompts ----------------

RESPONSE_SYSTEM = (
    "You are a helpful AI assistant specialized in VIDEO GAMES.\n"
    "\n"
    "MODE 1: CHITCHAT / GENERAL\n"
    "- If the user greets you ('Hi', 'Hello') or asks general questions without specific game data provided, simply be friendly, concise, and helpful.\n"
    "- Do NOT complain about missing context.\n"
    "\n"
    "MODE 2: GAME DATA (When <context> is provided)\n"
    "- If you see a <context> block with JSON data, you MUST use it as your primary source of truth.\n"
    "- Summarize the data nicely. Do not dump the JSON.\n"
    "- If a game is NOT in the <context>, you can use your general knowledge, but verify facts if possible.\n"
    "- Trust <context> ratings and dates over your internal memory.\n"
    "\n"
    "STYLE: Be enthusiastic, concise, and helpful."
)

INTENT_SYSTEM = (
    "You are a strict JSON classifier. You do NOT chat. You only output JSON.\n"
    "\n"
    "TASK:\n"
    "1) Analyze the user's latest message.\n"
    "2) Extract intent and filters (genre, platform, sort_by).\n"
    "3) Return valid JSON matching the schema below.\n"
    "\n"
    "INTENTS:\n"
    "- game_recommendation : User wants suggestions (categories, genres, 'best of').\n"
    "- game_info           : User asks about a SPECIFIC game name.\n"
    "- chitchat            : Greetings, 'how are you', or vague nonsense.\n"
    "- other               : Anything else.\n"
    "\n"
    "FILTERS (Only if explicitly stated):\n"
    "- genre (e.g. 'RPG', 'Shooter')\n"
    "- platform (e.g. 'PC', 'PS5')\n"
    "- sort_by ('rating', 'new', 'relevance')\n"
    "\n"
    "SCHEMA:\n"
    "{\"intent\": \"game_recommendation\", \"query\": \"\", \"genre\": \"Shooter\", \"platform\": null, \"sort_by\": \"rating\"}\n"
    "\n"
    "EXAMPLES:\n"
    "User: 'Hi'\n"
    "JSON: {\"intent\": \"chitchat\", \"query\": \"\", \"sort_by\": \"relevance\"}\n"
    "\n"
    "User: 'Best RPGs'\n"
    "JSON: {\"intent\": \"game_recommendation\", \"query\": \"\", \"genre\": \"RPG\", \"sort_by\": \"rating\"}\n"
    "\n"
    "User: 'Who made Elden Ring?'\n"
    "JSON: {\"intent\": \"game_info\", \"query\": \"Elden Ring\"}\n"
    "\n"
    "User: 'New racing games'\n"
    "JSON: {\"intent\": \"game_recommendation\", \"genre\": \"Racing\", \"sort_by\": \"new\"}\n"
    "\n"
    "Provide JSON ONLY."
)

# ---------------- LLM config ----------------

LLM = ChatOllama(
    model=settings.OLLAMA_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=0.2,
)

# ---------------- Pydantic schema for intent result ----------------

class IntentResult(BaseModel):
    intent: Literal["game_recommendation", "game_info", "chitchat", "other"]
    query: Optional[str] = ""
    genre: Optional[str] = None
    platform: Optional[str] = None
    sort_by: Optional[str] = "relevance"  # Changed to str to allow lenient parsing

# ---------------- IGDB client ----------------

# We instantiate it globally or per request. Global is fine for now as it handles its own token state.
igdb_client = IGDBClient()

# ---------------- Graph state ----------------

class ChatState(TypedDict):
    messages: Annotated[List[AnyMessage], add]
    intent: Optional[str]
    search_query: Optional[str]
    igdb_context: Optional[str]
    # Filters
    genre: Optional[str]
    platform: Optional[str]
    sort_by: Optional[str]

# ---------------- Node: analyze_intent ----------------

async def analyze_intent(state: ChatState) -> ChatState:
    msgs = list(state["messages"])
    prompt_msgs: List[AnyMessage] = [SystemMessage(content=INTENT_SYSTEM)]
    prompt_msgs.extend(msgs)

    # LLM invoke is sync in LangChain by default unless we use ainvoke, 
    # but ChatOllama might support async. Let's stick to invoke for now or upgrade to ainvoke if needed.
    # Actually, let's use ainvoke for true async.
    ai = await LLM.ainvoke(prompt_msgs)
    raw = str(ai.content)

    intent: str = "other"
    search_query: str = ""
    parsed: Optional[IntentResult] = None

    try:
        # Robust JSON extraction: Find first { and last }
        raw = raw.strip()
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            raw = raw[start : end + 1]
        
        data = json.loads(raw)
        parsed = IntentResult.model_validate(data)
        intent = parsed.intent
        search_query = parsed.query or ""
    except (json.JSONDecodeError, ValidationError) as e:
        logger.warning(f"Failed to parse JSON from LLM: {e}; raw={raw!r}")

    if not search_query and intent in ["game_recommendation", "game_info"]:
         # Only fallback if we REALLY think it's a game intent but missed the query.
         # But usually, it's safer to downgrade to chitchat if query is empty.
         pass
    
    if parsed:
        genre = parsed.genre
        platform = parsed.platform
        sb = (parsed.sort_by or "").lower()
        if "rating" in sb:
            sort_by = "rating"
        elif "new" in sb or "date" in sb:
            sort_by = "new"
        else:
            sort_by = "relevance"
    else:
        genre = None
        platform = None
        sort_by = "relevance"

    logger.info(f"Intent analyzed: {intent}, Query: {search_query}, Genre: {genre}, Sort: {sort_by}")
    return {
        "intent": intent,
        "search_query": search_query,
        "genre": genre,
        "platform": platform,
        "sort_by": sort_by,
        # Ensure keys exist
        "igdb_context": None,
        "messages": [] 
    }

# ---------------- Router ----------------

def route_from_intent(state: ChatState) -> str:
    intent = (state.get("intent") or "").lower()
    if intent in ("game_recommendation", "game_info"):
        return "use_igdb"
    return "skip_igdb"

# ---------------- Node: igdb_lookup ----------------

async def igdb_lookup(state: ChatState) -> ChatState:
    search_query = (state.get("search_query") or "").strip()
    genre = state.get("genre")
    platform = state.get("platform")
    sort_by = state.get("sort_by") or "relevance"

    # Strict check: If query AND filters are empty, skip IGDB to avoid random results?
    # Actually, empty query + filters = Browse Mode (e.g. "Best RPGs" -> genre=RPG, sort=rating, query="")
    # So we accept empty query IF filters exist.
    if not search_query and not genre and not platform and sort_by == "relevance":
         return {"igdb_context": None}

    logger.info(f"Searching IGDB: q='{search_query}' genre='{genre}' sort='{sort_by}'")
    games = await igdb_client.search_games(
        search_text=search_query,
        genre=genre,
        platform=platform,
        sort_by=sort_by,
        limit=5,
    )
    
    if not games:
        return {"igdb_context": "No matching games found in IGDB for this query."}

    ctx = igdb_client.clean_games_data(games)
    # Store as JSON string for consistent state typing, or store raw list if TypedDict allowed Any.
    # TypedDict 'igdb_context' is currently Optional[str]. Let's keep it str for simplicity in prompt injection.
    import json
    return {"igdb_context": json.dumps(ctx, indent=2)}

# ---------------- Node: respond ----------------

async def respond(state: ChatState) -> ChatState:
    history = list(state["messages"])
    igdb_context = state.get("igdb_context")

    msgs: List[AnyMessage] = [SystemMessage(content=RESPONSE_SYSTEM)]

    if igdb_context:
        msgs.append(
            SystemMessage(
                content=(
                    "Here is the <context> data from IGDB (JSON format):\n"
                    f"<context>\n{igdb_context}\n</context>"
                )
            )
        )

    msgs.extend(history)
    ai = await LLM.ainvoke(msgs)
    return {"messages": [ai]}

# ---------------- Build the graph ----------------

def build_graph():
    g = StateGraph(ChatState)

    g.add_node("analyze_intent", analyze_intent)
    g.add_node("igdb_lookup", igdb_lookup)
    g.add_node("respond", respond)

    g.add_edge(START, "analyze_intent")

    g.add_conditional_edges(
        "analyze_intent",
        route_from_intent,
        {
            "use_igdb": "igdb_lookup",
            "skip_igdb": "respond",
        },
    )

    g.add_edge("igdb_lookup", "respond")
    g.add_edge("respond", END)

    return g.compile()

GRAPH_APP = build_graph()
