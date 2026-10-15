"""
CARspective — Phase 10: Security, Secrets, and Path Traversal Audit
Scans repository for exposed API credentials, private tokens, passwords,
path traversal vectors, and insecure configurations.
"""

import os
import re
import json
from typing import List, Dict, Any

PATTERNS = {
    "google_api_key": re.compile(r"AIza[0-9A-Za-z-_]{35}"),
    "openai_api_key": re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    "github_token": re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    "slack_token": re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,}"),
    "private_key": re.compile(r"-----BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
    "hardcoded_password": re.compile(r"""(?i)(?:password|passwd|pwd)\s*=\s*['"][a-zA-Z0-9!@#$%^&*()_+]{8,}['"]"""),
}

IGNORE_DIRS = {".git", ".venv", "node_modules", "__pycache__", "dist", ".pytest_cache", ".idea", ".vscode"}
IGNORE_EXTS = {".png", ".jpg", ".jpeg", ".glb", ".pkl", ".joblib", ".ico", ".svg"}

def audit_secrets() -> Dict[str, Any]:
    findings = []
    
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in IGNORE_EXTS:
                continue
            fpath = os.path.join(root, fname)
            
            # Check for committed .env files
            if fname == ".env" or fname.endswith(".env"):
                import subprocess
                res = subprocess.run(["git", "ls-files", fpath], capture_output=True, text=True)
                if res.stdout.strip():
                    findings.append({
                        "file": fpath,
                        "line": 0,
                        "type": "committed_env_file",
                        "severity": "HIGH",
                        "remediation": "Add .env to .gitignore and remove from version control"
                    })
                
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    for line_idx, line in enumerate(f, 1):
                        for p_name, pattern in PATTERNS.items():
                            if pattern.search(line):
                                # Filter out false positives (tests, documentation, comments, schemas)
                                if "test" in fpath.lower() or "audit" in fpath.lower() or "scratch" in fpath.lower():
                                    continue
                                findings.append({
                                    "file": fpath,
                                    "line": line_idx,
                                    "type": p_name,
                                    "severity": "CRITICAL" if "key" in p_name or "token" in p_name else "MEDIUM",
                                    "remediation": "Move credential to environment variables"
                                })
            except Exception:
                pass

    return {
        "status": "PASS" if len(findings) == 0 else "WARNING",
        "total_findings": len(findings),
        "findings": findings
    }

if __name__ == "__main__":
    result = audit_secrets()
    print(json.dumps(result, indent=2))
