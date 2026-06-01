"""
Browser Tools — Web scraping, link extraction, page capture.
"""
import logging
from typing import Dict, Any
from core.tool_registry import registry, ToolParam

logger = logging.getLogger("nexusmind.tools.browser")


@registry.tool(
    name="web_scrape",
    description="Fetch and parse a webpage's text content. Extracts main text, title, and meta description.",
    category="Browser & Web",
    parameters=[
        ToolParam("url", "string", "The URL to scrape"),
        ToolParam("max_length", "integer", "Maximum characters to return", required=False, default=5000),
    ]
)
def web_scrape(url: str, max_length: int = 5000) -> Dict[str, Any]:
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return {"error": "Missing dependencies: pip install requests beautifulsoup4"}

    try:
        headers = {"User-Agent": "NexusMind/1.0 (Research Bot)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()

        title = soup.title.string if soup.title else "No title"
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        text = soup.get_text(separator="\n", strip=True)
        text = "\n".join(line for line in text.split("\n") if line.strip())

        return {
            "url": url,
            "title": title,
            "meta_description": meta_desc,
            "content": text[:max_length],
            "content_length": len(text),
            "truncated": len(text) > max_length,
        }
    except Exception as e:
        return {"error": str(e), "url": url}


@registry.tool(
    name="extract_links",
    description="Extract all hyperlinks from a webpage.",
    category="Browser & Web",
    parameters=[
        ToolParam("url", "string", "The URL to extract links from"),
        ToolParam("max_links", "integer", "Maximum number of links to return", required=False, default=50),
    ]
)
def extract_links(url: str, max_links: int = 50) -> Dict[str, Any]:
    try:
        import requests
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
    except ImportError:
        return {"error": "Missing dependencies: pip install requests beautifulsoup4"}

    try:
        headers = {"User-Agent": "NexusMind/1.0 (Research Bot)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        links = []

        for a in soup.find_all("a", href=True):
            href = urljoin(url, a["href"])
            text = a.get_text(strip=True)[:100]
            links.append({"url": href, "text": text})

            if len(links) >= max_links:
                break

        return {
            "source_url": url,
            "links": links,
            "count": len(links),
        }
    except Exception as e:
        return {"error": str(e), "url": url}


@registry.tool(
    name="web_search_enhanced",
    description="Enhanced web search with result parsing and content extraction.",
    category="Browser & Web",
    parameters=[
        ToolParam("query", "string", "Search query"),
        ToolParam("num_results", "integer", "Number of results", required=False, default=5),
    ]
)
def web_search_enhanced(query: str, num_results: int = 5) -> Dict[str, Any]:
    try:
        import requests
    except ImportError:
        return {"error": "Missing requests library"}

    # Use DuckDuckGo HTML for basic search
    try:
        headers = {"User-Agent": "NexusMind/1.0"}
        params = {"q": query, "format": "json"}
        resp = requests.get("https://api.duckduckgo.com/", params=params, headers=headers, timeout=10)
        data = resp.json()

        results = []
        for topic in data.get("RelatedTopics", [])[:num_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "text": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                })

        return {
            "query": query,
            "abstract": data.get("AbstractText", ""),
            "source": data.get("AbstractSource", ""),
            "results": results,
            "count": len(results),
        }
    except Exception as e:
        return {"error": str(e), "query": query}
