# app/main.py

import sys
import logging
import json
from pathlib import Path
from typing import Optional
from datetime import datetime

sys.path.append(str(Path(__file__).resolve().parent.parent))

# Added UploadFile and File for direct data loading
from fastapi import FastAPI, HTTPException, UploadFile, File as FastAPIFile
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.core import AgentConfig, init_client, AGENT_CAPABILITIES, EXPORT_PATH, BASE_PATH
from memory.short_term import ShortTermBuffer
from memory.long_term import LongTermMemory
from tools.web_search import SearchHistoryManager
from tools.calendar_tool import CalendarManager
from agent.orchestrator import orchestrate
from agent.response_builder import (
    build_startup_banner, build_help_text,
    build_session_summary, build_stats_text, build_response
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# --- tool registry ---
import math
import requests
import platform
import psutil
import shutil  # Added for direct background file stream copying
import pandas as pd
import wikipediaapi
from ddgs import DDGS

MAX_TOOL_OUTPUT = 500

def calculator(expression: str) -> str:
    try:
        return f"Result: {eval(expression, {'__builtins__': {}}, {'math': math})}"
    except Exception as e:
        return f"Calculator error: {e}"

def wikipedia_tool(query: str) -> str:
    try:
        wiki = wikipediaapi.Wikipedia(language="en", user_agent="AutonomousAgent/1.0")
        page = wiki.page(query)
        return page.summary[:MAX_TOOL_OUTPUT] if page.exists() else f"No page found: {query}"
    except Exception as e:
        return f"Wikipedia error: {e}"

def web_search_tool(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        return "\n".join([f"{r['title']}: {r['body'][:150]}" for r in results]) if results else "No results."
    except Exception as e:
        return f"Web search error: {e}"

def file_reader(filepath: str) -> str:
    import re
    from pathlib import Path

    match = re.search(r'([A-Za-z]:[^\|]+\.\w+)', filepath)
    actual_path = match.group(1).strip() if match else filepath.strip()
    path = Path(actual_path)

    if not path.exists():
        return f"Error: The file at path {actual_path} was not found on the server disk storage."

    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(path)
            text_content = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
            extracted_text = "\n".join(text_content).strip()
            if not extracted_text:
                return "Error: The PDF file appears to be empty or contains only scanned image layers."
            return extracted_text[:8000]
        except Exception as pdf_err:
            return f"Failed to extract text from PDF: {str(pdf_err)}"

    try:
        from tools.file_handler import read_file
        return read_file(actual_path)
    except Exception as e:
        return f"File reader error: {e}"

def datetime_tool(query: str) -> str:
    import pytz
    import re
    from datetime import datetime as dt

    query_lower = query.lower()

    # Extract place name from query
    patterns = [
        r'time in (.+)',
        r'current time in (.+)',
        r'what time is it in (.+)',
        r'what is the time in (.+)',
        r'time at (.+)',
    ]

    place = None
    for pattern in patterns:
        match = re.search(pattern, query_lower)
        if match:
            place = match.group(1).strip().rstrip('?').strip()
            break

    # If no place found default to IST
    if not place or place in ['india', 'ist', '']:
        tz = pytz.timezone("Asia/Kolkata")
        now = dt.now(tz)
        return f"Current time in India (IST): {now.strftime('%H:%M:%S %Z')}"

    # Look up timezone for any city in the world
    try:
        from geopy.geocoders import Nominatim
        from timezonefinder import TimezoneFinder

        geolocator = Nominatim(user_agent="autonomous_agent")
        location = geolocator.geocode(place, timeout=5)

        if not location:
            return f"Could not find location: {place}"

        tf = TimezoneFinder()
        tz_name = tf.timezone_at(lat=location.latitude, lng=location.longitude)

        if not tz_name:
            return f"Could not determine timezone for: {place}"

        tz = pytz.timezone(tz_name)
        now = dt.now(tz)

        if "time" in query_lower:
            return f"Current time in {place.title()}: {now.strftime('%H:%M:%S %Z')}"
        if "day" in query_lower:
            return f"Today in {place.title()}: {now.strftime('%A, %Y-%m-%d')}"
        return f"Current datetime in {place.title()}: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"

    except Exception as e:
        log.warning(f"Timezone lookup failed: {e}")
        tz = pytz.timezone("Asia/Kolkata")
        now = dt.now(tz)
        return f"Current time in India (IST): {now.strftime('%H:%M:%S %Z')}"

def unit_converter(query: str) -> str:
    try:
        parts = query.lower().split()
        value, unit_from, unit_to = float(parts[0]), parts[1], parts[3]
        conversions = {
            ("kg","lbs"): lambda x: x*2.20462, ("lbs","kg"): lambda x: x/2.20462,
            ("km","miles"): lambda x: x*0.621371, ("miles","km"): lambda x: x/0.621371,
            ("celsius","fahrenheit"): lambda x: x*9/5+32,
            ("fahrenheit","celsius"): lambda x: (x-32)*5/9,
            ("meters","feet"): lambda x: x*3.28084, ("feet","meters"): lambda x: x/3.28084,
        }
        key = (unit_from, unit_to)
        if key not in conversions:
            return f"Conversion {unit_from} to {unit_to} not supported."
        return f"{value} {unit_from} = {round(conversions[key](value), 4)} {unit_to}"
    except Exception as e:
        return f"Unit converter error: {e}"

def dictionary_tool(word: str) -> str:
    try:
        r = requests.get(f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}", timeout=5)
        data = r.json()
        if isinstance(data, list):
            meaning = data[0]["meanings"][0]
            return f"{word} ({meaning['partOfSpeech']}): {meaning['definitions'][0]['definition']}"
        return f"No definition found: {word}"
    except Exception as e:
        return f"Dictionary error: {e}"

def weather_tool(city: str) -> str:
    try:
        r = requests.get(f"https://wttr.in/{city.replace(' ', '+')}?format=3", timeout=5)
        return r.text.strip()
    except Exception as e:
        return f"Weather error: {e}"

def csv_analyzer(filepath: str) -> str:
    try:
        import re
        match = re.search(r'([A-Za-z]:[^\|]+\.csv)', filepath)
        actual_path = match.group(1).strip() if match else filepath.strip()
        df = pd.read_csv(actual_path)
        return f"Shape: {df.shape}\nColumns: {list(df.columns)}\nStats:\n{df.describe().to_string()[:MAX_TOOL_OUTPUT]}"
    except Exception as e:
        return f"CSV analyzer error: {e}"

def system_info(query: str) -> str:
    try:
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return (
            f"OS: {platform.system()} {platform.release()}\n"
            f"CPU: {cpu}%\n"
            f"RAM: {ram.used/1e9:.1f}GB / {ram.total/1e9:.1f}GB ({ram.percent}%)\n"
            f"Disk: {disk.used/1e9:.1f}GB / {disk.total/1e9:.1f}GB ({disk.percent}%)"
        )
    except Exception as e:
        return f"System info error: {e}"

TOOL_REGISTRY = {
    "calculator":     {"fn": calculator,      "description": "Evaluates math expressions."},
    "wikipedia":      {"fn": wikipedia_tool,  "description": "Fetches Wikipedia summary."},
    "web_search":     {"fn": web_search_tool, "description": "Searches the web via DuckDuckGo."},
    "file_reader":    {"fn": file_reader,      "description": "Reads txt, csv, pdf, json files."},
    "datetime_tool":  {"fn": datetime_tool,   "description": "Returns current date/time/day."},
    "unit_converter": {"fn": unit_converter,  "description": "Converts units (km, kg, celsius, etc)."},
    "dictionary":     {"fn": dictionary_tool, "description": "Returns word definition."},
    "weather":        {"fn": weather_tool,    "description": "Returns current weather by city."},
    "csv_analyzer":   {"fn": csv_analyzer,    "description": "Analyzes CSV file statistics."},
    "system_info":    {"fn": system_info,     "description": "Returns system CPU/RAM/disk usage."},
}

# --- app init ---
app = FastAPI(title="Autonomous AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

client = init_client()
config = AgentConfig()
short_term = ShortTermBuffer()
long_term = LongTermMemory()
search_history = SearchHistoryManager()
calendar = CalendarManager()

SESSIONS_PATH = Path(f"{BASE_PATH}/memory/sessions")
SESSIONS_PATH.mkdir(parents=True, exist_ok=True)

# Define and build dynamic uploads directory path anchor
UPLOAD_DIR = Path(f"{BASE_PATH}/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

current_session: dict = {"id": None, "title": None, "messages": []}

def generate_title(message: str) -> str:
    return message[:45] + "..." if len(message) > 45 else message

def session_file(session_id: str) -> Path:
    return SESSIONS_PATH / f"session_{session_id}.json"

def save_session() -> None:
    if not current_session["id"]:
        return
    session_file(current_session["id"]).write_text(
        json.dumps(current_session, indent=2), encoding="utf-8"
    )

def load_session_file(session_id: str) -> dict:
    path = session_file(session_id)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def init_new_session() -> str:
    sid = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_session["id"] = sid
    current_session["title"] = "New Conversation"
    current_session["messages"] = []
    current_session["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_session()
    log.info(f"New session created: {sid}")
    return sid

init_new_session()
log.info(f"Agent initialized — session: {config.session_id}")

# --- request models ---
class ChatRequest(BaseModel):
    message: str

class CalendarAddRequest(BaseModel):
    title: str
    date: str
    time: str
    description: Optional[str] = ""

# --- routes ---
@app.get("/")
def serve_index():
    return FileResponse(str(static_path / "index.html"))

@app.post("/upload")
async def upload_file(file: UploadFile = FastAPIFile(...)):
    try:
        dest = UPLOAD_DIR / file.filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(file.file, f)
        log.info(f"File uploaded successfully: {dest}")
        return {"absolute_path": str(dest.resolve()), "filename": file.filename}
    except Exception as e:
        log.error(f"Upload processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        import time
        start = time.time()
        reply, intent, tool = orchestrate(
            user_input=req.message,
            client=client,
            cfg=config,
            short_term=short_term,
            long_term=long_term,
            tool_registry=TOOL_REGISTRY,
            search_history=search_history
        )
        elapsed = round(time.time() - start, 2)
        final_reply = build_response(reply, intent, tool, elapsed, config)

        if len(current_session["messages"]) == 0:
            current_session["title"] = generate_title(req.message)

        current_session["messages"].append({
            "role": "user",
            "text": req.message,
            "intent": None,
            "tool": None,
            "elapsed": None,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        current_session["messages"].append({
            "role": "agent",
            "text": final_reply,
            "intent": intent,
            "tool": tool,
            "elapsed": elapsed,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        save_session()

        return {
            "reply": final_reply,
            "intent": intent,
            "tool": tool,
            "elapsed": elapsed,
            "tokens": config.session_token_count
        }
    except Exception as e:
        log.error(f"Chat endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memory")
def get_memory():
    return {
        "short_term": short_term.summary(),
        "long_term_count": long_term.count(),
        "memory_hits": config.memory_hits,
        "turns": config.total_turns
    }

@app.get("/tools")
def get_tools():
    return {
        name: meta["description"]
        for name, meta in TOOL_REGISTRY.items()
    }

@app.get("/stats")
def get_stats():
    avg_times = {
        intent: round(sum(times) / len(times), 2)
        for intent, times in config.response_times.items() if times
    }
    return {
        "session_id": config.session_id,
        "turns": config.total_turns,
        "tokens": config.session_token_count,
        "tool_calls": config.tool_call_count,
        "searches": config.search_count,
        "memory_hits": config.memory_hits,
        "intent_counts": config.intent_counts,
        "avg_response_times": avg_times
    }

@app.get("/search/history")
def get_search_history():
    return {"history": search_history.get_all()}

@app.get("/calendar")
def get_calendar():
    return {"upcoming": calendar.upcoming_events(n=10)}

@app.post("/calendar/add")
def add_calendar_event(req: CalendarAddRequest):
    result = calendar.add_event(req.title, req.date, req.time, req.description)
    return {"result": result}

@app.delete("/calendar/{event_id}")
def delete_calendar_event(event_id: str):
    result = calendar.delete_event(event_id)
    return {"result": result}

@app.post("/clear")
def clear_memory():
    short_term.clear()
    long_term.clear()
    log.info("Memory cleared via API")
    return {"status": "All memory cleared"}

@app.get("/sessions")
def list_sessions():
    sessions = []
    for f in sorted(SESSIONS_PATH.glob("session_*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            sessions.append({
                "id": data.get("id"),
                "title": data.get("title", "Untitled"),
                "created_at": data.get("created_at", ""),
                "message_count": len(data.get("messages", []))
            })
        except Exception:
            continue
    return {"sessions": sessions}

@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    data = load_session_file(session_id)
    if not data:
        raise HTTPException(status_code=404, detail="Session not found")
    return data

@app.post("/sessions/new")
def new_session():
    sid = init_new_session()
    short_term.clear()
    config.total_turns = 0
    config.session_token_count = 0
    config.tool_call_count = 0
    config.search_count = 0
    config.memory_hits = 0
    config.intent_counts = {
        "chat": 0, "tool": 0, "search": 0,
        "memory_recall": 0, "file_analysis": 0
    }
    config.response_times = {
        "chat": [], "tool": [], "search": [],
        "memory_recall": [], "file_analysis": []
    }
    log.info(f"New session started: {sid}")
    return {"session_id": sid}

@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    path = session_file(session_id)
    if path.exists():
        path.unlink()
        log.info(f"Session deleted: {session_id}")
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/sessions/current/id")
def get_current_session_id():
    return {"session_id": current_session["id"]}

@app.get("/export")
def export_session():
    try:
        export_path = Path(EXPORT_PATH)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        summary = build_session_summary(config)
        history = short_term.export()
        content = f"SESSION EXPORT\n{'='*50}\n{summary}\n\n{'='*50}\nCONVERSATION HISTORY\n{'='*50}\n{history}"
        export_path.write_text(content, encoding="utf-8")
        return FileResponse(
            path=str(export_path),
            filename=f"session_{config.session_id}.txt",
            media_type="text/plain"
        )
    except Exception as e:
        log.error(f"Export failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))