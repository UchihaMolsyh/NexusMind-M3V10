"""
Memory System — short-term conversation buffer + long-term SQLite storage.
"""
import json
import time
import sqlite3
import hashlib
import logging
import threading
from contextlib import contextmanager
from core.vector_memory import vector_memory
from typing import List, Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger("nexusmind.memory")


class MemorySystem:
    """Manages short-term and long-term memory for NexusMind."""

    def __init__(self, db_path: Optional[Path] = None, short_term_limit: int = 50):
        from config import MEMORY_DB, SHORT_TERM_LIMIT
        self.db_path = db_path or MEMORY_DB
        self.short_term_limit = short_term_limit or SHORT_TERM_LIMIT
        self.short_term: List[Dict[str, str]] = []
        self._local = threading.local()
        self._init_db()

    @contextmanager
    def _conn(self):
        """Thread-safe reusable connection via thread-local storage."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path))
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield self._local.conn
        except Exception:
            self._local.conn.rollback()
            raise

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    role TEXT,
                    content TEXT,
                    content_hash TEXT UNIQUE,
                    tags TEXT DEFAULT '',
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed REAL,
                    category TEXT DEFAULT 'general' -- 'goal', 'preference', 'project'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    timestamp REAL,
                    messages TEXT,
                    title TEXT DEFAULT 'New Chat'
                )
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_sid ON conversations(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_hash ON long_term_memory(content_hash)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_tags ON long_term_memory(tags)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_importance ON long_term_memory(importance DESC, timestamp DESC)
            """)
            
            # Migration: Add 'title' column if it doesn't exist
            cursor = conn.execute("PRAGMA table_info(conversations)")
            columns = [row[1] for row in cursor.fetchall()]
            if 'title' not in columns:
                conn.execute("ALTER TABLE conversations ADD COLUMN title TEXT DEFAULT 'New Chat'")
                logger.info("Migrated database: added 'title' column to conversations")

            # Migration: Ensure idx_conversations_sid is UNIQUE
            cursor = conn.execute("PRAGMA index_list(conversations)")
            indexes = cursor.fetchall()
            for idx in indexes:
                if idx[1] == 'idx_conversations_sid' and not idx[2]: # Name matches and unique=0
                    logger.info("Migrated database: converting idx_conversations_sid to UNIQUE")
                    conn.execute("DROP INDEX idx_conversations_sid")
                    conn.execute("CREATE UNIQUE INDEX idx_conversations_sid ON conversations(session_id)")
                
            conn.commit()

    # ─── Short-Term Memory ────────────────────────────────────

    def add_message(self, role: str, content: str):
        """Add a message to short-term memory."""
        self.short_term.append({"role": role, "content": content})
        if len(self.short_term) > self.short_term_limit:
            # Move oldest messages to long-term before trimming
            overflow = self.short_term[:len(self.short_term) - self.short_term_limit]
            for msg in overflow:
                self.store_long_term(msg["role"], msg["content"])
            self.short_term = self.short_term[-self.short_term_limit:]

    def get_history(self, n: Optional[int] = None) -> List[Dict[str, str]]:
        """Get recent conversation history."""
        if n is None:
            return list(self.short_term)
        return list(self.short_term[-n:])

    def clear_short_term(self):
        self.short_term.clear()

    # ─── Long-Term Memory ─────────────────────────────────────

    def store_long_term(self, role: str, content: str, tags: str = "", importance: float = 0.5, category: str = "general"):
        """Store a message in long-term memory (SQLite + Chroma)."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        now = time.time()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT OR IGNORE INTO long_term_memory
                       (timestamp, role, content, content_hash, tags, importance, last_accessed, category)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (now, role, content, content_hash, tags, importance, now, category),
                )
                conn.commit()
            
            # Also store in vector database for semantic search
            vector_memory.add_memory(
                content=content,
                metadata={"role": role, "tags": tags, "importance": importance, "timestamp": now},
                memory_id=content_hash
            )
        except Exception as e:
            logger.error(f"Failed to store long-term memory: {e}")

    def search_long_term(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search long-term memory using hybrid search (Keyword + Vector)."""
        # 1. Vector Search (Semantic)
        v_results = vector_memory.search(query, n_results=k)
        
        # 2. Keyword Search (SQLite) - existing logic
        words = query.lower().split()
        if not words:
            return v_results
        
        # ... (rest of search_long_term logic)

        # Filter to meaningful words (skip very short ones)
        words = [w for w in words if len(w) > 2]
        if not words:
            words = query.lower().split()  # fallback to all words

        conditions = " OR ".join(["LOWER(content) LIKE ?" for _ in words])
        params = [f"%{w}%" for w in words]

        with self._conn() as conn:
            rows = conn.execute(
                f"""SELECT id, role, content, tags, importance, timestamp
                    FROM long_term_memory
                    WHERE {conditions}
                    ORDER BY importance DESC, timestamp DESC
                    LIMIT ?""",
                params + [k],
            ).fetchall()

            # Batch update access counts
            if rows:
                now = time.time()
                conn.executemany(
                    "UPDATE long_term_memory SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                    [(now, r[0]) for r in rows],
                )
                conn.commit()

        # Convert SQLite rows to dicts
        sqlite_results = [
            {
                "id": r[0], "role": r[1], "content": r[2],
                "tags": r[3], "importance": r[4], "timestamp": r[5],
            }
            for r in rows
        ]

        # Convert vector results to match format
        vector_formatted = []
        for v in v_results:
            meta = v.get("metadata", {})
            vector_formatted.append({
                "id": -1,  # Semantic results don't return SQLite ID directly
                "role": meta.get("role", "user"),
                "content": v["content"],
                "tags": meta.get("tags", ""),
                "importance": meta.get("importance", 0.5),
                "timestamp": meta.get("timestamp", 0.0)
            })

        # Combine and deduplicate based on content
        merged = []
        seen = set()
        
        # Interleave to get top hits from both methods
        for i in range(max(len(sqlite_results), len(vector_formatted))):
            if i < len(vector_formatted):
                v = vector_formatted[i]
                if v["content"] not in seen:
                    seen.add(v["content"])
                    merged.append(v)
            if i < len(sqlite_results):
                r = sqlite_results[i]
                if r["content"] not in seen:
                    seen.add(r["content"])
                    merged.append(r)

        return merged[:k]

    def get_context_string(self, query: str) -> str:
        """Get relevant long-term memories as a context string."""
        memories = self.search_long_term(query)
        if not memories:
            return ""
        parts = []
        for m in memories:
            parts.append(f"[{m['role']}] {m['content'][:500]}")
        return "\n---\n".join(parts)

    # ─── Session Management ───────────────────────────────────

    def save_session(self, session_id: str, title: Optional[str] = None):
        """Save current conversation to a session. Merges if session exists."""
        with self._conn() as conn:
            if title:
                conn.execute(
                    "INSERT INTO conversations (session_id, timestamp, messages, title) VALUES (?, ?, ?, ?) "
                    "ON CONFLICT(session_id) DO UPDATE SET timestamp=excluded.timestamp, messages=excluded.messages, title=excluded.title",
                    (session_id, time.time(), json.dumps(self.short_term), title),
                )
            else:
                conn.execute(
                    "INSERT INTO conversations (session_id, timestamp, messages) VALUES (?, ?, ?) "
                    "ON CONFLICT(session_id) DO UPDATE SET timestamp=excluded.timestamp, messages=excluded.messages",
                    (session_id, time.time(), json.dumps(self.short_term)),
                )
            conn.commit()

    def load_session(self, session_id: str) -> bool:
        """Load a previous session."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT messages FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        if row:
            self.short_term = json.loads(row[0])
            return True
        return False

    def list_sessions(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT session_id, timestamp, title FROM conversations GROUP BY session_id ORDER BY timestamp DESC LIMIT 50"
            ).fetchall()
        return [{"session_id": r[0], "timestamp": r[1], "title": r[2]} for r in rows]

    def get_session_messages(self, session_id: str) -> List[Dict[str, str]]:
        """Retrieve all messages for a specific session."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT messages FROM conversations WHERE session_id = ? ORDER BY timestamp DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        if row:
            return json.loads(row[0])
        return []

    def delete_session(self, session_id: str):
        """Delete a specific session and its history. High speed via index."""
        with self._conn() as conn:
            conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            conn.commit()
            logger.info(f"Deleted session {session_id}")

    def update_session_title(self, session_id: str, title: str):
        """Update just the title for a session."""
        with self._conn() as conn:
            conn.execute(
                "UPDATE conversations SET title = ? WHERE session_id = ?",
                (title, session_id)
            )
            conn.commit()

    def get_stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            lt_count = conn.execute("SELECT COUNT(*) FROM long_term_memory").fetchone()[0]
            sess_count = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
        return {
            "short_term_messages": len(self.short_term),
            "long_term_entries": lt_count,
            "sessions": sess_count,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
        }

    def prune(self, max_entries: int = 10000, min_importance: float = 0.3):
        """Prune old, low-importance memories to keep the database lean."""
        with self._conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM long_term_memory").fetchone()[0]
            if count > max_entries:
                conn.execute(
                    """DELETE FROM long_term_memory WHERE id IN (
                        SELECT id FROM long_term_memory
                        WHERE importance < ? AND access_count < 3
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )""",
                    (min_importance, count - max_entries),
                )
                conn.commit()
                logger.info(f"Pruned long-term memory from {count} to ~{max_entries} entries")
