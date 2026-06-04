# agent/core.py

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv
from groq import Groq

# paths
from pathlib import Path
BASE_PATH = str(Path(__file__).resolve().parent.parent)
ENV_PATH = f"{BASE_PATH}/.env"
CHROMA_PATH = f"{BASE_PATH}/memory/chroma_store"
SEARCH_HISTORY_PATH = f"{BASE_PATH}/memory/search_history.json"
SENT_LOG_PATH = f"{BASE_PATH}/memory/sent_emails.json"
CALENDAR_PATH = f"{BASE_PATH}/memory/calendar.json"
SESSION_LOG_PATH = f"{BASE_PATH}/memory/session_log.json"
EXPORT_PATH = f"{BASE_PATH}/memory/session_export.txt"

# model constants
DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.3
SHORT_TERM_LIMIT = 10
MEMORY_RESULTS = 3
MAX_RESULTS_PER_QUERY = 4
MAX_BODY_LENGTH = 300
MAX_TOOL_OUTPUT = 500
MAX_TEXT_OUTPUT = 2000
MAX_RETRIES = 3
RETRY_DELAY = 2

AGENT_CAPABILITIES = [
    "Multi-turn conversation with persistent memory",
    "Short-term buffer + ChromaDB long-term vector memory",
    "Semantic memory recall across sessions",
    "10 tools: calculator, wikipedia, web search, file reader, datetime, unit converter, dictionary, weather, csv analyzer, system info",
    "Multi-query web search pipeline with source ranking",
    "Follow-up detection with context injection",
    "Intent classification: chat, tool, search, memory recall, file analysis",
    "Email sending with attachment support",
    "Calendar management: add, list, delete, search, upcoming events",
    "Session logging to JSON",
    "Conversation export to txt",
    "Graceful error recovery with pipeline fallback",
    "Performance tracking per intent type"
]


def setup_logging() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    return logging.getLogger(__name__)


log = setup_logging()


def generate_session_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def init_client() -> Groq:
    load_dotenv(Path(ENV_PATH))
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("GROQ_API_KEY not found in .env")
    log.info("Groq client initialized successfully")
    return Groq(api_key=api_key)


@dataclass
class AgentConfig:
    model: str = DEFAULT_MODEL
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = DEFAULT_TEMPERATURE
    system_prompt: str = (
        "You are a fully autonomous AI agent with memory, tools, and web search capabilities. "
        "You recall past interactions, execute tools, search the web, and reason across multiple steps. "
        "Always use the most appropriate capability for each request. "
        "Be concise, precise, and professional."
    )
    session_id: str = field(default_factory=generate_session_id)
    session_token_count: int = field(default=0, repr=False)
    tool_call_count: int = field(default=0, repr=False)
    search_count: int = field(default=0, repr=False)
    memory_hits: int = field(default=0, repr=False)
    total_turns: int = field(default=0, repr=False)
    intent_counts: Dict[str, int] = field(default_factory=lambda: {
        "chat": 0, "tool": 0, "search": 0, "memory_recall": 0, "file_analysis": 0
    }, repr=False)
    response_times: Dict[str, List[float]] = field(default_factory=lambda: {
        "chat": [], "tool": [], "search": [], "memory_recall": [], "file_analysis": []
    }, repr=False)
