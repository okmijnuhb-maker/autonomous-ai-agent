// script.js
const API = '';
let currentSessionId = null;
let selectedFileObject = null; // ChatGPT-style file upload state tracker

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  loadTheme();
  loadStats();
  loadTools();
  loadMemory();
  loadSearchHistory();
  loadCalendar();
  loadSessions();
});

// ============================================================
// FILE UPLOAD HANDLERS
// ============================================================
function handleFileSelect() {
  const fileInput = document.getElementById('fileUploadInput');
  if (fileInput.files.length === 0) return;
  
  selectedFileObject = fileInput.files[0];
  document.getElementById('previewFileName').textContent = `📄 ${selectedFileObject.name}`;
  document.getElementById('filePreview').style.display = 'flex';
}

function clearSelectedFile() {
  selectedFileObject = null;
  document.getElementById('fileUploadInput').value = '';
  document.getElementById('filePreview').style.display = 'none';
}

// ============================================================
// SESSION MANAGEMENT
// ============================================================
async function loadSessions() {
  try {
    const res = await fetch(`${API}/sessions`);
    const data = await res.json();
    const list = document.getElementById('sessionList');
    
    if (!data.sessions || data.sessions.length === 0) {
      list.innerHTML = `<div class="session-empty">No past conversations yet.<br>Start chatting to save your first session.</div>`;
      const idRes = await fetch(`${API}/sessions/current/id`);
      const idData = await idRes.json();
      currentSessionId = idData.session_id;
      renderWelcome();
      return;
    }
    
    const idRes = await fetch(`${API}/sessions/current/id`);
    const idData = await idRes.json();
    currentSessionId = idData.session_id;
    
    list.innerHTML = data.sessions.map(s => `
      <div class="session-item ${s.id === currentSessionId ? 'active' : ''}" 
           id="session-${s.id}" 
           onclick="openSession('${s.id}')">
        <div class="session-item-info">
          <div class="session-item-title">${escapeHtml(s.title)}</div>
          <div class="session-item-meta">
            <span>${s.created_at}</span>
            <span>${s.message_count} messages</span>
          </div>
        </div>
        <button class="session-delete-btn" 
                onclick="event.stopPropagation(); deleteSession('${s.id}')" 
                title="Delete">&#x2715;</button>
      </div>
    `).join('');
    
    const current = data.sessions.find(s => s.id === currentSessionId);
    if (current && current.message_count > 0) {
      await openSession(currentSessionId, false);
    } else {
      renderWelcome();
    }
  } catch (err) {
    console.error('Sessions load failed:', err);
    renderWelcome();
  }
}

async function openSession(sessionId, updateSidebar = true) {
  try {
    const res = await fetch(`${API}/sessions/${sessionId}`);
    const data = await res.json();
    currentSessionId = sessionId;
    
    const history = document.getElementById('chatHistory');
    history.innerHTML = '';
    
    if (!data.messages || data.messages.length === 0) {
      renderWelcome();
    } else {
      data.messages.forEach(msg => {
        appendMessage(
          msg.role,
          msg.text,
          msg.intent || 'chat',
          msg.tool || null,
          msg.elapsed || null
        );
      });
    }
    
    if (updateSidebar) {
      document.querySelectorAll('.session-item').forEach(el => {
        el.classList.remove('active');
      });
      const active = document.getElementById(`session-${sessionId}`);
      if (active) active.classList.add('active');
    }
  } catch (err) {
    console.error('Open session failed:', err);
  }
}

async function newSession() {
  try {
    const res = await fetch(`${API}/sessions/new`, { method: 'POST' });
    const data = await res.json();
    currentSessionId = data.session_id;
    
    const history = document.getElementById('chatHistory');
    history.innerHTML = '';
    
    clearSelectedFile();
    renderWelcome();
    loadSessions();
    loadStats();
    loadMemory();
  } catch (err) {
    console.error('New session failed:', err);
  }
}

async function deleteSession(sessionId) {
  if (!confirm('Delete this conversation?')) return;
  try {
    await fetch(`${API}/sessions/${sessionId}`, { method: 'DELETE' });
    if (sessionId === currentSessionId) {
      await newSession();
    } else {
      loadSessions();
    }
  } catch (err) {
    console.error('Delete session failed:', err);
  }
}

