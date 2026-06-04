# agent/response_builder.py

import logging
from typing import Optional, Dict, List
from agent.core import AgentConfig, AGENT_CAPABILITIES

log = logging.getLogger(__name__)


def format_metadata(
    intent: str,
    tool: Optional[str],
    elapsed: float,
    memory_hits: int
) -> str:
    parts = []
    if intent == "tool" and tool:
        parts.append(f"tool: {tool}")
    elif intent == "search":
        parts.append("source: web search")
    elif intent == "memory_recall":
        parts.append(f"memory: recalled")
    elif intent == "file_analysis":
        parts.append("source: file")
    parts.append(f"response time: {elapsed}s")
    return " | ".join(parts)


def format_sources(sources: List[str]) -> str:
    if not sources:
        return ""
    lines = ["\nSources:"]
    for i, url in enumerate(sources[:3], 1):
        lines.append(f"  {i}. {url}")
    return "\n".join(lines)


def format_memory_hits(memory_hits: int) -> str:
    if memory_hits == 0:
        return ""
    return f"memory hits this session: {memory_hits}"


def format_error(error: str) -> str:
    return f"Error: {error}\nPlease try rephrasing your request."


def build_startup_banner(cfg: AgentConfig) -> str:
    lines = [
        "=" * 70,
        "  AUTONOMOUS AI AGENT — FULL SYSTEM",
        f"  Model   : {cfg.model}",
        f"  Session : {cfg.session_id}",
        "=" * 70,
        "  Type 'help' to see all capabilities and commands",
        "=" * 70
    ]
    return "\n".join(lines)


def build_help_text() -> str:
    lines = ["I am a fully autonomous AI agent. Here is what I can do:\n"]
    for i, cap in enumerate(AGENT_CAPABILITIES, 1):
        lines.append(f"  {i}. {cap}")
    lines.append("\nCommands available in this session:")
    commands = {
        "exit": "end session and export transcript",
        "memory": "show memory stats",
        "recall <query>": "semantic search through past conversations",
        "tools": "list all available tools",
        "stats": "show session performance stats",
        "clear": "clear all memory",
        "history": "show past web searches",
        "last": "show last web search result",
        "upcoming": "show upcoming calendar events",
        "help": "show this message"
    }
    for cmd, desc in commands.items():
        lines.append(f"  {cmd:<20} — {desc}")
    return "\n".join(lines)


def build_session_summary(cfg: AgentConfig) -> str:
    avg_times = {
        intent: round(sum(times) / len(times), 2)
        for intent, times in cfg.response_times.items() if times
    }
    lines = [
        "\nSession Summary:",
        f"  Session ID   : {cfg.session_id}",
        f"  Turns        : {cfg.total_turns}",
        f"  Tokens used  : {cfg.session_token_count}",
        f"  Tool calls   : {cfg.tool_call_count}",
        f"  Searches     : {cfg.search_count}",
        f"  Memory hits  : {cfg.memory_hits}",
        f"  Intent breakdown : {cfg.intent_counts}",
        f"  Avg response times : {avg_times}"
    ]
    return "\n".join(lines)


def build_stats_text(cfg: AgentConfig, memory_summary: str, search_summary: str) -> str:
    avg_times = {
        intent: round(sum(times) / len(times), 2)
        for intent, times in cfg.response_times.items() if times
    }
    lines = [
        "\nSession Stats:",
        f"  Turns        : {cfg.total_turns}",
        f"  Tokens       : {cfg.session_token_count}",
        f"  Tool calls   : {cfg.tool_call_count}",
        f"  Searches     : {cfg.search_count}",
        f"  Memory hits  : {cfg.memory_hits}",
        f"  Intents      : {cfg.intent_counts}",
        f"  Avg times    : {avg_times}",
        f"  {memory_summary}",
        f"  {search_summary}"
    ]
    return "\n".join(lines)


def build_response(
    reply: str,
    intent: str,
    tool: Optional[str],
    elapsed: float,
    cfg: AgentConfig
) -> str:
    metadata = format_metadata(intent, tool, elapsed, cfg.memory_hits)
    if metadata:
        return f"{reply}\n\n{metadata}"
    return reply