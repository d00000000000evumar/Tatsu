"""
Tatsu AI — Semantic Memory
=============================
Vector-based memory using ChromaDB for similarity search.
Enables Tatsu to find relevant past interactions and knowledge.
"""

import logging
from typing import Any

import config

logger = logging.getLogger("tatsu.memory.semantic")


class SemanticMemory:
    """
    Vector store for semantic similarity search.
    Uses ChromaDB to embed and retrieve contextually relevant memories.
    Falls back gracefully if ChromaDB is not available.
    """

    def __init__(self):
        self._collection = None
        self._client = None
        self._available = False

    async def initialize(self) -> bool:
        """Initialize ChromaDB. Returns False if unavailable."""
        try:
            import chromadb
            self._client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
            self._collection = self._client.get_or_create_collection(
                name="tatsu_memories",
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            logger.info(f"Semantic memory initialized ({self._collection.count()} entries)")
            return True
        except ImportError:
            logger.warning("ChromaDB not installed. Semantic memory disabled.")
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize semantic memory: {e}")
            return False

    @property
    def available(self) -> bool:
        return self._available

    def store(self, text: str, metadata: dict | None = None, doc_id: str | None = None) -> None:
        """Store a text with optional metadata for future retrieval."""
        if not self._available:
            return

        import uuid
        doc_id = doc_id or str(uuid.uuid4())

        try:
            self._collection.add(
                documents=[text],
                metadatas=[metadata or {}],
                ids=[doc_id],
            )
            logger.debug(f"Stored semantic memory: {text[:50]}...")
        except Exception as e:
            logger.error(f"Failed to store semantic memory: {e}")

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Search for semantically similar memories.

        Returns list of dicts with 'text', 'metadata', and 'distance'.
        """
        if not self._available:
            return []

        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(top_k, self._collection.count() or 1),
            )

            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    memories.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0,
                    })

            return memories
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

    @property
    def count(self) -> int:
        if not self._available:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0
