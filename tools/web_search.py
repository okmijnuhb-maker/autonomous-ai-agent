# tools/web_search.py

import re
import json
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Tuple
from pathlib import Path
from ddgs import DDGS

log = logging.getLogger(__name__)

MAX_RESULTS_PER_QUERY = 4
MAX_BODY_LENGTH = 500
MAX_TOOL_OUTPUT = 500
HISTORY_PATH = "C:/educational files/advanced_agent/memory/search_history.json"

CREDIBLE_DOMAINS = {
    "wikipedia.org": 10, "bbc.com": 9, "reuters.com": 9,
    "nature.com": 9, "sciencedirect.com": 9, "arxiv.org": 8,
    "techcrunch.com": 7, "theverge.com": 7, "wired.com": 7,
    "github.com": 7, "stackoverflow.com": 6, "medium.com": 5
}


def plan_queries(user_input: str, client, model: str) -> List[str]:
    prompt = (
        "Break the following question into 2-3 specific search queries. "
        "Return ONLY a JSON array of strings, nothing else.\n"
        f"Question: {user_input}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=256,
            temperature=0.2
        )
        raw = response.choices[0].message.content.strip()
        queries = json.loads(raw)
        if isinstance(queries, list) and all(isinstance(q, str) for q in queries):
            log.info(f"Query planner generated {len(queries)} sub-queries")
            return queries
    except Exception as e:
        log.warning(f"Query planner failed: {e} — falling back to original input")
    return [user_input]


def run_search(queries: List[str]) -> List[Dict]:
    seen_urls = set()
    all_results = []
    for query in queries:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=MAX_RESULTS_PER_QUERY))
            log.info(f"Search executed: '{query}' — {len(results)} results")
            for r in results:
                url = r.get("href", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                all_results.append({
                    "title": r.get("title", "").strip(),
                    "body": r.get("body", "")[:MAX_BODY_LENGTH].strip(),
                    "url": url,
                    "query": query
                })
        except Exception as e:
            log.warning(f"Search failed for query '{query}': {e}")
    log.info(f"Total unique results: {len(all_results)}")
    return all_results


def extract_results(raw_results: List[Dict]) -> List[Dict]:
    extracted = []
    for r in raw_results:
        title = r.get("title", "").strip()
        body = re.sub(r'\s+', ' ', r.get("body", "").strip())
        url = r.get("url", "").strip()
        if not title or not body:
            continue
        extracted.append({
            "title": title,
            "body": body,
            "url": url,
            "query": r.get("query", ""),
            "word_count": len(body.split())
        })
    log.info(f"Extracted {len(extracted)} clean results")
    return extracted


def rank_sources(results: List[Dict]) -> List[Dict]:
    def score(r: Dict) -> int:
        url = r.get("url", "").lower()
        domain_score = next((pts for domain, pts in CREDIBLE_DOMAINS.items() if domain in url), 0)
        length_score = min(r.get("word_count", 0) // 10, 5)
        return domain_score + length_score
    ranked = sorted(results, key=score, reverse=True)
    if ranked:
        log.info(f"Top source: {ranked[0]['title'][:60]}")
    return ranked


def summarize_results(user_input: str, results: List[Dict], client, model: str, system_prompt: str) -> str:
    if not results:
        return "No results found to summarize."
    results_text = "\n\n".join([
        f"Source {i+1}: {r['title']}\nURL: {r['url']}\nContent: {r['body']}"
        for i, r in enumerate(results)
    ])
    prompt = (
    f"User question: {user_input}\n\n"
    f"Search results:\n{results_text}\n\n"
    "Give a direct, concise answer in 3-4 sentences maximum. "
    "Lead with the direct answer immediately — no preamble. "
    "Only mention sources if they add value. "
    "Do not list bullet points unless absolutely necessary. "
    "Do not repeat the same fact multiple times. "
    "If the answer is a simple fact, just state it clearly and stop."
)
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        log.error(f"Summarizer failed: {e}")
        return "Failed to generate summary."


def is_followup(user_input: str, last_query: Optional[str], client, model: str) -> Tuple[bool, str]:
    if not last_query:
        return False, ""
    prompt = (
        f"Previous search: {last_query}\n"
        f"New question: {user_input}\n"
        "Is this a follow-up? Reply ONLY with JSON: "
        "{\"is_followup\": true/false, \"reason\": \"one line\"}"
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=128,
            temperature=0.1
        )
        parsed = json.loads(response.choices[0].message.content.strip())
        result = parsed.get("is_followup", False)
        log.info(f"Follow-up detection: {result}")
        return result, parsed.get("reason", "")
    except Exception as e:
        log.warning(f"Follow-up detector failed: {e}")
        return False, ""


class SearchHistoryManager:
    def __init__(self, path: str = HISTORY_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.history: List[Dict] = self._load()
        log.info(f"Search history loaded — {len(self.history)} past searches")

    def _load(self) -> List[Dict]:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except Exception:
                return []
        return []

    def save(self, query: str, sub_queries: List[str], results: List[Dict], summary: str) -> None:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "query": query,
            "sub_queries": sub_queries,
            "result_count": len(results),
            "top_sources": [r["url"] for r in results[:3]],
            "summary": summary
        }
        self.history.append(entry)
        self.path.write_text(json.dumps(self.history, indent=2), encoding="utf-8")
        log.info(f"Search saved — total entries: {len(self.history)}")

    def get_last(self) -> Optional[Dict]:
        return self.history[-1] if self.history else None

    def get_all(self) -> List[Dict]:
        return self.history.copy()

    def clear(self) -> None:
        self.history.clear()
        self.path.write_text("[]", encoding="utf-8")
        log.info("Search history cleared")

    def summary(self) -> str:
        return f"Total searches stored: {len(self.history)}"


def run_search_pipeline(
    user_input: str,
    client,
    model: str,
    system_prompt: str,
    history: SearchHistoryManager
) -> str:
    last = history.get_last()
    last_query = last["query"] if last else None
    followup, _ = is_followup(user_input, last_query, client, model)

    augmented = user_input
    if followup and last:
        augmented = f"Previous context: {last['summary']}\n\nFollow-up: {user_input}"

    sub_queries = plan_queries(augmented, client, model)
    raw = run_search(sub_queries)
    extracted = extract_results(raw)
    ranked = rank_sources(extracted)
    summary = summarize_results(user_input, ranked, client, model, system_prompt)
    history.save(user_input, sub_queries, ranked, summary)
    return summary