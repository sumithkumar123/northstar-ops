from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router
from agent_events import create_event_table
from agents.retail_agent import create_retail_agent
from agents.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan — runs setup on startup and teardown on shutdown.
    1. Creates the ai_agent_events table (if not exists)
    2. Initializes the LangGraph + Gemini agent
    3. Starts the autonomous scheduler (Restock + Guardian sentinels)
    """
    # Create audit log table
    await create_event_table()

    # Boot the agent (requires GEMINI_API_KEY env var)
    agent = create_retail_agent()

    # Store agent on app state so routes can access it
    app.state.agent = agent

    # Launch background autonomous loops
    start_scheduler(agent)

    yield  # App is running

    # Graceful shutdown
    stop_scheduler()


app = FastAPI(
    title="NorthStar AI Service",
    version="2.0.0",
    description="Multi-agent retail intelligence: LangGraph + Gemini Flash + autonomous sentinels",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
