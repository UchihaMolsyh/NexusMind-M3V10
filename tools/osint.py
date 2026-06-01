"""
OSINT — Wikipedia, YouTube, GitHub, Shodan, theHarvester, recon-ng, Metasploit integration.
"""
import json
import subprocess
import requests
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


WIKI_API = "https://en.wikipedia.org/api/rest_v1"


@registry.tool(
    name="osint_lookup",
    description="OSINT research: Wikipedia, YouTube search, GitHub, Shodan lookup, theHarvester, recon-ng, Metasploit (educational). All lookups are informational.",
    category="OSINT & Research",
    parameters=[
        ToolParam("source", "string", "Source: wikipedia, youtube, github, shodan, theharvester, recon_ng, metasploit, web_search"),
        ToolParam("query", "string", "Search query or target"),
        ToolParam("params", "string", "Additional JSON parameters", required=False, default="{}"),
    ],
)
def osint_lookup(source: str, query: str, params: str = "{}"):
    p = json.loads(params) if isinstance(params, str) else params

    if source == "wikipedia":
        return _wikipedia_search(query, p)
    elif source == "youtube":
        return _youtube_search(query, p)
    elif source == "github":
        return _github_osint(query, p)
    elif source == "shodan":
        return _shodan_lookup(query, p)
    elif source == "theharvester":
        return _theharvester(query, p)
    elif source == "recon_ng":
        return _recon_ng(query, p)
    elif source == "metasploit":
        return _metasploit(query, p)
    elif source == "web_search":
        return _web_search(query, p)
    else:
        return {"error": f"Unknown source: {source}",
                "available": ["wikipedia", "youtube", "github", "shodan", "theharvester", "recon_ng", "metasploit", "web_search"]}


def _wikipedia_search(query: str, params: dict) -> Dict:
    try:
        # Search
        resp = requests.get(f"https://en.wikipedia.org/w/api.php", params={
            "action": "query", "list": "search", "srsearch": query,
            "format": "json", "srlimit": params.get("limit", 5),
        }, timeout=10)
        data = resp.json()
        results = []
        for r in data.get("query", {}).get("search", []):
            # Get summary for top result
            title = r["title"]
            summary_resp = requests.get(f"{WIKI_API}/page/summary/{title.replace(' ', '_')}", timeout=10)
            summary = summary_resp.json() if summary_resp.status_code == 200 else {}
            results.append({
                "title": title,
                "snippet": r.get("snippet", "")[:300],
                "summary": summary.get("extract", "")[:1000],
                "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
            })
        return {"source": "wikipedia", "results": results}
    except Exception as e:
        return {"error": str(e)}


