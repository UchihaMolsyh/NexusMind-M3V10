"""
Reasoning Cache — cache reasoning chains to avoid redundant computation.
"""
import json
import time
import sqlite3
import hashlib
import logging
import threading
from contextlib import contextmanager
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger("nexusmind.cache")


class ReasoningCache:
    """Cache question → reasoning → answer chains in SQLite."""

    def __init__(self, db_path: Optional[Path] = None, ttl_hours: int = 168):
        from config import CACHE_DB
        self.db_path = db_path or CACHE_DB
        self.ttl_seconds = ttl_hours * 3600
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
                CREATE TABLE IF NOT EXISTS reasoning_cache (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query_hash TEXT UNIQUE,
                    query TEXT,
                    reasoning TEXT,
                    answer TEXT,
                    confidence REAL,
                    tools_used TEXT,
                    timestamp REAL,
                    hit_count INTEGER DEFAULT 0,
                    last_hit REAL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_cache_hash ON reasoning_cache(query_hash)
            """)
            conn.commit()

    def _hash(self, query: str) -> str:
        normalized = " ".join(query.lower().strip().split())
        return hashlib.sha256(normalized.encode()).hexdigest()[:32]

    def lookup(self, query: str) -> Optional[Dict[str, Any]]:
        """Look up a cached reasoning chain. Returns None if not found or expired."""
        qhash = self._hash(query)
        with self._conn() as conn:
            row = conn.execute(
                """SELECT query, reasoning, answer, confidence, tools_used, timestamp
                   FROM reasoning_cache WHERE query_hash = ?""",
                (qhash,),
            ).fetchone()

            if row:
                # Check TTL
                if time.time() - row[5] > self.ttl_seconds:
                    conn.execute("DELETE FROM reasoning_cache WHERE query_hash = ?", (qhash,))
                    conn.commit()
                    return None

                conn.execute(
                    "UPDATE reasoning_cache SET hit_count = hit_count + 1, last_hit = ? WHERE query_hash = ?",
                    (time.time(), qhash),
                )
                conn.commit()
                return {
                    "query": row[0],
                    "reasoning": row[1],
                    "answer": row[2],
                    "confidence": row[3],
                    "tools_used": json.loads(row[4]) if row[4] else [],
                    "timestamp": row[5],
                    "cached": True,
                }

        return None

    def store(
        self,
        query: str,
        reasoning: str,
        answer: str,
        confidence: float = 5.0,
        tools_used: Optional[List[str]] = None,
    ):
        """Store a reasoning chain in the cache."""
        qhash = self._hash(query)
        now = time.time()
        try:
            with self._conn() as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO reasoning_cache
                       (query_hash, query, reasoning, answer, confidence, tools_used, timestamp, last_hit)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (qhash, query, reasoning, answer, confidence,
                     json.dumps(tools_used or []), now, now),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to cache reasoning: {e}")

    def invalidate(self, query: str):
        """Remove a cached entry."""
        qhash = self._hash(query)
        with self._conn() as conn:
            conn.execute("DELETE FROM reasoning_cache WHERE query_hash = ?", (qhash,))
            conn.commit()

    def clear(self):
        """Clear the entire cache."""
        with self._conn() as conn:
            conn.execute("DELETE FROM reasoning_cache")
            conn.commit()

    def evict_stale(self):
        """Remove entries older than TTL."""
        cutoff = time.time() - self.ttl_seconds
        with self._conn() as conn:
            deleted = conn.execute(
                "DELETE FROM reasoning_cache WHERE timestamp < ?", (cutoff,)
            ).rowcount
            conn.commit()
            if deleted:
                logger.info(f"Evicted {deleted} stale cache entries")

    def stats(self) -> Dict[str, Any]:
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM reasoning_cache").fetchone()[0]
            total_hits = conn.execute("SELECT SUM(hit_count) FROM reasoning_cache").fetchone()[0] or 0
        db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
        return {
            "cached_entries": total,
            "total_hits": total_hits,
            "db_size_mb": round(db_size / (1024 * 1024), 2),
        }
