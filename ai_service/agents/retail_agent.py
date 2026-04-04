"""
NorthStar Retail Intelligence Agent
====================================
Built on LangGraph's ReAct (Reason + Act) pattern using Google Gemini Flash.

How it works:
1. A manager's question (or a scheduled trigger) enters as a HumanMessage.
2. Gemini Flash reads the question and decides which tool(s) to call.
3. Tool calls hit the live PostgreSQL database and return real data.
4. Gemini reasons over the results and decides whether to call more tools or answer.
5. This loop repeats until the agent has enough information to give a final answer.

The LLM never hardcodes which tools to call — it decides based on the question.
That's what makes this truly agentic.
"""
import os
import logging
from typing import Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from agents.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

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

OPERATING PRINCIPLES:
- Always use real data from tools before making recommendations. Never guess.
- When analyzing inventory issues, check BOTH stock levels AND sales velocity.
- Be specific: name exact products, give exact numbers, suggest exact quantities.
- Prioritize by urgency: stockouts > low stock > slow movers.
- Your responses go directly to store managers who need to act immediately.

Keep answers concise, factual, and immediately actionable."""


def create_retail_agent():
    """
    Create the LangGraph ReAct agent with Gemini Flash as the reasoning engine.
    Returns None if GEMINI_API_KEY is not configured (graceful degradation).
    """
    if not GEMINI_API_KEY:
        logger.warning("GEMINI_API_KEY not set — agentic AI features disabled. "
                       "Set GEMINI_API_KEY env var to enable LangGraph agent.")
        return None

    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=GEMINI_API_KEY,
            temperature=0,          # Deterministic for business decisions
            max_tokens=2048,
        )
        agent = create_react_agent(
            llm,
            ALL_TOOLS,
            state_modifier=SYSTEM_PROMPT,
        )
        logger.info("NorthStar Retail Agent initialized: Gemini 1.5 Flash + %d tools", len(ALL_TOOLS))
        return agent
    except Exception as e:
        logger.error("Failed to initialize retail agent: %s", e)
        return None


async def run_agent_query(
    question: str,
    store_id: Optional[str] = None,
    agent=None,
) -> dict:
    """
    Run a single query through the agent and return the result with reasoning chain.

    Args:
        question: Natural language question from manager
        store_id: Store context (appended to question if provided)
        agent: The compiled LangGraph graph (from create_retail_agent())

    Returns:
        {
            "answer": str,           # final response
            "tool_calls": list,      # which tools were called and in what order
            "reasoning_steps": int   # how many steps the agent took
        }
    """
    if agent is None:
        return {
            "error": "Agentic AI not configured. Please set GEMINI_API_KEY environment variable.",
            "fallback": "Using deterministic AI features (recommendations, anomalies, NL query).",
        }

    # Inject store context into the question
    full_question = question
    if store_id:
        full_question = f"{question}\n\n[Store ID for all tool calls: {store_id}]"

    try:
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=full_question)]}
        )

        messages = result.get("messages", [])
        final_message = messages[-1] if messages else None
        answer = final_message.content if final_message else "No response generated."

        # Extract tool call trace for transparency
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
            "agent": "NorthStar Retail Intelligence Agent (Gemini 1.5 Flash + LangGraph)",
        }

    except Exception as e:
        logger.error("Agent query failed: %s", e)
        return {"error": f"Agent execution failed: {str(e)}"}
