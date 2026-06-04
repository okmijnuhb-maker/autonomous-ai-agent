# tools/calendar_tool.py

import json
import logging
import uuid
from datetime import datetime, date
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict
from pathlib import Path

log = logging.getLogger(__name__)

CALENDAR_PATH = "C:/educational files/advanced_agent/memory/calendar.json"
DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"


@dataclass
class Event:
    title: str
    date: str
    time: str
    description: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


class CalendarManager:
    def __init__(self, path: str = CALENDAR_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.events: List[Dict] = self._load()
        log.info(f"Calendar loaded — {len(self.events)} events")

    def _load(self) -> List[Dict]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def _save(self) -> None:
        self.path.write_text(json.dumps(self.events, indent=2), encoding="utf-8")

    def _validate_date(self, date_str: str) -> bool:
        try:
            datetime.strptime(date_str, DATE_FORMAT)
            return True
        except ValueError:
            return False

    def _validate_time(self, time_str: str) -> bool:
        try:
            datetime.strptime(time_str, TIME_FORMAT)
            return True
        except ValueError:
            return False

    def add_event(self, title: str, date_str: str, time_str: str, description: str = "") -> str:
        if not self._validate_date(date_str):
            return f"Invalid date format: {date_str} — use YYYY-MM-DD"
        if not self._validate_time(time_str):
            return f"Invalid time format: {time_str} — use HH:MM"
        event = Event(title=title, date=date_str, time=time_str, description=description)
        self.events.append(asdict(event))
        self._save()
        log.info(f"Event added — id: {event.event_id} | title: {title} | date: {date_str}")
        return f"Event added — ID: {event.event_id} | {title} on {date_str} at {time_str}"

    def list_events(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
        if not self.events:
            return "No events found."
        filtered = self.events
        if start_date and self._validate_date(start_date):
            filtered = [e for e in filtered if e["date"] >= start_date]
        if end_date and self._validate_date(end_date):
            filtered = [e for e in filtered if e["date"] <= end_date]
        if not filtered:
            return "No events found in the given date range."
        sorted_events = sorted(filtered, key=lambda e: (e["date"], e["time"]))
        lines = [f"{'ID':<10} {'Date':<12} {'Time':<8} {'Title':<30} Description"]
        lines.append("-" * 70)
        for e in sorted_events:
            lines.append(f"{e['event_id']:<10} {e['date']:<12} {e['time']:<8} {e['title']:<30} {e['description'][:30]}")
        log.info(f"Listed {len(sorted_events)} events")
        return "\n".join(lines)

    def delete_event(self, event_id: str) -> str:
        original_count = len(self.events)
        self.events = [e for e in self.events if e["event_id"] != event_id]
        if len(self.events) == original_count:
            return f"No event found with ID: {event_id}"
        self._save()
        log.info(f"Event deleted — id: {event_id}")
        return f"Event deleted successfully — ID: {event_id}"

    def search_events(self, keyword: str) -> str:
        keyword_lower = keyword.lower()
        matches = [
            e for e in self.events
            if keyword_lower in e["title"].lower() or keyword_lower in e["description"].lower()
        ]
        if not matches:
            return f"No events found matching: {keyword}"
        lines = [f"Found {len(matches)} event(s) matching '{keyword}':\n"]
        for e in sorted(matches, key=lambda x: (x["date"], x["time"])):
            lines.append(f"  [{e['event_id']}] {e['date']} {e['time']} — {e['title']}")
            if e["description"]:
                lines.append(f"      {e['description']}")
        log.info(f"Search '{keyword}' — {len(matches)} matches")
        return "\n".join(lines)

    def upcoming_events(self, n: int = 5) -> str:
        today = date.today().strftime(DATE_FORMAT)
        upcoming = [e for e in self.events if e["date"] >= today]
        sorted_upcoming = sorted(upcoming, key=lambda e: (e["date"], e["time"]))[:n]
        if not sorted_upcoming:
            return "No upcoming events."
        lines = [f"Next {len(sorted_upcoming)} upcoming event(s):\n"]
        for e in sorted_upcoming:
            lines.append(f"  [{e['event_id']}] {e['date']} {e['time']} — {e['title']}")
            if e["description"]:
                lines.append(f"      {e['description']}")
        log.info(f"Upcoming events fetched — {len(sorted_upcoming)} events")
        return "\n".join(lines)

    def summary(self) -> str:
        return f"Total events: {len(self.events)}"


calendar = CalendarManager()


def calendar_action(action: str, **kwargs) -> str:
    actions = {
        "add": lambda: calendar.add_event(
            title=kwargs.get("title", ""),
            date_str=kwargs.get("date", ""),
            time_str=kwargs.get("time", ""),
            description=kwargs.get("description", "")
        ),
        "list": lambda: calendar.list_events(
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date")
        ),
        "delete": lambda: calendar.delete_event(kwargs.get("event_id", "")),
        "search": lambda: calendar.search_events(kwargs.get("keyword", "")),
        "upcoming": lambda: calendar.upcoming_events(n=kwargs.get("n", 5)),
        "summary": lambda: calendar.summary()
    }
    handler = actions.get(action.lower())
    if not handler:
        return f"Unknown calendar action: {action}. Available: add, list, delete, search, upcoming, summary"
    return handler()