def _youtube_search(query: str, params: dict) -> Dict:
    """Search YouTube via scraping (no API key needed)."""
    try:
        resp = requests.get(
            "https://www.youtube.com/results",
            params={"search_query": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        # Basic extraction from HTML
        import re
        video_ids = re.findall(r'"videoId":"([^"]+)"', resp.text)
        unique_ids = list(dict.fromkeys(video_ids))[:params.get("limit", 5)]
        results = []
        for vid in unique_ids:
            results.append({
                "video_id": vid,
                "url": f"https://www.youtube.com/watch?v={vid}",
            })
        return {"source": "youtube", "query": query, "results": results}
    except Exception as e:
        return {"error": str(e)}


def _github_osint(query: str, params: dict) -> Dict:
    """GitHub OSINT — user info and repo analysis."""
    try:
        resp = requests.get(f"https://api.github.com/users/{query}", timeout=10)
        if resp.status_code != 200:
            return {"error": f"User not found: {query}"}
        user = resp.json()
        repos_resp = requests.get(user["repos_url"], params={"per_page": 10, "sort": "updated"}, timeout=10)
        repos = repos_resp.json() if repos_resp.status_code == 200 else []
        return {
            "source": "github_osint",
            "user": {
                "login": user["login"], "name": user.get("name"),
                "bio": user.get("bio"), "location": user.get("location"),
                "public_repos": user["public_repos"], "followers": user["followers"],
                "created": user["created_at"][:10],
            },
            "recent_repos": [{"name": r["name"], "language": r.get("language"), "stars": r.get("stargazers_count")} for r in repos[:10]],
        }
    except Exception as e:
        return {"error": str(e)}


def _shodan_lookup(query: str, params: dict) -> Dict:
    """Shodan lookup (requires CLI tool installed)."""
    try:
        result = subprocess.run(["shodan", "search", query], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return {"source": "shodan", "output": result.stdout[:5000]}
        return {"error": result.stderr[:1000], "note": "Ensure Shodan CLI is installed: pip install shodan"}
    except FileNotFoundError:
        return {"error": "Shodan CLI not installed. Install with: pip install shodan && shodan init YOUR_API_KEY"}
    except Exception as e:
        return {"error": str(e)}


def _theharvester(query: str, params: dict) -> Dict:
    """theHarvester integration (requires tool installed)."""
    source = params.get("source", "google")
    try:
        result = subprocess.run(
            ["theHarvester", "-d", query, "-b", source, "-l", str(params.get("limit", 100))],
            capture_output=True, text=True, timeout=60,
        )
        return {"source": "theharvester", "target": query, "output": result.stdout[:5000]}
    except FileNotFoundError:
        return {"error": "theHarvester not installed. Clone from: https://github.com/laramies/theHarvester"}
    except Exception as e:
        return {"error": str(e)}


def _recon_ng(query: str, params: dict) -> Dict:
    """recon-ng integration."""
    try:
        commands = params.get("commands", [f"modules search {query}"])
        cmd_str = "\n".join(commands)
        result = subprocess.run(
            ["recon-ng", "-x", cmd_str], capture_output=True, text=True, timeout=60,
        )
        return {"source": "recon_ng", "output": result.stdout[:5000]}
    except FileNotFoundError:
        return {"error": "recon-ng not installed. Install from: https://github.com/lanmaster53/recon-ng"}
    except Exception as e:
        return {"error": str(e)}


def _metasploit(query: str, params: dict) -> Dict:
    """Metasploit integration (EDUCATIONAL PURPOSES ONLY)."""
    disclaimer = "⚠️ EDUCATIONAL PURPOSES ONLY. Only use on systems you own or have explicit permission to test."
    try:
        action = params.get("action", "search")
        if action == "search":
            result = subprocess.run(
                ["msfconsole", "-q", "-x", f"search {query}; exit"],
                capture_output=True, text=True, timeout=60,
            )
            return {"source": "metasploit", "disclaimer": disclaimer, "output": result.stdout[:5000]}
        elif action == "info":
            result = subprocess.run(
                ["msfconsole", "-q", "-x", f"info {query}; exit"],
                capture_output=True, text=True, timeout=60,
            )
            return {"source": "metasploit", "disclaimer": disclaimer, "output": result.stdout[:5000]}
        return {"error": f"Unknown metasploit action: {action}", "disclaimer": disclaimer}
    except FileNotFoundError:
        return {"error": "Metasploit not installed.", "disclaimer": disclaimer}
    except Exception as e:
        return {"error": str(e), "disclaimer": disclaimer}


def _web_search(query: str, params: dict) -> Dict:
    """Basic web search via DuckDuckGo Lite (no API key)."""
    try:
        resp = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a in soup.find_all("a", class_="result-link")[:5]:
            results.append({"title": a.get_text(strip=True), "url": a.get("href", "")})
        if not results:
            links = soup.find_all("a", href=True)
            for a in links:
                href = a.get("href", "")
                if href.startswith("http") and "duckduckgo" not in href:
                    results.append({"title": a.get_text(strip=True)[:100], "url": href})
                if len(results) >= 5:
                    break
        return {"source": "web_search", "query": query, "results": results}
    except Exception as e:
        return {"error": str(e)}
