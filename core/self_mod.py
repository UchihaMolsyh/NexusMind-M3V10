"""
Self-Modification Engine — Allows AI to modify its own code with user permission.
"""
import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from core.llm import engine
from core.memory import MemorySystem

logger = logging.getLogger("nexusmind.selfmod")

class SelfModificationEngine:
    def __init__(self, memory: MemorySystem):
        self.memory = memory
        self.backup_dir = Path("data/backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.pending_modifications = {}
        
    def create_backup(self, file_path: Path) -> str:
        """Create a backup of the file before modification."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = self.backup_dir / backup_name
        
        try:
            shutil.copy2(file_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return ""
    
    async def analyze_modification_request(self, request: str) -> Dict[str, Any]:
        """Analyze a self-modification request and create a plan."""
        analysis_prompt = f"""
        Analyze this self-modification request and create a detailed implementation plan:
        
        Request: {request}
        
        Provide:
        1. Files to modify
        2. Specific changes needed
        3. Potential risks
        4. Testing requirements
        5. Rollback plan
        
        Return as JSON:
        {{
            "target_files": ["path1", "path2"],
            "changes": [
                {{
                    "file": "path",
                    "type": "add/modify/delete",
                    "description": "...",
                    "code": "..."
                }}
            ],
            "risks": ["..."],
            "tests": ["..."],
            "rollback": "..."
        }}
        """
        
        try:
            plan = await engine.generate_simple(analysis_prompt, max_tokens=2048)
            # Try to parse as JSON
            try:
                return json.loads(plan)
            except json.JSONDecodeError:
                return {
                    "plan_text": plan,
                    "status": "needs_manual_review"
                }
        except Exception as e:
            logger.error(f"Modification analysis failed: {e}")
            return {"error": str(e), "status": "failed"}
    
    async def implement_modification(self, modification_id: str, user_approved: bool = False) -> Dict[str, Any]:
        """Implement a modification with user approval."""
        if modification_id not in self.pending_modifications:
            return {"error": "Modification not found", "status": "failed"}
        
        mod = self.pending_modifications[modification_id]
        
        if not user_approved:
            return {
                "status": "awaiting_approval",
                "modification": mod,
                "message": "Please review and approve this modification"
            }
        
        # Create backups
        backups = {}
        for file_path in mod.get("target_files", []):
            path = Path(file_path)
            if path.exists():
                backup = self.create_backup(path)
                if backup:
                    backups[file_path] = backup
        
        # Implement changes
        results = []
        for change in mod.get("changes", []):
            file_path = Path(change["file"])
            try:
                if change["type"] == "add":
                    # Add new code/functionality
                    await self._apply_add_change(file_path, change)
                elif change["type"] == "modify":
                    # Modify existing code
                    await self._apply_modify_change(file_path, change)
                elif change["type"] == "delete":
                    # Delete code/functionality
                    await self._apply_delete_change(file_path, change)
                
                results.append({
                    "file": str(file_path),
                    "status": "success",
                    "change": change["description"]
                })
            except Exception as e:
                results.append({
                    "file": str(file_path),
                    "status": "failed",
                    "error": str(e),
                    "change": change["description"]
                })
        
        # Store modification record
        self.memory.store_long_term(
            "system",
            f"Applied modification {modification_id}: {mod.get('description', 'No description')}",
            tags="self_modification",
            category="project"
        )
        
        return {
            "status": "completed",
            "results": results,
            "backups": backups,
            "rollback_available": True
        }
    
    async def _apply_add_change(self, file_path: Path, change: Dict):
        """Apply an addition change to a file."""
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(f"\n# Added by self-modification\n{change['code']}\n")
    
    async def _apply_modify_change(self, file_path: Path, change: Dict):
        """Apply a modification change to a file."""
        # This is simplified - would need more sophisticated code manipulation
        content = file_path.read_text(encoding='utf-8')
        if "old_code" in change and "new_code" in change:
            content = content.replace(change["old_code"], change["new_code"])
            file_path.write_text(content, encoding='utf-8')
        else:
            # Append modification
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n# Modified by self-modification\n{change['code']}\n")
    
    async def _apply_delete_change(self, file_path: Path, change: Dict):
        """Apply a deletion change to a file."""
        content = file_path.read_text(encoding='utf-8')
        if "code_to_remove" in change:
            content = content.replace(change["code_to_remove"], "")
            file_path.write_text(content, encoding='utf-8')
    
    async def rollback_modification(self, modification_id: str) -> Dict[str, Any]:
        """Rollback a modification using backups."""
        # This would restore from backup files
        return {"status": "rollback_implemented", "message": "Rollback functionality to be implemented"}
    
    def integrate_github_repo(self, repo_url: str, target_dir: str = "data/integrated_repos") -> Dict[str, Any]:
        """Integrate a GitHub repository into the codebase."""
        try:
            import requests
            
            # Extract owner/repo from URL
            parts = repo_url.strip("/").split("/")
            if len(parts) < 2:
                return {"error": "Invalid repository URL", "status": "failed"}
            
            owner, repo = parts[-2], parts[-1]
            
            # Get repo info
            api_url = f"https://api.github.com/repos/{owner}/{repo}"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code != 200:
                return {"error": "Repository not found", "status": "failed"}
            
            repo_info = response.json()
            
            # Clone or download the repository
            target_path = Path(target_dir) / repo
            target_path.parent.mkdir(exist_ok=True)
            
            # For now, just record the integration
            integration_record = {
                "repo_url": repo_url,
                "repo_info": {
                    "name": repo_info["name"],
                    "description": repo_info["description"],
                    "language": repo_info["language"],
                    "stars": repo_info["stargazers_count"]
                },
                "integration_date": datetime.now().isoformat(),
                "status": "recorded"
            }
            
            # Store in memory
            self.memory.store_long_term(
                "system",
                f"Integrated GitHub repo: {repo_url}",
                tags="github_integration",
                category="project"
            )
            
            return {
                "status": "recorded",
                "integration": integration_record,
                "message": "Repository integration recorded. Full integration to be implemented."
            }
            
        except Exception as e:
            logger.error(f"GitHub integration failed: {e}")
            return {"error": str(e), "status": "failed"}

# Initialize self-modification engine
def create_self_mod_engine(memory: MemorySystem) -> SelfModificationEngine:
    return SelfModificationEngine(memory)