// ============================================================
// WELCOME MESSAGE
// ============================================================
function renderWelcome() {
  const history = document.getElementById('chatHistory');
  const chips = [
    'What is machine learning?',
    'What time is it?',
    'Weather in Hyderabad',
    'Convert 100 km to miles',
    'Search latest AI news'
  ];
  history.innerHTML = `
    <div class="welcome-msg">
      <h2>Autonomous AI Agent</h2>
      <p>Ask me anything. I can search the web, use tools, recall memory, analyze files, and more.</p>
      <div class="welcome-chips">
        ${chips.map(c => `<div class="welcome-chip" onclick="chipSend('${c}')">${c}</div>`).join('')}
      </div>
    </div>
  `;
}

function chipSend(text) {
  document.getElementById('chatInput').value = text;
  sendMessage();
}

// ============================================================
// SEND MESSAGE
// ============================================================
async function sendMessage() {
  const input = document.getElementById('chatInput');
  let message = input.value.trim();
  
  if (!message && !selectedFileObject) return;

  let finalPayloadMessage = message;

  if (selectedFileObject) {
    try {
      const fileName = selectedFileObject.name.toLowerCase();
      
      if (fileName.endsWith('.pdf')) {
        const formData = new FormData();
        formData.append("file", selectedFileObject);
        document.getElementById('previewFileName').textContent = `⏳ Parsing PDF...`;
        const uploadRes = await fetch(`${API}/upload`, { method: "POST", body: formData });
        const uploadData = await uploadRes.json();
        finalPayloadMessage = `PDF_PATH:${uploadData.absolute_path}||||USER_REQUEST:${message || "Summarize this file"}`;
      
      } else if (fileName.endsWith('.csv')) {
        const formData = new FormData();
        formData.append("file", selectedFileObject);
        const uploadRes = await fetch(`${API}/upload`, { method: "POST", body: formData });
        const uploadData = await uploadRes.json();
        finalPayloadMessage = `analyze this CSV ${uploadData.absolute_path}`;
      
      } else {
        const formData = new FormData();
        formData.append("file", selectedFileObject);
        const uploadRes = await fetch(`${API}/upload`, { method: "POST", body: formData });
        const uploadData = await uploadRes.json();
        finalPayloadMessage = `read this file ${uploadData.absolute_path}`;
      }

    } catch (err) {
      console.error("File extraction failed:", err);
    }
  }

  const fileAttachedThisTurn = selectedFileObject;
  const userDisplayPromptText = message;
  input.value = '';
  clearSelectedFile();

  input.disabled = true;
  document.querySelector('.btn-send-inside').disabled = true;
  document.querySelector('.btn-attach-inside').disabled = true;
  
  const welcome = document.querySelector('.welcome-msg');
  if (welcome) welcome.remove();
  
  const bubbleText = fileAttachedThisTurn 
    ? `📁 Attached File: ${fileAttachedThisTurn.name}\n${userDisplayPromptText || "Summarize this file"}` 
    : userDisplayPromptText;
    
  appendMessage('user', bubbleText, null, null, null);
  showTyping(true);
  
  try {
    const res = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: finalPayloadMessage })
    });
    const data = await res.json();
    showTyping(false);
    
    appendMessage('agent', data.reply, data.intent, data.tool, data.elapsed);
    loadMemory();
    loadStats();
    loadSessions();
    if (data.intent === 'search') loadSearchHistory();
  } catch (err) {
    showTyping(false);
    appendMessage('agent', 'Connection error. Make sure the server is running.', 'chat', null, null);
  } finally {
    input.disabled = false;
    document.querySelector('.btn-send-inside').disabled = false;
    document.querySelector('.btn-attach-inside').disabled = false;
    input.focus();
  }
}

// ============================================================
// APPEND MESSAGE
// ============================================================
function appendMessage(role, text, intent, tool, elapsed) {
  const history = document.getElementById('chatHistory');
  const msg = document.createElement('div');
  msg.className = `message ${role}`;
  
  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';
  
  if (role === 'agent') {
    bubble.innerHTML = renderMarkdown(text);
  } else {
    bubble.textContent = text;
  }
  msg.appendChild(bubble);
  
  if (role === 'agent' && intent) {
    const meta = document.createElement('div');
    meta.className = 'message-meta';

    const badge = document.createElement('span');
    badge.className = `intent-badge badge-${intent}`;
    badge.textContent = badgeLabel(intent, tool);
    meta.appendChild(badge);

    if (elapsed !== null) {
      const time = document.createElement('span');
      time.textContent = `${elapsed}s`;
      meta.appendChild(time);
    }

    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-btn';
    copyBtn.textContent = 'Copy';
    copyBtn.onclick = () => copyMessage(copyBtn, text);
    meta.appendChild(copyBtn);

    msg.appendChild(meta);
  }
  
  history.appendChild(msg);
  autoScroll();
}

