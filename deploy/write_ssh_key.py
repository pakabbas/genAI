#!/usr/bin/env python3
"""Write a normalized OpenSSH private key file from env or stdin."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def normalize_openssh_private_key(raw: str) -> str:
    key = raw.strip().replace("\r\n", "\n")
    if "\n" in key:
        return key if key.endswith("\n") else key + "\n"

    match = re.search(
        r"-----BEGIN OPENSSH PRIVATE KEY-----\s*(.+?)\s*-----END OPENSSH PRIVATE KEY-----",
        key,
        re.DOTALL,
    )
    if not match:
        raise ValueError("Unrecognized SSH private key format")

    body = re.sub(r"\s+", "", match.group(1))
    wrapped = "\n".join(body[i : i + 70] for i in range(0, len(body), 70))
    return f"-----BEGIN OPENSSH PRIVATE KEY-----\n{wrapped}\n-----END OPENSSH PRIVATE KEY-----\n"


def main() -> None:
    destination = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("SSH_KEY_PATH", ""))
    if not destination:
        raise SystemExit("Usage: write_ssh_key.py <destination>  (or set SSH_KEY_PATH)")

    raw = os.environ.get("SSH_PRIVATE_KEY", "")
    if not raw and not sys.stdin.isatty():
        raw = sys.stdin.read()
    if not raw:
        raise SystemExit("SSH_PRIVATE_KEY environment variable or stdin is required")

    destination.write_text(normalize_openssh_private_key(raw), encoding="utf-8")
    destination.chmod(0o600)


if __name__ == "__main__":
    main()
