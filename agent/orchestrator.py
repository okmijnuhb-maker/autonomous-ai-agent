# agent/orchestrator.py

import json
import time
import logging
from typing import Optional, Tuple
from agent.core import AgentConfig, MAX_RETRIES, RETRY_DELAY
from memory.short_term import ShortTermBuffer
from memory.long_term import LongTermMemory
from tools.file_handler import read_file, detect_file_type
from tools.web_search import run_search_pipeline, SearchHistoryManager

log = logging.getLogger(__name__)

def classify_intent(
    user_input: str,
    client,
    cfg: AgentConfig
) -> Tuple[str, Optional[str]]:
    # Force direct file analysis routing if browser-attached context markers are found
    if "[ATTACHED FILE CONTEXT:" in user_input or "[FILE_CONTENT_START]" in user_input:
        log.info("Direct file text markers intercepted — bypassing classifier routing")
        return "file_analysis", None

    prompt = (
        "Classify the user input into exactly one intent.\n\n"
        "Rules:\n"
        "- chat: greetings, general knowledge, explanations, opinions, how things work\n"
        "- tool: math calculations, current time/date, weather, unit conversion, word definitions, system info, wikipedia lookup, file reading\n"
        "- search: current events, news, recent developments, who currently holds a position, prices today, sports results, anything that changes frequently and needs live data\n"
        "- memory_recall: questions about what was said earlier, user's name, past conversation, 'what do you know about me'\n"
        "- file_analysis: user provides a file path, explicitly references an uploaded or attached file name, or asks to read/analyze a document data structure\n\n"
        "Examples:\n"
        "- 'what is 25 * 48' -> tool, calculator\n"
        "- 'what time is it' -> tool, datetime_tool\n"
        "- 'what time is it in London' -> search\n"
        "- 'current time in Tokyo' -> search\n"
        "- 'weather in Hyderabad' -> tool, weather\n"
        "- 'define cognition' -> tool, dictionary\n"
        "- 'who is the PM of India' -> search\n"
        "- 'latest AI news' -> search\n"
        "- 'who won IPL 2025' -> search\n"
        "- 'what is machine learning' -> chat\n"
        "- 'how does photosynthesis work' -> chat\n"
        "- 'what is my name' -> memory_recall\n"
        "- 'read file C:/path/file.txt' -> file_analysis\n\n"
        "Reply ONLY with JSON: {\"intent\": \"...\", \"tool\": \"...or null\"}\n"
        "Input: " + user_input
    )
    try:
        response = client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=64,
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        cfg.session_token_count += response.usage.total_tokens
        parsed = json.loads(raw)
        intent = parsed.get("intent", "chat")
        tool = parsed.get("tool", None)
        log.info(f"Intent classified: {intent} | tool: {tool}")
        return intent, tool
    except Exception as e:
        log.warning(f"Intent classification failed: {e} — defaulting to chat")
        return "chat", None

def handle_memory_recall(
    user_input: str,
    long_term: LongTermMemory,
    short_term: ShortTermBuffer,
    client,
    cfg: AgentConfig
) -> str:
    retrieved = long_term.query(user_input)
    if not retrieved:
        return handle_chat(user_input, short_term, client, cfg)
    context = "Relevant memory:\n" + "\n---\n".join(retrieved)
    augmented_system = cfg.system_prompt + f"\n\n{context}"
    messages = [{"role": "system", "content": augmented_system}]
    messages += short_term.get()
    messages.append({"role": "user", "content": user_input})
    cfg.memory_hits += 1
    log.info(f"Memory hit #{cfg.memory_hits}")
    return _call_llm(messages, client, cfg)

def handle_tool(
    user_input: str,
    tool_name: str,
    tool_registry: dict,
    short_term: ShortTermBuffer,
    client,
    cfg: AgentConfig
) -> str:
    if tool_name not in tool_registry:
        log.warning(f"Tool not found: {tool_name} — falling back to chat")
        return handle_chat(user_input, short_term, client, cfg)
    try:
        tool_result = tool_registry[tool_name]["fn"](user_input)
        cfg.tool_call_count += 1
        log.info(f"Tool call #{cfg.tool_call_count}: {tool_name}")
        messages = [
            {"role": "system", "content": cfg.system_prompt},
            {"role": "user", "content": user_input},
            {"role": "assistant", "content": f"Tool result: {tool_result}"},
            {"role": "user", "content": "Summarize this tool result clearly and concisely."}
        ]
        return _call_llm(messages, client, cfg)
    except Exception as e:
        log.error(f"Tool handler failed: {e}")
        return handle_chat(user_input, short_term, client, cfg)

def handle_search(
    user_input: str,
    search_history: SearchHistoryManager,
    client,
    cfg: AgentConfig
) -> str:
    try:
        result = run_search_pipeline(
            user_input=user_input,
            client=client,
            model=cfg.model,
            system_prompt=cfg.system_prompt,
            history=search_history
        )
        cfg.search_count += 1
        log.info(f"Search #{cfg.search_count} completed")
        return result
    except Exception as e:
        log.error(f"Search handler failed: {e}")
        return f"Search failed: {e}"