function badgeLabel(intent, tool) {
  if (intent === 'tool' && tool) return tool.replace('_', ' ');
  const labels = {
    chat:           'chat',
    search:         'web search',
    memory_recall:  'memory recall',
    file_analysis:  'file analysis'
  };
  return labels[intent] || intent;
}

// ============================================================
// TYPING INDICATOR
// ============================================================
function showTyping(show) {
  const el = document.getElementById('typingIndicator');
  el.classList.toggle('active', show);
  if (show) autoScroll();
}

// ============================================================
// AUTO SCROLL
// ============================================================
function autoScroll() {
  const history = document.getElementById('chatHistory');
  history.scrollTop = history.scrollHeight;
}

// ============================================================
// LOAD STATS
// ============================================================
async function loadStats() {
  try {
    const res = await fetch(`${API}/stats`);
    const data = await res.json();
    
    document.getElementById('sessionId').textContent = `Session: ${data.session_id}`;
    document.getElementById('tokenCount').textContent = data.tokens.toLocaleString();
    document.getElementById('turnCount').textContent = data.turns;
    document.getElementById('toolCalls').textContent = data.tool_calls;
    document.getElementById('searches').textContent = data.searches;
    renderIntentBreakdown(data.intent_counts);
  } catch (err) {
    console.error('Stats load failed:', err);
  }
}

// ============================================================
// INTENT BREAKDOWN OVERVIEW
// ============================================================
function renderIntentBreakdown(counts) {
  const grid = document.getElementById('intentBreakdown');
  grid.innerHTML = Object.entries(counts).map(([intent, count]) => `
    <div class="intent-item">
      <span>${count}</span>
      ${intent.replace('_', ' ')}
    </div>
  `).join('');
}

// ============================================================
// LOAD MEMORY
// ============================================================
async function loadMemory() {
  try {
    const res = await fetch(`${API}/memory`);
    const data = await res.json();
    
    document.getElementById('shortTerm').textContent = data.short_term;
    document.getElementById('longTerm').textContent = `${data.long_term_count} entries`;
    document.getElementById('memoryHits').textContent = data.memory_hits;
  } catch (err) {
    console.error('Memory load failed:', err);
  }
}

// ============================================================
// LOAD TOOLS
// ============================================================
async function loadTools() {
  try {
    const res = await fetch(`${API}/tools`);
    const data = await res.json();
    const list = document.getElementById('toolList');
    
    list.innerHTML = Object.keys(data).map(name => `
      <div title="${data[name]}">${name.replace('_', ' ')}</div>
    `).join('');
  } catch (err) {
    console.error('Tools load failed:', err);
  }
}

// ============================================================
// LOAD SEARCH HISTORY
// ============================================================
async function loadSearchHistory() {
  try {
    const res = await fetch(`${API}/search/history`);
    const data = await res.json();
    const container = document.getElementById('searchHistory');
    
    if (!data.history || data.history.length === 0) {
      container.innerHTML = `<div class="empty-state">No searches yet.</div>`;
      return;
    }
    
    const recent = [...data.history].reverse().slice(0, 10);
    container.innerHTML = recent.map(item => `
      <div class="scroll-list-item">
        <div class="item-label">${escapeHtml(item.query)}</div>
        <div class="item-meta">${item.timestamp} &middot; ${item.result_count} results</div>
      </div>
    `).join('');
  } catch (err) {
    console.error('Search history load failed:', err);
  }
}

// ============================================================
// LOAD CALENDAR
// ============================================================
async function loadCalendar() {
  try {
    const res = await fetch(`${API}/calendar`);
    const data = await res.json();
    const container = document.getElementById('calendarEvents');
    const raw = data.upcoming || '';
    const lines = raw.split('\n').filter(l => l.trim().startsWith('['));
    
    if (lines.length === 0) {
      container.innerHTML = `<div class="empty-state">No upcoming events.</div>`;
      return;
    }
    
    container.innerHTML = lines.map(line => {
      const idMatch = line.match(/\[([^\]]+)\]/);
      const id = idMatch ? idMatch[1] : '';
      const text = line.replace(/\[[^\]]+\]/, '').trim();
      return `
        <div class="scroll-list-item" style="display:flex;justify-content:space-between;align-items:center;">
          <div style="min-width: 0; flex: 1;">
            <div class="item-label">${escapeHtml(text)}</div>
          </div>
          <button onclick="deleteEvent('${id}')" style="
            background: none;
            border: 1px solid #FCA5A5;
            border-radius: 6px;
            color: var(--danger);
            font-size: 11px;
            padding: 2px 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.2s;
            flex-shrink: 0;
            margin-left: 8px;
          " onmouseover="this.style.background='#FEF2F2'" 
             onmouseout="this.style.background='none'">
            Remove
          </button>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Calendar load failed:', err);
  }
}

// ============================================================
// ADD EVENT
// ============================================================
async function addEvent() {
  const title = document.getElementById('evtTitle').value.trim();
  const date  = document.getElementById('evtDate').value;
  const time  = document.getElementById('evtTime').value;
  const desc  = document.getElementById('evtDesc').value.trim();
  
  if (!title || !date || !time) {
    alert('Title, date, and time are required.');
    return;
  }
  try {
    await fetch(`${API}/calendar/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, date, time, description: desc })
    });
    document.getElementById('evtTitle').value = '';
    document.getElementById('evtDate').value  = '';
    document.getElementById('evtTime').value  = '';
    document.getElementById('evtDesc').value  = '';
    loadCalendar();
  } catch (err) {
    console.error('Add event failed:', err);
  }
}

