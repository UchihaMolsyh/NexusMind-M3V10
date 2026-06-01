"""
Git Integration — local Git operations via GitPython.
"""
import os
import json
from pathlib import Path
from typing import Dict, Any
from core.tool_registry import registry, ToolParam


def _get_repo(path: str):
    try:
        from git import Repo
        return Repo(path)
    except Exception as e:
        return None


@registry.tool(
    name="git_command",
    description="Execute Git operations: status, log, diff, commit, branch, clone, pull, push, stash.",
    category="Git & Code",
    parameters=[
        ToolParam("action", "string", "Git action: status, log, diff, commit, branch, clone, pull, push, stash, init, add"),
        ToolParam("repo_path", "string", "Path to Git repository"),
        ToolParam("params", "string", "JSON parameters for the action", required=False, default="{}"),
    ],
)
def git_command(action: str, repo_path: str, params: str = "{}"):
    p = json.loads(params) if isinstance(params, str) else params

    try:
        from git import Repo, InvalidGitRepositoryError
    except ImportError:
        return {"error": "GitPython not installed. pip install GitPython"}

    try:
        if action == "clone":
            url = p.get("url", "")
            if not url:
                return {"error": "Clone URL required"}
            dest = Path(repo_path).resolve()
            dest.mkdir(parents=True, exist_ok=True)
            repo = Repo.clone_from(url, str(dest))
            return {"cloned": url, "path": str(dest), "branch": str(repo.active_branch)}

        if action == "init":
            dest = Path(repo_path).resolve()
            dest.mkdir(parents=True, exist_ok=True)
            repo = Repo.init(str(dest))
            return {"initialized": str(dest)}

        repo = Repo(repo_path)

        if action == "status":
            return {
                "branch": str(repo.active_branch),
                "is_dirty": repo.is_dirty(),
                "untracked": repo.untracked_files[:50],
                "changed": [d.a_path for d in repo.index.diff(None)][:50],
                "staged": [d.a_path for d in repo.index.diff("HEAD")][:50] if repo.head.is_valid() else [],
            }

        elif action == "log":
            n = p.get("n", 10)
            commits = []
            for c in repo.iter_commits(max_count=n):
                commits.append({
                    "hash": c.hexsha[:8],
                    "message": c.message.strip()[:200],
                    "author": str(c.author),
                    "date": c.committed_datetime.isoformat(),
                })
            return {"branch": str(repo.active_branch), "commits": commits}

        elif action == "diff":
            file_path = p.get("file")
            if file_path:
                diffs = repo.git.diff(file_path)
            else:
                diffs = repo.git.diff()
            return {"diff": diffs[:5000]}

        elif action == "add":
            files = p.get("files", ["."])
            repo.index.add(files)
            return {"added": files}

        elif action == "commit":
            message = p.get("message", "NexusMind commit")
            repo.index.commit(message)
            return {"committed": message, "hash": repo.head.commit.hexsha[:8]}

        elif action == "branch":
            sub = p.get("sub", "list")
            if sub == "list":
                return {"branches": [str(b) for b in repo.branches], "active": str(repo.active_branch)}
            elif sub == "create":
                name = p.get("name", "new-branch")
                repo.create_head(name)
                return {"created": name}
            elif sub == "checkout":
                name = p.get("name")
                repo.git.checkout(name)
                return {"checked_out": name}

        elif action == "pull":
            info = repo.remotes.origin.pull()
            return {"pulled": True, "updates": len(info)}

        elif action == "push":
            info = repo.remotes.origin.push()
            return {"pushed": True}

        elif action == "stash":
            sub = p.get("sub", "save")
            if sub == "save":
                repo.git.stash("save", p.get("message", "NexusMind stash"))
                return {"stashed": True}
            elif sub == "pop":
                repo.git.stash("pop")
                return {"popped": True}
            elif sub == "list":
                stashes = repo.git.stash("list")
                return {"stashes": stashes.split("\n") if stashes else []}

        return {"error": f"Unknown action: {action}"}

    except InvalidGitRepositoryError:
        return {"error": f"Not a git repository: {repo_path}"}
    except Exception as e:
        return {"error": str(e)}
