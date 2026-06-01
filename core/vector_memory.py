"""
Vector Memory — ChromaDB integration for semantic search and long-term memory.
Uses local/cached embedding model — NO network requests on startup.
"""
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("nexusmind.vector_memory")


class VectorMemory:
    def __init__(self):
        from config import CHROMA_DB_DIR, EMBEDDING_MODEL
        
        import chromadb
        from chromadb.utils import embedding_functions
        
        self.client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
        
        # Force offline mode — use cached model only, no HuggingFace HTTP requests
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        
        try:
            self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )
            logger.info(f"Loaded embedding model: {EMBEDDING_MODEL} (offline/cached)")
        except Exception as e:
            logger.warning(f"Failed to load embedding model (offline): {e}")
            logger.warning("Falling back to default ChromaDB embeddings.")
            self.emb_fn = None
        finally:
            # Restore env so other code can use HF if needed
            os.environ.pop("HF_HUB_OFFLINE", None)
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
        
        kwargs = {"name": "long_term_memory"}
        if self.emb_fn:
            kwargs["embedding_function"] = self.emb_fn
        
        self.collection = self.client.get_or_create_collection(**kwargs)

    def add_memory(self, content: str, metadata: Dict[str, Any], memory_id: str):
        """Add a memory with metadata and embedding."""
        try:
            # Sanitize metadata — ChromaDB only accepts str, int, float, bool
            clean_meta = {}
            for k, v in metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                else:
                    clean_meta[k] = str(v)
            
            self.collection.upsert(
                documents=[content],
                metadatas=[clean_meta],
                ids=[memory_id]
            )
        except Exception as e:
            logger.error(f"Failed to add vector memory: {e}")

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Semantic search for relevant memories."""
        try:
            # Don't search if collection is empty
            if self.collection.count() == 0:
                return []
            
            results = self.collection.query(
                query_texts=[query],
                n_results=min(n_results, self.collection.count())
            )
            
            memories = []
            if results["documents"]:
                for i in range(len(results["documents"][0])):
                    memories.append({
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None
                    })
            return memories
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def delete_memory(self, memory_id: str):
        """Remove a memory by ID."""
        try:
            self.collection.delete(ids=[memory_id])
        except Exception as e:
            logger.error(f"Failed to delete vector memory: {e}")

vector_memory = VectorMemory()
