# memory/short_term.py

import logging
from collections import deque
from datetime import datetime
from typing import List, Dict, Optional

log = logging.getLogger(__name__)

SHORT_TERM_LIMIT = 10


class ShortTermBuffer:
    def __init__(self, limit: int = SHORT_TERM_LIMIT):
        self.limit = limit
        self.buffer: deque = deque(maxlen=limit)
        log.info(f"Short term buffer initialized — capacity: {limit}")

    def add(self, role: str, content: str) -> None:
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.buffer.append(entry)
        log.debug(f"Message added — role: {role} | length: {len(content)}")

    def get(self) -> List[Dict[str, str]]:
        return [{"role": e["role"], "content": e["content"]} for e in self.buffer]

    def get_recent(self, n: int) -> List[Dict[str, str]]:
        recent = list(self.buffer)[-n:]
        return [{"role": e["role"], "content": e["content"]} for e in recent]

    def clear(self) -> None:
        self.buffer.clear()
        log.info("Short term buffer cleared")

    def summary(self) -> str:
        return f"Short term: {len(self.buffer)}/{self.limit} messages"

    def export(self) -> str:
        if not self.buffer:
            return "No recent conversation history."
        lines = ["Recent conversation:"]
        for e in self.buffer:
            lines.append(f"  [{e['timestamp']}] {e['role'].upper()}: {e['content'][:100]}")
        return "\n".join(lines)

    def is_empty(self) -> bool:
        return len(self.buffer) == 0

    def count(self) -> int:
        return len(self.buffer)