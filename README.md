# Autonomous AI Agent

A Multi-Capability Autonomous AI Agent with conversational memory, 10 tools, 
real-time web search, file handling, and a ChatGPT-style web interface.

**Live Demo:** https://autonomous-ai-agent-gdcx.onrender.com
First visit may take 30-60 seconds to wake up on Render free tier.

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Groq API — llama-3.3-70b-versatile |
| Backend | FastAPI + Uvicorn |
| Memory | ChromaDB + short-term deque buffer |
| Search | DuckDuckGo (ddgs) |
| Frontend | HTML, CSS, JavaScript |
| Deployment | Render |

---

## Setup

### 1. Clone the repository
```bash
git clone https://github.com/okmijnuhb-maker/autonomous-ai-agent.git
cd autonomous-ai-agent
```

### 2. Install dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. Create .env file in project root
GROQ_API_KEY=your_groq_api_key_here
Get a free key at https://console.groq.com

### 4. Run locally
```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open in browser
http://localhost:8000

---

## Capabilities

This agent was built around 3 core capability types:

**1. Conversational AI**
- Multi-turn chat with context retention
- Short-term deque buffer for recent messages
- ChromaDB long-term vector memory with semantic recall across sessions

**2. Task Automation**
- 10 tools — calculator, weather, datetime, unit converter, dictionary,
  Wikipedia, web search, file reader, CSV analyzer, system info
- Email tool and calendar management
- File upload and analysis — PDF, CSV, TXT, JSON

**3. Web Search and Research**
- Real-time web search via DuckDuckGo
- Multi-query planning and source ranking
- Result summarization with confirmed vs uncertain facts
- Follow-up detection with context injection
- Persistent search history

---

## Features

- Multi-turn chat with persistent memory across sessions
- 10 tools — calculator, weather, datetime, unit converter, dictionary,
  Wikipedia, web search, file reader, CSV analyzer, system info
- Real-time web search with source ranking and summarization
- File upload and analysis — PDF, CSV, TXT
- ChatGPT-style session history — save, reopen, delete conversations
- Calendar management — add, delete, upcoming events
- Voice input — speak your questions directly
- Markdown rendering — formatted responses with headers, bullets, code blocks
- Dark/Light mode toggle
- Copy button on every agent message
- Session export to txt file
- Intent classification — chat, tool, search, memory recall, file analysis
- Performance tracking — tokens, response times, tool calls per session

---


## Notebooks

| Notebook | What it builds |
|---|---|
| 01_basic_chatbot | Groq API, conversation manager, retry logic |
| 02_memory_agent | Short-term buffer + ChromaDB long-term memory |
| 03_tool_calling | 10 tools with registry and executor |
| 04_web_search_agent | Full search pipeline with ranking and summarization |
| 05_full_agent | Complete integration of all modules |

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/chat` | POST | Send message, get reply |
| `/memory` | GET | Memory stats |
| `/tools` | GET | List all tools |
| `/stats` | GET | Session performance stats |
| `/search/history` | GET | Past web searches |
| `/calendar` | GET | Upcoming events |
| `/calendar/add` | POST | Add event |
| `/calendar/{id}` | DELETE | Delete event |
| `/sessions` | GET | All past sessions |
| `/sessions/new` | POST | Start new session |
| `/sessions/{id}` | DELETE | Delete session |
| `/upload` | POST | Upload file |
| `/export` | GET | Export session |
| `/clear` | POST | Clear memory |
