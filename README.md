# Autonomous AI Agent

A Multi-Capability Autonomous AI Agent with conversational memory, 14 tools, real-time web search, file handling, and a ChatGPT-style web interface.

**Live Demo:** https://autonomous-ai-agent-gdcx.onrender.com

> First visit may take 30-60 seconds to wake up on Render free tier.

> Note: Conversation history resets if the server restarts (Render free tier limitation). All features work fully within an active session.

---

## Tech Stack

| Component | Technology |
|---|---|
| LLM | Groq API — llama-3.3-70b-versatile |
| Backend | FastAPI + Uvicorn |
| Memory | ChromaDB + short-term deque buffer |
| Storage | Local JSON files + ChromaDB persistent vector store |
| Search | DuckDuckGo (ddgs) |
| Frontend | HTML, CSS, JavaScript |
| Deployment | Render |

---

## Setup

### 1. Clone the repository
git clone https://github.com/okmijnuhb-maker/autonomous-ai-agent.git

cd autonomous-ai-agent

### 2. Install dependencies
python -m pip install -r requirements.txt

### 3. Create .env file in project root
GROQ_API_KEY=your_groq_api_key_here
Get a free key at https://console.groq.com

### 4. Run locally
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

### 5. Open in browser
http://localhost:8000

---

## Capabilities

This agent was built around 3 core capability types:

### 1. Conversational AI
- Multi-turn chat with context retention
- Short-term deque buffer for recent messages
- ChromaDB long-term vector memory with semantic recall across sessions

### 2. Task Automation
- 10 core tools — calculator, weather, datetime, unit converter, dictionary, Wikipedia, web search, file reader, CSV analyzer, system info
- 4 additional utility tools — currency converter, text translator, QR code generator, password generator
- Email tool and calendar management
- File upload and analysis — PDF, DOCX, CSV, TXT, JSON

### 3. Web Search and Research
- Real-time web search via DuckDuckGo
- Multi-query planning and source ranking
- Result summarization with confirmed vs uncertain facts
- Follow-up detection with context injection
- News-specific search — separates breaking news from general results
- Persistent search history

---

## Features

- Multi-turn chat with persistent memory across sessions
- 14 tools — calculator, weather, datetime, unit converter, dictionary, Wikipedia, web search, file reader, CSV analyzer, system info, currency converter, text translator, QR code generator, password generator
- Real-time web search with source ranking and summarization
- Streaming responses — replies appear word by word like ChatGPT
- File upload and analysis — PDF, DOCX, CSV, TXT
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

## Tools (14 total)

calculator, wikipedia, web_search, file_reader, datetime_tool, unit_converter, dictionary, weather, csv_analyzer, system_info, currency_converter, text_translator, qr_generator, password_generator

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
| /chat | POST | Send message, get reply |
| /chat/stream | POST | Streaming chat response |
| /memory | GET | Memory stats |
| /tools | GET | List all tools |
| /stats | GET | Session performance stats |
| /search/history | GET | Past web searches |
| /calendar | GET | Upcoming events |
| /calendar/add | POST | Add event |
| /calendar/{id} | DELETE | Delete event |
| /sessions | GET | All past sessions |
| /sessions/new | POST | Start new session |
| /sessions/{id} | DELETE | Delete session |
| /upload | POST | Upload file |
| /export | GET | Export session |
| /clear | POST | Clear memory |
