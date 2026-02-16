#!/usr/bin/env python3
"""Python helper for Obsidian Command API.

Standard-library-only. Handles all special characters correctly.

Two functions:
  obsidian_cmd  — execute CLI commands via POST (use for all markdown operations)
  obsidian_put  — write files to vault via PUT (use for non-markdown files,
                  or as fallback for markdown when POST fails)

Escaping: inside shlex double-quoted strings, only \\ and " need escaping.
Newlines, tabs, $, `, ', unicode (emoji, CJK) all pass through safely.
The JSON layer (json.dumps/json.loads) handles its own encoding transparently.
PUT bypasses shlex entirely — content goes straight to disk as raw bytes.
"""

import json
import urllib.error
import urllib.parse
import urllib.request


def obsidian_cmd(endpoint, token, command, params=None, flags=None, timeout=30):
    """Execute Obsidian CLI command via POST.

    Args:
        endpoint: API URL (e.g. "https://obs-api.example.com")
        token:    Bearer token string
        command:  CLI command (e.g. "read", "search", "daily:append")
        params:   Dict of param=value pairs (e.g. {"file": "Recipe"})
        flags:    List of flag strings (e.g. ["matches", "verbose"])
        timeout:  Request timeout in seconds

    Returns: Response body as string
    Raises:  RuntimeError on HTTP errors, ValueError on null bytes
    """
    parts = ["obsidian", command]
    for key, value in (params or {}).items():
        s = str(value)
        if "\x00" in s:
            raise ValueError(f"Null byte in parameter '{key}'")
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'{key}="{escaped}"')
    parts.extend(flags or [])
    payload = json.dumps({"commands": [" ".join(parts)]}).encode()
    req = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout).read().decode()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}") from e


def obsidian_put(endpoint, token, vault_path, content, timeout=30):
    """Write a file to the vault via PUT /vault/<path>.

    Args:
        endpoint:   API URL
        token:      Bearer token string
        vault_path: Path relative to vault root (e.g. "attachments/photo.png")
        content:    File content (str or bytes)
        timeout:    Request timeout in seconds

    Returns: Response body as string
    Raises:  RuntimeError on HTTP errors
    """
    if isinstance(content, str):
        content = content.encode("utf-8")
    url = f"{endpoint.rstrip('/')}/vault/{urllib.parse.quote(vault_path, safe='/')}"
    req = urllib.request.Request(
        url,
        data=content,
        method="PUT",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        return urllib.request.urlopen(req, timeout=timeout).read().decode()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode()}") from e


if __name__ == "__main__":
    # Quick smoke test — requires endpoint and token as arguments
    import sys

    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <endpoint> <token>")
        sys.exit(1)
    ep, tk = sys.argv[1], sys.argv[2]
    print(obsidian_cmd(ep, tk, "vault"))
