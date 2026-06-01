"""
Virus Scanning — lightweight file scanning using YARA rules and heuristics.
"""
import os
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List
from core.tool_registry import registry, ToolParam


# Suspicious patterns for heuristic scanning
SUSPICIOUS_STRINGS = [
    b"cmd.exe", b"powershell", b"/bin/sh", b"/bin/bash",
    b"CreateRemoteThread", b"VirtualAllocEx", b"WriteProcessMemory",
    b"ShellExecute", b"WinExec", b"URLDownloadToFile",
    b"eval(", b"exec(", b"base64_decode",
    b"HKEY_LOCAL_MACHINE", b"HKEY_CURRENT_USER",
    b"\\system32\\", b"\\syswow64\\",
]

SUSPICIOUS_EXTENSIONS = {".exe", ".dll", ".bat", ".ps1", ".vbs", ".js", ".cmd", ".scr", ".pif", ".com"}


def compute_hashes(file_path: Path) -> Dict[str, str]:
    """Compute MD5, SHA1, SHA256 of a file."""
    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return {
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def heuristic_scan(file_path: Path) -> Dict[str, Any]:
    """Basic heuristic scanning for suspicious patterns."""
    findings = []
    risk_score = 0

    ext = file_path.suffix.lower()

    # Check extension
    if ext in SUSPICIOUS_EXTENSIONS:
        findings.append(f"Suspicious file extension: {ext}")
        risk_score += 2

    # Check file size anomalies
    size = file_path.stat().st_size
    if size == 0:
        findings.append("Empty file (0 bytes)")
        risk_score += 1
    elif ext in {".exe", ".dll"} and size < 1024:
        findings.append("Unusually small executable")
        risk_score += 3

    # Scan content for suspicious strings
    try:
        with open(file_path, "rb") as f:
            content = f.read(min(size, 10 * 1024 * 1024))  # max 10MB

        for pattern in SUSPICIOUS_STRINGS:
            if pattern in content:
                findings.append(f"Suspicious string found: {pattern.decode('utf-8', errors='replace')}")
                risk_score += 1

        # Check for high entropy (potential encryption/packing)
        if len(content) > 0:
            byte_counts = [0] * 256
            for byte in content[:10000]:
                byte_counts[byte] += 1
            total = min(len(content), 10000)
            import math
            entropy = -sum(
                (c / total) * math.log2(c / total) for c in byte_counts if c > 0
            )
            if entropy > 7.5:
                findings.append(f"High entropy ({entropy:.2f}) — possible packed/encrypted content")
                risk_score += 2

    except PermissionError:
        findings.append("Permission denied reading file")
    except Exception as e:
        findings.append(f"Scan error: {e}")

    return {
        "risk_score": min(risk_score, 10),
        "risk_level": "HIGH" if risk_score >= 7 else "MEDIUM" if risk_score >= 4 else "LOW",
        "findings": findings,
    }


def yara_scan(file_path: Path) -> Dict[str, Any]:
    """Scan with YARA rules if available."""
    try:
        import yara
        from config import YARA_RULES_DIR
        rules_files = list(YARA_RULES_DIR.glob("*.yar")) + list(YARA_RULES_DIR.glob("*.yara"))
        if not rules_files:
            return {"note": "No YARA rules found. Add .yar files to data/yara_rules/"}
        matches = []
        for rf in rules_files:
            try:
                rules = yara.compile(filepath=str(rf))
                m = rules.match(str(file_path))
                for match in m:
                    matches.append({"rule": match.rule, "file": rf.name, "tags": match.tags})
            except Exception as e:
                continue
        return {"yara_matches": matches, "rules_checked": len(rules_files)}
    except ImportError:
        return {"note": "yara-python not installed. Install with: pip install yara-python"}


@registry.tool(
    name="virus_scan",
    description="Scan files for malware using heuristic analysis and YARA rules. Computes file hashes (MD5, SHA1, SHA256).",
    category="Security",
    parameters=[
        ToolParam("path", "string", "File path to scan"),
        ToolParam("deep_scan", "string", "Enable deep heuristic scan (true/false)", required=False, default="true"),
    ],
)
def virus_scan(path: str, deep_scan: str = "true"):
    p = Path(path).resolve()
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path}"}

    result = {
        "file": str(p),
        "name": p.name,
        "size_bytes": p.stat().st_size,
        "hashes": compute_hashes(p),
    }

    if deep_scan.lower() == "true":
        result["heuristic"] = heuristic_scan(p)
        result["yara"] = yara_scan(p)

    verdict = result.get("heuristic", {}).get("risk_level", "UNKNOWN")
    result["verdict"] = verdict
    result["safe"] = verdict == "LOW"

    return result
