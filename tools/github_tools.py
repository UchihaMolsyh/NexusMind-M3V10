"""
GitHub & Stack Overflow — search public repos, read code, search SO questions.
"""
import json
import requests
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


GH_API = "https://api.github.com"
SO_API = "https://api.stackexchange.com/2.3"


@registry.tool(
    name="github_search",
    description="Search GitHub public repositories, code, issues, and users.",
    category="Git & Code",
    parameters=[
        ToolParam("query", "string", "Search query"),
        ToolParam("search_type", "string", "Type: repos, code, issues, users", required=False, default="repos"),
        ToolParam("language", "string", "Filter by programming language", required=False, default=""),
        ToolParam("max_results", "string", "Max results (default: 10)", required=False, default="10"),
    ],
)
def github_search(query: str, search_type: str = "repos", language: str = "", max_results: str = "10"):
    n = min(int(max_results), 30)
    headers = {"Accept": "application/vnd.github.v3+json"}

    try:
        q = query
        if language:
            q += f" language:{language}"

        if search_type == "repos":
            resp = requests.get(f"{GH_API}/search/repositories", params={"q": q, "per_page": n}, headers=headers, timeout=15)
            data = resp.json()
            items = []
            for r in data.get("items", [])[:n]:
                items.append({
                    "name": r["full_name"],
                    "description": (r.get("description") or "")[:200],
                    "stars": r["stargazers_count"],
                    "language": r.get("language"),
                    "url": r["html_url"],
                    "updated": r.get("updated_at", "")[:10],
                })
            return {"results": items, "total": data.get("total_count", 0)}

        elif search_type == "code":
            resp = requests.get(f"{GH_API}/search/code", params={"q": q, "per_page": n}, headers=headers, timeout=15)
            data = resp.json()
            items = []
            for r in data.get("items", [])[:n]:
                items.append({
                    "file": r["name"],
                    "path": r["path"],
                    "repo": r["repository"]["full_name"],
                    "url": r["html_url"],
                })
            return {"results": items, "total": data.get("total_count", 0)}

        elif search_type == "issues":
            resp = requests.get(f"{GH_API}/search/issues", params={"q": q, "per_page": n}, headers=headers, timeout=15)
            data = resp.json()
            items = []
            for r in data.get("items", [])[:n]:
                items.append({
                    "title": r["title"][:200],
                    "state": r["state"],
                    "repo": r["repository_url"].split("/")[-2] + "/" + r["repository_url"].split("/")[-1],
                    "url": r["html_url"],
                    "comments": r.get("comments", 0),
                })
            return {"results": items, "total": data.get("total_count", 0)}

        elif search_type == "users":
            resp = requests.get(f"{GH_API}/search/users", params={"q": q, "per_page": n}, headers=headers, timeout=15)
            data = resp.json()
            items = [{"login": u["login"], "url": u["html_url"], "type": u["type"]} for u in data.get("items", [])[:n]]
            return {"results": items, "total": data.get("total_count", 0)}

        return {"error": f"Unknown search type: {search_type}"}

    except requests.exceptions.Timeout:
        return {"error": "GitHub API timeout"}
    except Exception as e:
        return {"error": str(e)}


@registry.tool(
    name="github_read_file",
    description="Read a file from a public GitHub repository.",
    category="Git & Code",
    parameters=[
        ToolParam("repo", "string", "Repository (e.g., 'owner/repo')"),
        ToolParam("path", "string", "File path in the repo"),
        ToolParam("branch", "string", "Branch name (default: main)", required=False, default="main"),
    ],
)
def github_read_file(repo: str, path: str, branch: str = "main"):
    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        resp = requests.get(f"{GH_API}/repos/{repo}/contents/{path}", params={"ref": branch}, headers=headers, timeout=15)
        if resp.status_code == 404:
            return {"error": f"File not found: {repo}/{path}"}
        data = resp.json()
        import base64
        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        else:
            content = data.get("content", "")
        return {
            "repo": repo,
            "path": path,
            "size": data.get("size"),
            "content": content[:50000],
        }
    except Exception as e:
        return {"error": str(e)}


@registry.tool(
    name="stackoverflow_search",
    description="Search Stack Overflow questions and answers.",
    category="Git & Code",
    parameters=[
        ToolParam("query", "string", "Search query"),
        ToolParam("tags", "string", "Comma-separated tags (e.g., 'python,numpy')", required=False, default=""),
        ToolParam("max_results", "string", "Max results (default: 5)", required=False, default="5"),
    ],
)
def stackoverflow_search(query: str, tags: str = "", max_results: str = "5"):
    n = min(int(max_results), 20)
    params = {
        "order": "desc",
        "sort": "relevance",
        "intitle": query,
        "site": "stackoverflow",
        "pagesize": n,
        "filter": "withbody",
    }
    if tags:
        params["tagged"] = tags.replace(" ", "")

    try:
        resp = requests.get(f"{SO_API}/search/advanced", params=params, timeout=15)
        data = resp.json()
        items = []
        for q in data.get("items", [])[:n]:
            items.append({
                "title": q["title"],
                "score": q["score"],
                "answers": q["answer_count"],
                "accepted": q.get("accepted_answer_id") is not None,
                "url": q["link"],
                "tags": q.get("tags", []),
                "body_preview": q.get("body", "")[:500],
            })
        return {"results": items, "total": data.get("total", 0)}
    except Exception as e:
        return {"error": str(e)}
