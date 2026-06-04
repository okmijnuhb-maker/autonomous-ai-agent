# memory/long_term.py

import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

log = logging.getLogger(__name__)

CHROMA_PATH = "C:/educational files/advanced_agent/memory/chroma_store"
COLLECTION_NAME = "agent_memory"
MEMORY_RESULTS = 3


class LongTermMemory:
    def __init__(self, path: str = CHROMA_PATH):
        Path(path).mkdir(parents=True, exist_ok=True)
        self.path = path
        self.client = chromadb.PersistentClient(path=path)
        self.ef = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self.ef
        )
        log.info(f"Long term memory ready — stored entries: {self.collection.count()}")

    def store(self, memory_id: str, text: str, metadata: Optional[Dict] = None) -> None:
        try:
            self.collection.upsert(
                ids=[memory_id],
                documents=[text],
                metadatas=[metadata or {"timestamp": int(datetime.now().timestamp())}]
            )
            log.debug(f"Memory stored — id: {memory_id} | length: {len(text)}")
        except Exception as e:
            log.error(f"Memory store failed: {e}")

    def query(self, query_text: str, n_results: int = MEMORY_RESULTS) -> List[str]:
        try:
            count = self.collection.count()
            if count == 0:
                return []
            n = min(n_results, count)
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n
            )
            documents = results["documents"][0] if results["documents"] else []
            log.info(f"Memory query — '{query_text[:50]}' — {len(documents)} results")
            return documents
        except Exception as e:
            log.error(f"Memory query failed: {e}")
            return []

    def get_all(self) -> List[Dict]:
        try:
            results = self.collection.get()
            entries = []
            for i, doc_id in enumerate(results["ids"]):
                entries.append({
                    "id": doc_id,
                    "text": results["documents"][i],
                    "metadata": results["metadatas"][i]
                })
            log.info(f"Retrieved all — {len(entries)} entries")
            return entries
        except Exception as e:
            log.error(f"Get all failed: {e}")
            return []

    def delete(self, memory_id: str) -> str:
        try:
            self.collection.delete(ids=[memory_id])
            log.info(f"Memory deleted — id: {memory_id}")
            return f"Memory entry deleted — ID: {memory_id}"
        except Exception as e:
            log.error(f"Memory delete failed: {e}")
            return f"Memory delete error: {e}"

    def clear(self) -> None:
        try:
            self.client.delete_collection(COLLECTION_NAME)
            self.collection = self.client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self.ef
            )
            log.info("Long term memory cleared")
        except Exception as e:
            log.error(f"Memory clear failed: {e}")

    def count(self) -> int:
        try:
            return self.collection.count()
        except Exception:
            return 0

    def summary(self) -> str:
        return f"Long term: {self.count()} entries | path: {self.path}"