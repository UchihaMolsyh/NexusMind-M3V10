"""
RAG Tools — Retrieval-Augmented Generation, Knowledge Graphs, Document Ingestion.
"""
import json
import hashlib
import logging
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.rag")

# ─── In-Memory Knowledge Graph ──────────────────────────
_knowledge_graph = {"entities": {}, "relations": []}
_bookmarks = {}


@registry.tool(
    name="rag_search",
    description="Perform Retrieval-Augmented Generation search against the vector memory store. Returns semantically similar stored knowledge.",
    category="RAG & Knowledge",
    parameters=[
        ToolParam("query", "string", "The search query to find relevant knowledge"),
        ToolParam("top_k", "integer", "Number of results to return", required=False, default=5),
    ]
)
def rag_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    from core.vector_memory import vector_memory
    results = vector_memory.search(query, n_results=top_k)
    return {
        "query": query,
        "results": results,
        "count": len(results),
    }


@registry.tool(
    name="knowledge_graph_add",
    description="Add an entity or relation to the in-memory knowledge graph.",
    category="RAG & Knowledge",
    parameters=[
        ToolParam("entity", "string", "Entity name to add"),
        ToolParam("entity_type", "string", "Type of entity (person, concept, tool, etc.)", required=False, default="concept"),
        ToolParam("relation", "string", "Relation type (e.g., 'is_a', 'has', 'uses')", required=False),
        ToolParam("target", "string", "Target entity for the relation", required=False),
    ]
)
def knowledge_graph_add(entity: str, entity_type: str = "concept",
                        relation: str = None, target: str = None) -> Dict[str, Any]:
    _knowledge_graph["entities"][entity] = {"type": entity_type}
    if relation and target:
        _knowledge_graph["entities"].setdefault(target, {"type": "concept"})
        _knowledge_graph["relations"].append({
            "source": entity, "relation": relation, "target": target
        })
    return {
        "status": "added",
        "total_entities": len(_knowledge_graph["entities"]),
        "total_relations": len(_knowledge_graph["relations"]),
    }


@registry.tool(
    name="knowledge_graph_query",
    description="Query the knowledge graph for entities and their relations.",
    category="RAG & Knowledge",
    parameters=[
        ToolParam("entity", "string", "Entity to query"),
    ]
)
def knowledge_graph_query(entity: str) -> Dict[str, Any]:
    info = _knowledge_graph["entities"].get(entity)
    if not info:
        return {"found": False, "entity": entity}

    relations = [r for r in _knowledge_graph["relations"]
                 if r["source"] == entity or r["target"] == entity]
    return {
        "found": True,
        "entity": entity,
        "type": info["type"],
        "relations": relations,
    }


@registry.tool(
    name="document_ingest",
    description="Parse and ingest a text document into the vector memory store for RAG retrieval.",
    category="RAG & Knowledge",
    parameters=[
        ToolParam("text", "string", "The document text to ingest"),
        ToolParam("source", "string", "Source identifier for the document", required=False, default="manual"),
        ToolParam("chunk_size", "integer", "Characters per chunk", required=False, default=500),
    ]
)
def document_ingest(text: str, source: str = "manual", chunk_size: int = 500) -> Dict[str, Any]:
    from core.vector_memory import vector_memory

    # Chunk the text
    chunks = []
    words = text.split()
    current_chunk = []
    current_len = 0
    for word in words:
        current_chunk.append(word)
        current_len += len(word) + 1
        if current_len >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_len = 0
    if current_chunk:
        chunks.append(" ".join(current_chunk))

    # Store chunks in vector memory
    for i, chunk in enumerate(chunks):
        chunk_id = hashlib.md5(f"{source}_{i}_{chunk[:50]}".encode()).hexdigest()
        vector_memory.add_memory(
            content=chunk,
            metadata={"source": source, "chunk_index": i, "type": "document"},
            memory_id=f"doc_{chunk_id}"
        )

    return {
        "status": "ingested",
        "chunks": len(chunks),
        "source": source,
        "total_chars": len(text),
    }


@registry.tool(
    name="bookmark_memory",
    description="Bookmark/store a knowledge chunk with tags for later retrieval.",
    category="RAG & Knowledge",
    parameters=[
        ToolParam("content", "string", "The knowledge content to bookmark"),
        ToolParam("tags", "string", "Comma-separated tags for categorization"),
        ToolParam("title", "string", "Short title for the bookmark", required=False, default=""),
    ]
)
def bookmark_memory(content: str, tags: str, title: str = "") -> Dict[str, Any]:
    from core.vector_memory import vector_memory

    bookmark_id = hashlib.md5(content[:100].encode()).hexdigest()
    tag_list = [t.strip() for t in tags.split(",")]

    _bookmarks[bookmark_id] = {
        "title": title,
        "content": content,
        "tags": tag_list,
    }

    vector_memory.add_memory(
        content=content,
        metadata={"type": "bookmark", "tags": tags, "title": title},
        memory_id=f"bm_{bookmark_id}"
    )

    return {
        "status": "bookmarked",
        "id": bookmark_id,
        "tags": tag_list,
        "total_bookmarks": len(_bookmarks),
    }
