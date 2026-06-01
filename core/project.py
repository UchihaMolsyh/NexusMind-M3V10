"""
Project Manager — handles workspace roots, file tree traversal, and project context.
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger("nexusmind.project")

class ProjectManager:
    """Manages the active workspace and project metadata."""

    def __init__(self):
        self.workspace_root: Optional[Path] = None
        self.project_name: str = "Unnamed Project"
        self.active_files: List[Path] = []

    def set_workspace(self, path: str) -> Dict[str, Any]:
        """Set the current workspace root."""
        p = Path(path).resolve()
        if not p.exists():
            return {"success": False, "error": f"Path does not exist: {path}"}
        if not p.is_dir():
            return {"success": False, "error": f"Path is not a directory: {path}"}
        
        self.workspace_root = p
        self.project_name = p.name
        logger.info(f"Workspace set to: {self.workspace_root}")
        return {"success": True, "root": str(self.workspace_root), "name": self.project_name}

    def get_file_tree(self, max_depth: int = 3) -> List[Dict[str, Any]]:
        """Generate a tree representation of the workspace."""
        if not self.workspace_root:
            return []
        
        return self._build_tree(self.workspace_root, max_depth)

    def _build_tree(self, root: Path, depth: int) -> List[Dict[str, Any]]:
        if depth < 0:
            return []
        
        items = []
        try:
            for entry in sorted(root.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if entry.name.startswith(('.', '__pycache__', 'node_modules', '.venv', 'venv')):
                    continue
                
                item = {
                    "name": entry.name,
                    "path": str(entry),
                    "type": "directory" if entry.is_dir() else "file"
                }
                if entry.is_dir():
                    item["children"] = self._build_tree(entry, depth - 1)
                items.append(item)
        except Exception as e:
            logger.error(f"Error building tree for {root}: {e}")
            
        return items

    def initialize_project(self, template: str) -> Dict[str, Any]:
        """Bootstrap a project with a template."""
        if not self.workspace_root:
            return {"success": False, "error": "No workspace root set"}
        
        templates = {
            "python": {
                "main.py": 'print("Hello from NexusMind Project!")',
                "requirements.txt": "fastapi\nuvicorn",
                "README.md": f"# {self.project_name}\nCreated with NexusMind."
            },
            "web": {
                "index.html": "<!DOCTYPE html><html><body><h1>Hello!</h1></body></html>",
                "style.css": "body { font-family: sans-serif; }",
                "script.js": 'console.log("Ready!");'
            }
        }
        
        if template not in templates:
            return {"success": False, "error": f"Unknown template: {template}"}
        
        try:
            for filename, content in templates[template].items():
                file_path = self.workspace_root / filename
                file_path.write_text(content)
            return {"success": True, "files": list(templates[template].keys())}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_project_summary(self) -> str:
        """Get a summary string for the system prompt."""
        if not self.workspace_root:
            return ""
        
        tree = self.get_file_tree(max_depth=1)
        files = [item["name"] for item in tree]
        return f"\nCURRENT PROJECT: {self.project_name}\nROOT: {self.workspace_root}\nFILES (Top-level): {', '.join(files)}"

# Global project manager instance
project_manager = ProjectManager()
