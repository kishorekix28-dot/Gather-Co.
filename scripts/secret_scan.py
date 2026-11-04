#!/usr/bin/env python3
"""Scan git-tracked (or staged) files for secrets before committing/pushing.

Usage: python scripts/secret_scan.py [--staged]
Exits 1 if anything suspicious is found.
"""
import re
import subprocess
import sys

PATTERNS = {
    "Private key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "AWS access key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    "OpenAI/Anthropic key": re.compile(r"sk-(ant-)?[A-Za-z0-9_\-]{20,}"),
    "Google API key": re.compile(r"AIza[0-9A-Za-z\-_]{35}"),
    "Slack token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    "Mongo URI with password": re.compile(r"mongodb(\+srv)?://[^\s:/@]+:[^\s@/]+@"),
    "Postgres URI with password": re.compile(r"postgres(ql)?://[^\s:/@]+:[^\s@/]+@"),
    "Assigned secret": re.compile(
        r"""(?i)^\s*(SECRET_KEY|AI_API_KEY|DJANGO_ADMIN_PASSWORD|DEMO_\w+_PASSWORD|MONGODB_URI|DATABASE_URL)\s*=\s*['"]?[^\s'"#]{8,}"""),
}
FORBIDDEN_FILES = re.compile(r"(^|/)(\.env|db\.sqlite3|.*\.pem|.*\.key)$")
ALLOW = {"scripts/secret_scan.py"}
# Lines that read secrets from the environment or show documented placeholders are fine.
SAFE_LINE = re.compile(r"os\.environ|getenv|secrets\.token_|<password>|<user>|\$\{?[A-Z_]+")


def tracked_files(staged):
    cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"] if staged else ["git", "ls-files"]
    return [f for f in subprocess.check_output(cmd, text=True).splitlines() if f]


def main():
    staged = "--staged" in sys.argv
    problems = []
    for path in tracked_files(staged):
        if FORBIDDEN_FILES.search(path):
            problems.append(f"{path}: file must not be committed")
            continue
        if path in ALLOW:
            continue
        try:
            text = open(path, encoding="utf-8").read()
        except (UnicodeDecodeError, FileNotFoundError, IsADirectoryError):
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if SAFE_LINE.search(line):
                continue
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    problems.append(f"{path}:{lineno}: possible {name}")
    if problems:
        print("Secret scan FAILED:")
        print("\n".join(problems))
        return 1
    print(f"Secret scan passed: {len(tracked_files(staged))} files checked, no secrets found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