def handle_file_analysis(
    user_input: str,
    short_term: ShortTermBuffer,
    client,
    cfg: AgentConfig
) -> str:
    # Scenario A: Direct file content injection from browser
    if "[FILE_CONTENT_START]" in user_input and "[FILE_CONTENT_END]" in user_input:
        log.info("Processing direct file content from browser")
        try:
            file_name = ""
            if "[FILE_NAME:" in user_input:
                file_name = user_input.split("[FILE_NAME:")[1].split("]")[0]
            
            content = user_input.split("[FILE_CONTENT_START]")[1].split("[FILE_CONTENT_END]")[0].strip()
            user_request = user_input.split("[FILE_CONTENT_END]")[1].strip()
            if user_request.startswith("User Request:"):
                user_request = user_request.replace("User Request:", "").strip()
            
            messages = [
                {"role": "system", "content": cfg.system_prompt},
                {"role": "user", "content": f"File name: {file_name}\n\nFile content:\n{content[:12000]}\n\nInstruction: {user_request}"}
            ]
            return _call_llm(messages, client, cfg)
        except Exception as e:
            log.error(f"Direct content processing failed: {e}")
            return handle_chat(user_input, short_term, client, cfg)

    # Scenario B: PDF explicit binary data stream handler (via pdfplumber)
    if "PDF_PATH:" in user_input and "||||" in user_input:
        log.info("Processing absolute internal server PDF file parsing token marker target")
        try:
            parts = user_input.split("||||")
            filepath = parts[0].replace("PDF_PATH:", "").strip()
            user_instruction = parts[1].replace("USER_REQUEST:", "").strip()
            
            import pdfplumber
            log.info(f"Extracting text via pdfplumber: {filepath}")
            extracted_pages = []
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        extracted_pages.append(page_text)
            file_content = "\n".join(extracted_pages).strip()
            file_content = file_content[:12000]
            
            if not file_content:
                return "The system successfully uploaded your PDF, but no plain text information could be read. Ensure it is not an image-only scanned document."

            messages = [
                {"role": "system", "content": cfg.system_prompt},
                {"role": "user", "content": f"Document context data extracted from upload file:\n\n{file_content}\n\nUser Question/Instruction: {user_instruction}"}
            ]
            return _call_llm(messages, client, cfg)
            
        except Exception as upload_read_err:
            log.error(f"Internal file loader pipeline execution crash: {upload_read_err}")
            return f"An internal system error occurred processing your file stream data payload: {str(upload_read_err)}"

    # Scenario C: Shorthand text path strings fallback
    words = user_input.replace(",", " ").split()
    filepath = None
    for word in words:
        cleaned_word = word.strip("'\"`()[]*")
        if "." in cleaned_word and ("/" in cleaned_word or "\\" in cleaned_word):
            filepath = cleaned_word
            break

    if not filepath:
        return handle_chat(user_input, short_term, client, cfg)
        
    try:
        file_content = read_file(filepath)
        messages = [
            {"role": "system", "content": cfg.system_prompt},
            {"role": "user", "content": f"File content from local directory path:\n\n{file_content}\n\nRequest: {user_input}"}
        ]
        return _call_llm(messages, client, cfg)
    except Exception as e:
        return f"Could not read the file signature provided: {str(e)}"

def handle_chat(
    user_input: str,
    short_term: ShortTermBuffer,
    client,
    cfg: AgentConfig
) -> str:
    messages = [{"role": "system", "content": cfg.system_prompt}]
    messages += short_term.get()
    messages.append({"role": "user", "content": user_input})
    return _call_llm(messages, client, cfg)

def _call_llm(messages: list, client, cfg: AgentConfig) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=cfg.model,
                messages=messages,
                max_tokens=cfg.max_tokens,
                temperature=cfg.temperature
            )
            reply = response.choices[0].message.content.strip()
            cfg.session_token_count += response.usage.total_tokens
            return reply
        except Exception as e:
            log.warning(f"LLM call attempt {attempt + 1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
    log.error("All LLM retry attempts failed")
    return "I was unable to process your request. Please try again."

def orchestrate(
    user_input: str,
    client,
    cfg: AgentConfig,
    short_term: ShortTermBuffer,
    long_term: LongTermMemory,
    tool_registry: dict,
    search_history: SearchHistoryManager
) -> Tuple[str, str, Optional[str]]:
    start_time = time.time()
    intent, tool = classify_intent(user_input, client, cfg)
    cfg.intent_counts[intent] = cfg.intent_counts.get(intent, 0) + 1

    try:
        if intent == "memory_recall":
            reply = handle_memory_recall(user_input, long_term, short_term, client, cfg)
        elif intent == "tool" and tool:
            reply = handle_tool(user_input, tool, tool_registry, short_term, client, cfg)
        elif intent == "search":
            reply = handle_search(user_input, search_history, client, cfg)
        elif intent == "file_analysis":
            reply = handle_file_analysis(user_input, short_term, client, cfg)
        else:
            reply = handle_chat(user_input, short_term, client, cfg)
    except Exception as e:
        log.error(f"Orchestrator error: {e} — falling back to chat")
        reply = handle_chat(user_input, short_term, client, cfg)
        intent = "chat"
        tool = None

    elapsed = round(time.time() - start_time, 2)
    cfg.response_times[intent].append(elapsed)
    cfg.total_turns += 1

    short_term.add("user", user_input)
    short_term.add("assistant", reply)
    long_term.store(
        memory_id=f"turn_{cfg.total_turns}_{int(time.time())}",
        text=f"User: {user_input}\nAssistant: {reply}",
        metadata={"turn": cfg.total_turns, "timestamp": int(time.time())}
    )

    log.info(f"Orchestrator complete — intent: {intent} | time: {elapsed}s")
    return reply, intent, tool