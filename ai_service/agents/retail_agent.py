import os
import logging
import asyncio
import traceback
from typing import Optional, List

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from agents.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# Add .strip() to handle accidental spaces from copy-pasting the key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Store initialization error globally so the health endpoint can report it
INIT_ERROR = None
CURRENT_MODEL = None

DEFAULT_MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]

SYSTEM_PROMPT = """You are the NorthStar Retail Intelligence Agent — an autonomous AI system \
managing retail operations for NorthStar Outfitters' 48 specialty stores across the US and UK.

You have access to real-time store data through specialized tools. Your responsibilities:

1. INVENTORY GUARDIAN: Monitor stock levels and identify restock needs before stockouts occur.
   Always check inventory AND sales velocity together to properly forecast demand.

2. FRAUD SENTINEL: Detect statistically anomalous transactions that may indicate fraud,
   pricing errors, or operational issues. Flag these for manager review.

3. MERCHANDISING ADVISOR: Align product promotions with seasonal demand patterns.
   Use current season data to recommend which products to push and which need attention.

4. PERFORMANCE ANALYST: Interpret sales data and give managers clear, actionable insights
   about store health, revenue trends, and top performers.

5. TRANSFER COORDINATOR: When one store is likely to stock out, check whether another
   store can cover the gap faster through an inter-store transfer before recommending
   a fresh supplier order.

OPERATING PRINCIPLES:
- Always use real data from tools before making recommendations. Never guess.
- When analyzing inventory issues, check BOTH stock levels AND sales velocity.
- Be specific: name exact products, give exact numbers, suggest exact quantities.
- Prioritize by urgency: stockouts > low stock > slow movers.
- Your responses go directly to store managers who need to act immediately.

Keep answers concise, factual, and immediately actionable."""


def get_model_candidates() -> List[str]:
    """
    Candidate models in priority order.
    Supports either GEMINI_MODEL for a single preferred value or
    GEMINI_MODEL_CANDIDATES for a comma-separated override list.
    """
    explicit_model = os.getenv("GEMINI_MODEL", "").strip()
    explicit_candidates = os.getenv("GEMINI_MODEL_CANDIDATES", "").strip()

    ordered: List[str] = []
    if explicit_model:
        ordered.append(explicit_model)

    if explicit_candidates:
        ordered.extend([m.strip() for m in explicit_candidates.split(",") if m.strip()])

    ordered.extend(DEFAULT_MODEL_CANDIDATES)

    deduped: List[str] = []
    seen = set()
    for model in ordered:
        if model not in seen:
            deduped.append(model)
            seen.add(model)
    return deduped


def discover_supported_model() -> str:
    """
    Ask Google which generateContent-capable models are available for this key,
    then choose the best matching configured candidate. Falls back to the first
    candidate if discovery is unavailable so local/dev boot still works.
    """
    candidates = get_model_candidates()

    try:
        import google.generativeai as genai

        genai.configure(api_key=GEMINI_API_KEY)
        available = [
            m.name.replace("models/", "")
            for m in genai.list_models()
            if "generateContent" in getattr(m, "supported_generation_methods", [])
        ]

        for candidate in candidates:
            if candidate in available:
                return candidate

        # As a safe fallback, use the first available flash model if present.
        for available_model in available:
            if "flash" in available_model:
                logger.warning(
                    "Configured Gemini candidates %s not found. Falling back to available model %s",
                    candidates,
                    available_model,
                )
                return available_model

        if available:
            logger.warning(
                "No flash model matched. Falling back to first available generateContent model %s",
                available[0],
            )
            return available[0]
    except ImportError:
        logger.warning(
            "google.generativeai is not installed; skipping model discovery and using fallback model %s",
            candidates[0],
        )
    except Exception as exc:
        logger.warning("Gemini model discovery failed, using configured fallback list: %s", exc)

    return candidates[0]


def get_current_model() -> Optional[str]:
    return CURRENT_MODEL


def create_retail_agent():
    """
    Create the LangGraph ReAct agent with Gemini Flash as the reasoning engine.
    Returns None if GEMINI_API_KEY is not configured (graceful degradation).
    """
    global INIT_ERROR, CURRENT_MODEL

    if not GEMINI_API_KEY:
        INIT_ERROR = "GEMINI_API_KEY environment variable is empty or not set."
        CURRENT_MODEL = None
        logger.warning(INIT_ERROR)
        return None

    try:
        selected_model = discover_supported_model()
        llm = ChatGoogleGenerativeAI(
            model=selected_model,
            version="v1",
            google_api_key=GEMINI_API_KEY,
            temperature=0,
            max_tokens=2048,
        )
        agent = create_react_agent(
            llm,
            ALL_TOOLS,
        )
        CURRENT_MODEL = selected_model
        logger.info("NorthStar Retail Agent initialized: %s + %d tools", selected_model, len(ALL_TOOLS))
        INIT_ERROR = None
        return agent
    except Exception as e:
        CURRENT_MODEL = None
        INIT_ERROR = f"Failed to initialize LangGraph agent: {str(e)}"
        logger.error(INIT_ERROR)
        traceback.print_exc()
        return None


async def run_agent_query(
    question: str,
    store_id: Optional[str] = None,
    agent=None,
) -> dict:
    """
    Run a single query through the agent and return the result with reasoning chain.
    """
    if agent is None:
        return {
            "error": f"Agent offline. Reason: {INIT_ERROR}",
            "fallback": "Using deterministic AI features.",
        }

    full_question = question
    if store_id:
        full_question = f"{question}\n\n[Store ID for all tool calls: {store_id}]"

    try:
        # 55-second timeout so Vercel proxy never cuts us off (or we cut it first)
        result = await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=full_question)]}
            ),
            timeout=55.0,
        )

        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None

        # Defensive: Gemini content can be str or list-of-dicts
        raw = final_message.content if final_message else "No response generated."
        if isinstance(raw, list):
            parts = [b.get("text", "") for b in raw if isinstance(b, dict) and "text" in b]
            answer = "\n".join(parts) if parts else str(raw)
        else:
            answer = str(raw)

        tool_calls_trace = []
        for msg in messages:
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls_trace.append({
                        "tool": tc.get("name", "unknown"),
                        "args": tc.get("args", {}),
                    })

        return {
            "question": question,
            "answer": answer,
            "tools_invoked": tool_calls_trace,
            "reasoning_steps": len(messages),
            "model": CURRENT_MODEL,
            "agent": f"NorthStar Retail Intelligence Agent ({CURRENT_MODEL or 'Gemini'} + LangGraph)",
        }

    except asyncio.TimeoutError:
        logger.warning("Agent query timed out after 55s for: %s", question)
        return {"error": "The agent took too long to respond. Please try a simpler question."}
    except Exception as e:
        logger.error("Agent query failed: %s", e, exc_info=True)
        error_text = str(e).lower()
        if (
            "resource_exhausted" in error_text
            or "quota exceeded" in error_text
            or "429" in error_text
            or "rate limit" in error_text
        ):
            return {"error": "API key limit completed"}
        return {"error": f"Agent execution failed: {str(e)}"}
