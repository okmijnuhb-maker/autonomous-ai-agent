# Autonomous AI Agent

A Multi-Capability Autonomous AI Agent with conversational memory, 10 tools, real-time web search, file handling, and a ChatGPT-style web interface.

**Live Demo:** https://autonomous-ai-agent-gdcx.onrender.com

> First visit may take 30-60 seconds to wake up on Render free tier.

---

## Tech Stack

- **LLM:** Groq API — llama-3.3-70b-versatile
- **Backend:** FastAPI + Uvicorn
- **Memory:** ChromaDB + short-term deque buffer
- **Search:** DuckDuckGo (ddgs)
- **Frontend:** HTML, CSS, JavaScript
- **Deployment:** Render

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

## Features

- Multi-turn chat with persistent memory across sessions
- 10 tools — calculator, weather, datetime, unit converter, dictionary, Wikipedia, web search, file reader, CSV analyzer, system info
- Real-time web search with source ranking and summarization
- File upload and analysis — PDF, CSV, TXT
- ChatGPT-style session history — save, reopen, delete conversations
- Calendar management
- Session export

---

## Author

Charan — Capstone Project
