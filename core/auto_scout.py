"""
Auto-Scout — Background GitHub optimization finder.
Periodically searches GitHub for repos/techniques that can make NexusMind
more lightweight, powerful, or efficient, then notifies connected clients.
"""
import json
import time
import asyncio
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Set

logger = logging.getLogger("nexusmind.scout")

GH_API = "https://api.github.com"


class AutoScout:
    """Background service that searches GitHub for optimization opportunities."""

    def __init__(self):
        from config import SCOUT_HISTORY_FILE, SCOUT_MIN_STARS, SCOUT_QUERIES, SCOUT_INTERVAL_MINUTES
        self.history_file = SCOUT_HISTORY_FILE
        self.min_stars = SCOUT_MIN_STARS
        self.queries = SCOUT_QUERIES
        self.interval = SCOUT_INTERVAL_MINUTES * 60  # Convert to seconds
        self.seen_repos: Set[str] = set()
        self.findings: List[Dict[str, Any]] = []
        self.dismissed: Set[str] = set()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._connected_websockets: List = []
        self._load_history()

    def _load_history(self):
        """Load previously seen repos from disk."""
        try:
            if self.history_file.exists():
                data = json.loads(self.history_file.read_text(encoding="utf-8"))
                self.seen_repos = set(data.get("seen", []))
                self.dismissed = set(data.get("dismissed", []))
                self.findings = data.get("findings", [])
                logger.info(f"Scout loaded {len(self.seen_repos)} previously seen repos")
        except Exception as e:
            logger.warning(f"Scout history load failed: {e}")

    def _save_history(self):
        """Persist seen repos and findings to disk."""
        try:
            data = {
                "seen": list(self.seen_repos),
                "dismissed": list(self.dismissed),
                "findings": self.findings[-50:],  # Keep last 50 findings
                "last_scan": datetime.now().isoformat(),
            }
            self.history_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Scout history save failed: {e}")

    def register_websocket(self, ws):
        """Register a WebSocket client for scout notifications."""
        if ws not in self._connected_websockets:
            self._connected_websockets.append(ws)

    def unregister_websocket(self, ws):
        """Remove a WebSocket client."""
        if ws in self._connected_websockets:
            self._connected_websockets.remove(ws)

    def start(self):
        """Start the background scanning loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._scan_loop())
        logger.info("🔭 Auto-Scout started — will scan GitHub for optimizations")

    def stop(self):
        """Stop the background scanning loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        logger.info("Auto-Scout stopped")

    async def _scan_loop(self):
        """Main background loop — runs initial scan after 30s, then every interval."""
        # Short initial delay so the server can fully start
        await asyncio.sleep(30)

        while self._running:
            try:
                new_findings = await asyncio.to_thread(self._run_scan)
                if new_findings:
                    logger.info(f"🔭 Scout found {len(new_findings)} new optimization repos!")
                    await self._broadcast(new_findings)
                    self._save_history()
                else:
                    logger.info("🔭 Scout scan complete — no new findings")
            except Exception as e:
                logger.error(f"Scout scan error: {e}")

            # Wait for next scan
            await asyncio.sleep(self.interval)

    def _run_scan(self) -> List[Dict[str, Any]]:
        """Execute all search queries against GitHub API. Runs in a thread."""
        new_findings = []
        headers = {"Accept": "application/vnd.github.v3+json"}

        # Calculate date cutoff (repos updated in last 90 days)
        cutoff = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        for query in self.queries:
            try:
                # Search for repos with minimum stars, recently updated
                q = f"{query} pushed:>{cutoff} stars:>={self.min_stars}"
                resp = requests.get(
                    f"{GH_API}/search/repositories",
                    params={"q": q, "sort": "stars", "order": "desc", "per_page": 5},
                    headers=headers,
                    timeout=15,
                )

                if resp.status_code == 403:
                    logger.warning("Scout: GitHub API rate limit hit, pausing")
                    time.sleep(60)
                    continue

                if resp.status_code != 200:
                    continue

                data = resp.json()
                for repo in data.get("items", []):
                    repo_id = repo["full_name"]

                    # Skip if already seen or dismissed
                    if repo_id in self.seen_repos or repo_id in self.dismissed:
                        continue

                    finding = {
                        "id": repo_id,
                        "name": repo["full_name"],
                        "description": (repo.get("description") or "No description")[:200],
                        "stars": repo["stargazers_count"],
                        "language": repo.get("language", "Unknown"),
                        "url": repo["html_url"],
                        "updated": repo.get("updated_at", "")[:10],
                        "query": query,
                        "found_at": datetime.now().isoformat(),
                        "category": self._categorize(query),
                    }

                    new_findings.append(finding)
                    self.seen_repos.add(repo_id)
                    self.findings.append(finding)

                # Rate limit: small delay between queries
                time.sleep(2)

            except requests.exceptions.Timeout:
                logger.warning(f"Scout: Timeout for query '{query}'")
            except Exception as e:
                logger.warning(f"Scout: Error for query '{query}': {e}")

        return new_findings

    def _categorize(self, query: str) -> str:
        """Assign a category based on the search query."""
        q = query.lower()
        if "quantiz" in q or "compress" in q or "gguf" in q:
            return "⚡ Quantization"
        elif "speculative" in q:
            return "🚀 Speculative Decoding"
        elif "llama" in q or "inference" in q:
            return "🏎️ Inference Speed"
        elif "qwen" in q:
            return "🧠 Qwen Ecosystem"
        elif "small" in q or "efficien" in q or "lightweight" in q:
            return "🪶 Lightweight Models"
        return "🔧 Optimization"

    async def _broadcast(self, new_findings: List[Dict[str, Any]]):
        """Send scout findings to all connected WebSocket clients."""
        if not self._connected_websockets:
            return

        message = {
            "type": "scout_alert",
            "findings": new_findings,
            "total_pending": len([f for f in self.findings if f["id"] not in self.dismissed]),
        }

        disconnected = []
        for ws in self._connected_websockets:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(ws)

        # Clean up disconnected sockets
        for ws in disconnected:
            self._connected_websockets.remove(ws)

    def get_findings(self, include_dismissed: bool = False) -> List[Dict[str, Any]]:
        """Get all findings, optionally filtering out dismissed ones."""
        if include_dismissed:
            return self.findings[-50:]
        return [f for f in self.findings if f["id"] not in self.dismissed][-50:]

    def dismiss(self, repo_id: str):
        """Dismiss a finding so it won't show again."""
        self.dismissed.add(repo_id)
        self._save_history()

    def dismiss_all(self):
        """Dismiss all current findings."""
        for f in self.findings:
            self.dismissed.add(f["id"])
        self._save_history()

    async def implement(self, repo_url: str) -> dict:
        """Propose integration — NEVER auto-execute. Saves for human review."""
        import uuid

        # Notify user something was found
        if self._connected_websockets:
            for ws in self._connected_websockets:
                try:
                    await ws.send_json({
                        "type": "notification",
                        "content": f"Scout found: {repo_url} — saved for your review"
                    })
                except Exception:
                    pass

        proposal = {
            "id": str(uuid.uuid4())[:8],
            "repo_url": repo_url,
            "timestamp": datetime.now().isoformat(),
            "status": "pending_review",
        }

        proposals_file = Path("data/scout_proposals.json")
        proposals = []
        if proposals_file.exists():
            try:
                proposals = json.loads(proposals_file.read_text())
            except Exception:
                proposals = []
        proposals.append(proposal)
        proposals_file.write_text(json.dumps(proposals, indent=2))

        logger.info(f"Scout proposal saved for review: {repo_url}")
        return proposal

    async def force_scan(self) -> List[Dict[str, Any]]:
        """Manually trigger a scan (for API endpoint)."""
        new_findings = await asyncio.to_thread(self._run_scan)
        if new_findings:
            await self._broadcast(new_findings)
            self._save_history()
        return new_findings

    

# Singleton instance
scout = AutoScout()
