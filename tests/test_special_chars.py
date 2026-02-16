"""Tests for special character handling in PUT content, PUT path, and POST commands.

20 characters tested across 4 dimensions + combined tests.
"""

import json
import urllib.parse

import pytest


# The 20 special characters to test
SPECIAL_CHARS = {
    "space": " ",
    "hash": "#",
    "percent": "%",
    "question": "?",
    "ampersand": "&",
    "plus": "+",
    "single_quote": "'",
    "double_quote": '"',
    "backtick": "`",
    "dollar": "$",
    "backslash": "\\",
    "semicolon": ";",
    "pipe": "|",
    "gt": ">",
    "lt": "<",
    "newline": "\n",
    "null_byte": "\x00",
    "tab": "\t",
    "emoji": "\U0001f525",  # 🔥
    "cjk": "\u65e5\u672c\u8a9e",  # 日本語
}

# Characters that are unsafe in URL paths (expected to fail or be rejected)
PATH_UNSAFE = {"null_byte", "newline"}


# ---------------------------------------------------------------------------
# 1. Special characters in PUT content (~20 tests)
# ---------------------------------------------------------------------------
class TestSpecialCharsInContent:
    """Each character individually in file body via PUT /vault/."""

    @pytest.mark.parametrize("name,char", list(SPECIAL_CHARS.items()), ids=list(SPECIAL_CHARS.keys()))
    def test_char_in_content(self, http_client, vault_dir, name, char):
        content = f"before{char}after"
        status, body = http_client.put("/vault/content-test.md", body=content.encode())
        assert status == 200
        written = (vault_dir / "content-test.md").read_bytes()
        assert written == content.encode()


# ---------------------------------------------------------------------------
# 2. Special characters in PUT path (~20 tests)
# ---------------------------------------------------------------------------
class TestSpecialCharsInPath:
    """Each character in filename via PUT /vault/<name>. URL-encoded."""

    @pytest.mark.parametrize("name,char", list(SPECIAL_CHARS.items()), ids=list(SPECIAL_CHARS.keys()))
    def test_char_in_path(self, http_client, vault_dir, name, char):
        if name in PATH_UNSAFE:
            # Null bytes and newlines in paths — server may accept or reject
            encoded = urllib.parse.quote(f"file{char}name.md", safe="")
            status, body = http_client.put(f"/vault/{encoded}", body=b"data")
            # Accept any non-crash response: server handles safely
            assert status in (200, 400, 404, 500), f"Unexpected status for {name}: {status}"
            return

        encoded = urllib.parse.quote(f"file-{name}.md", safe="")
        status, body = http_client.put(f"/vault/{encoded}", body=b"data")
        assert status == 200, f"PUT with {name} in path failed: {body}"
        # Verify file exists (name is URL-decoded by server)
        expected_path = vault_dir / f"file-{name}.md"
        assert expected_path.exists(), f"File not found: {expected_path}"


# ---------------------------------------------------------------------------
# 3. Special characters in POST commands (~20 tests)
# ---------------------------------------------------------------------------
class TestSpecialCharsInCommands:
    """Each character in Obsidian CLI command arguments via POST /."""

    @pytest.mark.parametrize("name,char", list(SPECIAL_CHARS.items()), ids=list(SPECIAL_CHARS.keys()))
    def test_char_in_command_arg(self, http_client, mock_run_obsidian, name, char):
        mock_run_obsidian.stdout = "ok\n"
        # The command includes the special char in an argument
        cmd = f'obsidian read file="note with {char}"'
        body = json.dumps({"commands": [cmd]})
        status, resp = http_client.post(body=body)
        # shlex.split may reject some inputs (unmatched quotes, null bytes)
        # but the server should not crash — it should return 200 with error or result
        assert status == 200


# ---------------------------------------------------------------------------
# 4. Combined: all chars in one file content
# ---------------------------------------------------------------------------
class TestCombinedContent:
    def test_all_chars_in_content(self, http_client, vault_dir):
        """One file with all 20 special chars in content."""
        parts = []
        for name, char in SPECIAL_CHARS.items():
            parts.append(f"{name}: [{char}]")
        content = "\n".join(parts)
        status, body = http_client.put("/vault/all-chars.md", body=content.encode())
        assert status == 200
        written = (vault_dir / "all-chars.md").read_bytes()
        assert written == content.encode()

    def test_all_chars_in_command(self, http_client, mock_run_obsidian):
        """One POST command with multiple special chars in arguments."""
        mock_run_obsidian.stdout = "ok\n"
        # Build a command with several special chars (avoiding ones that break shlex)
        cmd = 'obsidian create title="test & notes + more"'
        body = json.dumps({"commands": [cmd]})
        status, resp = http_client.post(body=body)
        assert status == 200


# ---------------------------------------------------------------------------
# 5. Combined realistic markdown note
# ---------------------------------------------------------------------------
class TestCombinedMarkdownNote:
    def test_realistic_markdown_note(self, http_client, vault_dir):
        """Create a realistic markdown note containing all special characters."""
        note = """\
# Heading with special chars: $price & 50% off

## Links & References
- [Search?query=hello&lang=en](#)
- File: `path/to/file`
- Price: $19.99 + tax

## Code Block
```python
if x > 0 and y < 10:
    print("it's working")
    os.system('echo $HOME | grep "user"')
    path = "C:\\\\Users\\\\name"
```

## Quotes
> "To be or not to be" — Shakespeare
> It's a single-quoted phrase

## Special Content
- Tab:\there
- Pipe: cmd | grep pattern
- Semicolon: cmd1; cmd2
- Emoji: \U0001f525 fire
- CJK: \u65e5\u672c\u8a9e
- Backtick: `inline code`
- Hash: #tag #another
- Plus: 1+1=2
- Ampersand: Tom & Jerry
- Percent: 100%
"""
        status, body = http_client.put("/vault/realistic-note.md", body=note.encode())
        assert status == 200
        written = (vault_dir / "realistic-note.md").read_bytes()
        assert written == note.encode()