// ============================================================
// DELETE EVENT
// ============================================================
async function deleteEvent(eventId) {
  try {
    await fetch(`${API}/calendar/${eventId}`, { method: 'DELETE' });
    loadCalendar();
  } catch (err) {
    console.error('Delete event failed:', err);
  }
}

// ============================================================
// CLEAR MEMORY
// ============================================================
async function clearMemory() {
  if (!confirm('Clear all memory? This cannot be undone.')) return;
  try {
    await fetch(`${API}/clear`, { method: 'POST' });
    loadMemory();
    loadStats();
    appendMessage('agent', 'All memory has been cleared.', 'chat', null, null);
  } catch (err) {
    console.error('Clear memory failed:', err);
  }
}

// ============================================================
// EXPORT SESSION
// ============================================================
async function exportSession() {
  try {
    const res = await fetch(`${API}/export`);
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `session_export.txt`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    console.error('Export failed:', err);
  }
}

// ============================================================
// UTILS
// ============================================================
function escapeHtml(text) {
  const d = document.createElement('div');
  d.textContent = text;
  return d.innerHTML;
}

// ============================================================
// MARKDOWN RENDERING
// ============================================================
function renderMarkdown(text) {
  try {
    return marked.parse(text);
  } catch (err) {
    return text;
  }
}

// ============================================================
// DARK / LIGHT MODE
// ============================================================
function toggleTheme() {
  const body = document.body;
  const btn = document.getElementById('themeToggle');
  body.classList.toggle('dark');
  if (body.classList.contains('dark')) {
    btn.textContent = 'Light Mode';
    localStorage.setItem('theme', 'dark');
  } else {
    btn.textContent = 'Dark Mode';
    localStorage.setItem('theme', 'light');
  }
}

function loadTheme() {
  const saved = localStorage.getItem('theme');
  if (saved === 'dark') {
    document.body.classList.add('dark');
    document.getElementById('themeToggle').textContent = 'Light Mode';
  }
}

// ============================================================
// COPY BUTTON
// ============================================================
function copyMessage(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = 'Copied!';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = 'Copy';
      btn.classList.remove('copied');
    }, 2000);
  }).catch(err => {
    console.error('Copy failed:', err);
  });
}

// ============================================================
// VOICE INPUT
// ============================================================
let recognition = null;
let isListening = false;

function toggleVoice() {
  if (isListening) {
    stopVoice();
  } else {
    startVoice();
  }
}

function startVoice() {
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    alert('Voice input is not supported in this browser. Use Chrome or Edge.');
    return;
  }
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.lang = 'en-US';
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => {
    isListening = true;
    const micBtn = document.getElementById('micBtn');
    micBtn.classList.add('listening');
    micBtn.textContent = '⏹';
    document.getElementById('chatInput').placeholder = 'Listening...';
  };

  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    document.getElementById('chatInput').value = transcript;
    stopVoice();
    sendMessage();
  };

  recognition.onerror = (event) => {
    console.error('Voice error:', event.error);
    stopVoice();
  };

  recognition.onend = () => {
    stopVoice();
  };

  recognition.start();
}

function stopVoice() {
  isListening = false;
  const micBtn = document.getElementById('micBtn');
  if (micBtn) {
    micBtn.classList.remove('listening');
    micBtn.textContent = '🎤';
  }
  const chatInput = document.getElementById('chatInput');
  if (chatInput) {
    chatInput.placeholder = 'Ask anything...';
  }
  if (recognition) {
    recognition.stop();
    recognition = null;
  }
}