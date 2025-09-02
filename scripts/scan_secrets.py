#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IGNORE_DIRS = {
    ".git", ".venv", "__pycache__", ".pytest_cache", ".idea", ".github",
    "src/scribe/output", "instance/recipients"
}

# Patterns: generic high-risk tokens and non-example emails in repo-tracked assets
PATTERNS = {
    "possible_aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "generic_secret_assign": re.compile(r"(?i)(secret|password|token|apikey|api_key)\s*[:=]\s*['\"][^'\"]+['\"]"),
    "private_key_block": re.compile(r"-----BEGIN (?:RSA|EC|DSA|OPENSSH) PRIVATE KEY-----"),
    "non_example_email": re.compile(r"\b(?![A-Za-z0-9._%+-]+@example\.com\b)[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
}

# File-level allowlist for non-example emails (only in tests or explicitly allowed files)
ALLOWED_NON_EXAMPLE_PATHS = {
    # Add test-only data files below if needed
}

TEXT_EXTS = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".csv", ".tsv", ".j2"
}

def is_ignored(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    parts = rel.parts
    if any(p in IGNORE_DIRS for p in parts):
        return True
    return False

def mask_email(addr: str) -> str:
    try:
        user, domain = addr.split("@", 1)
        if len(user) <= 2:
            masked_user = user[0] + "*"
        else:
            masked_user = user[0] + "***" + user[-1]
        return f"{masked_user}@{domain}"
    except Exception:
        return "***"

def scan_file(path: Path):
    rel = str(path.relative_to(ROOT)).replace("\\", "/")
    try:
        if not path.suffix.lower() in TEXT_EXTS:
            return []
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []
    findings = []
    for name, regex in PATTERNS.items():
        if name == "non_example_email" and rel in ALLOWED_NON_EXAMPLE_PATHS:
            continue
        for m in regex.finditer(text):
            val = m.group(0)
            if name == "non_example_email":
                masked = mask_email(val)
            else:
                masked = (val[:2] + "***" + val[-2:]) if len(val) > 6 else "***"
            snippet = text[max(0, m.start()-20):m.end()+20].replace(val, masked)
            findings.append((name, rel, masked, snippet))
    return findings

def main():
    all_findings = []
    for dirpath, _, filenames in os.walk(ROOT):
        dpath = Path(dirpath)
        if is_ignored(dpath):
            continue
        for fn in filenames:
            fpath = dpath / fn
            if is_ignored(fpath):
                continue
            findings = scan_file(fpath)
            if findings:
                for name, rel, masked, snippet in findings:
                    print(f"[{name}] {rel}: {masked}\n  ... {snippet} ...")
                all_findings.extend(findings)

    if all_findings:
        print(f"\nFound {len(all_findings)} potential secret(s). Failing.")
        sys.exit(1)
    print("No potential secrets found.")
    sys.exit(0)

if __name__ == "__main__":
    main()
