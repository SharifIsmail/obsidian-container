"""Tests for the obsidian_api.py helper script.

Tests the full round-trip: helper escaping → JSON → HTTP → server → shlex.split → argv.
"""

import os
import sys

import pytest

# Make the helper importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "obsidian-skill", "scripts"))
from obsidian_api import obsidian_cmd, obsidian_put


# Same 20 special chars as test_special_chars.py
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
    "tab": "\t",
    "emoji": "\U0001f525",  # 🔥
    "cjk": "\u65e5\u672c\u8a9e",  # 日本語
}

# Null byte tested separately (helper rejects it before HTTP)
ROUNDTRIP_CHARS = {k: v for k, v in SPECIAL_CHARS.items()}


# ---------------------------------------------------------------------------
# 1. obsidian_cmd unit tests
# ---------------------------------------------------------------------------
class TestObsidianCmdUnit:
    def test_basic_command(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        result = obsidian_cmd(http_client.base_url, "test-token", "vault")
        assert "ok" in result

    def test_with_params(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "content\n"
        result = obsidian_cmd(http_client.base_url, "test-token", "read",
                              params={"file": "Recipe"})
        assert "content" in result
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv == ["obsidian", "read", 'file=Recipe']

    def test_with_flags(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "tasks",
                     flags=["daily", "todo", "verbose"])
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv == ["obsidian", "tasks", "daily", "todo", "verbose"]

    def test_multiple_params_and_flags(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "create",
                     params={"name": "My Note", "content": "hello world"},
                     flags=["overwrite", "silent"])
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[0] == "obsidian"
        assert argv[1] == "create"
        assert 'name=My Note' in argv
        assert 'content=hello world' in argv
        assert "overwrite" in argv
        assert "silent" in argv

    def test_null_byte_rejected(self, http_client):
        with pytest.raises(ValueError, match="Null byte"):
            obsidian_cmd(http_client.base_url, "test-token", "read",
                         params={"file": "bad\x00file"})

    def test_backslash_escaping(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "read",
                     params={"file": "path\\to\\file"})
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[2] == "file=path\\to\\file"

    def test_double_quote_escaping(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "read",
                     params={"file": 'say "hello"'})
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[2] == 'file=say "hello"'

    def test_backslash_and_quote_combined(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "read",
                     params={"file": 'C:\\path\\"quoted"'})
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[2] == 'file=C:\\path\\"quoted"'

    def test_http_error_raises_runtime_error(self, http_client):
        with pytest.raises(RuntimeError, match="HTTP 401"):
            obsidian_cmd(http_client.base_url, "wrong-token", "vault")

    def test_empty_params(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "vault",
                     params={}, flags=[])
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv == ["obsidian", "vault"]


# ---------------------------------------------------------------------------
# 2. obsidian_put unit tests
# ---------------------------------------------------------------------------
class TestObsidianPutUnit:
    def test_string_content(self, http_client, vault_dir):
        result = obsidian_put(http_client.base_url, "test-token",
                              "test.md", "hello")
        assert "OK" in result
        assert (vault_dir / "test.md").read_bytes() == b"hello"

    def test_bytes_content(self, http_client, vault_dir):
        obsidian_put(http_client.base_url, "test-token",
                     "binary.bin", b"\x89PNG\r\n")
        assert (vault_dir / "binary.bin").read_bytes() == b"\x89PNG\r\n"

    def test_nested_path(self, http_client, vault_dir):
        obsidian_put(http_client.base_url, "test-token",
                     "sub/dir/file.md", "nested")
        assert (vault_dir / "sub" / "dir" / "file.md").read_bytes() == b"nested"

    def test_url_encodes_path(self, http_client, vault_dir):
        obsidian_put(http_client.base_url, "test-token",
                     "file with spaces.md", "data")
        assert (vault_dir / "file with spaces.md").read_bytes() == b"data"

    def test_http_error_raises_runtime_error(self, http_client):
        with pytest.raises(RuntimeError, match="HTTP 401"):
            obsidian_put(http_client.base_url, "wrong-token",
                         "test.md", "data")


# ---------------------------------------------------------------------------
# 3. POST round-trip: special chars through helper → server → verify argv
# ---------------------------------------------------------------------------
class TestObsidianCmdRoundTrip:
    """Verify that values survive: helper escaping → JSON → HTTP → shlex.split."""

    @pytest.mark.parametrize("name,char", list(ROUNDTRIP_CHARS.items()),
                             ids=list(ROUNDTRIP_CHARS.keys()))
    def test_special_char_in_param(self, http_client, mock_run_obsidian, name, char):
        mock_run_obsidian.stdout = "ok\n"
        original_value = f"note with {char} inside"
        obsidian_cmd(http_client.base_url, "test-token", "read",
                     params={"file": original_value})
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[0] == "obsidian"
        assert argv[1] == "read"
        # Extract value after 'file='
        recovered = argv[2].split("=", 1)[1]
        assert recovered == original_value, (
            f"Round-trip failed for {name}: "
            f"sent {original_value!r}, got {recovered!r}"
        )

    def test_all_chars_combined_in_param(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        # Build a value with all special chars
        combined = "".join(ROUNDTRIP_CHARS.values())
        obsidian_cmd(http_client.base_url, "test-token", "read",
                     params={"file": combined})
        argv = mock_run_obsidian.captured_calls[-1]
        recovered = argv[2].split("=", 1)[1]
        assert recovered == combined

    def test_multiline_content_param(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        content = "---\ntags: [test]\nsource: \"[[Ref]]\"\n---\n# Title\nBody."
        obsidian_cmd(http_client.base_url, "test-token", "create",
                     params={"name": "Note", "content": content})
        argv = mock_run_obsidian.captured_calls[-1]
        content_arg = [a for a in argv if a.startswith("content=")][0]
        recovered = content_arg.split("=", 1)[1]
        assert recovered == content

    def test_value_with_equals_sign(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "read",
                     params={"file": "a=b=c"})
        argv = mock_run_obsidian.captured_calls[-1]
        recovered = argv[2].split("=", 1)[1]
        assert recovered == "a=b=c"


# ---------------------------------------------------------------------------
# 4. Realistic CLI command patterns
# ---------------------------------------------------------------------------
class TestRealisticCommands:
    """Test realistic multi-param commands through the helper."""

    def test_create_with_content(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "create",
                     params={"name": "Trip to Paris",
                             "content": "# Trip\n\nNotes about the trip."},
                     flags=["overwrite"])
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[0:2] == ["obsidian", "create"]
        assert "overwrite" in argv
        name_arg = [a for a in argv if a.startswith("name=")][0]
        assert name_arg == "name=Trip to Paris"

    def test_search_with_query(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "found 3 results\n"
        result = obsidian_cmd(http_client.base_url, "test-token", "search",
                              params={"query": "meeting & notes"},
                              flags=["matches", "total"])
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[0:2] == ["obsidian", "search"]
        assert "matches" in argv
        assert "total" in argv
        query_arg = [a for a in argv if a.startswith("query=")][0]
        assert query_arg == "query=meeting & notes"

    def test_daily_append(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "daily:append",
                     params={"content": "- [ ] Buy groceries $5"},
                     flags=["silent"])
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[0:2] == ["obsidian", "daily:append"]
        content_arg = [a for a in argv if a.startswith("content=")][0]
        assert content_arg == "content=- [ ] Buy groceries $5"

    def test_property_set(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "property:set",
                     params={"name": "source", "value": '[[My "Special" Note]]',
                             "file": "Target"})
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[0:2] == ["obsidian", "property:set"]
        value_arg = [a for a in argv if a.startswith("value=")][0]
        assert value_arg == 'value=[[My "Special" Note]]'

    def test_eval_with_javascript(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "42\n"
        js = 'app.vault.getFiles().filter(f => f.path.includes("test")).length'
        result = obsidian_cmd(http_client.base_url, "test-token", "eval",
                              params={"code": js})
        argv = mock_run_obsidian.captured_calls[-1]
        code_arg = [a for a in argv if a.startswith("code=")][0]
        assert code_arg.split("=", 1)[1] == js

    def test_create_with_template(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        obsidian_cmd(http_client.base_url, "test-token", "create",
                     params={"path": "Notes/Projects/New Project.md",
                             "template": "Project Template"},
                     flags=["silent", "newtab"])
        argv = mock_run_obsidian.captured_calls[-1]
        assert argv[0:2] == ["obsidian", "create"]
        path_arg = [a for a in argv if a.startswith("path=")][0]
        assert path_arg == "path=Notes/Projects/New Project.md"
        assert "silent" in argv
        assert "newtab" in argv


# ---------------------------------------------------------------------------
# 5. PUT round-trip: special chars in content through helper → disk
# ---------------------------------------------------------------------------
class TestObsidianPutRoundTrip:
    @pytest.mark.parametrize("name,char", list(ROUNDTRIP_CHARS.items()),
                             ids=list(ROUNDTRIP_CHARS.keys()))
    def test_special_char_in_content(self, http_client, vault_dir, name, char):
        content = f"before{char}after"
        obsidian_put(http_client.base_url, "test-token",
                     "roundtrip-test.md", content)
        written = (vault_dir / "roundtrip-test.md").read_bytes()
        assert written == content.encode()

    def test_realistic_markdown_note(self, http_client, vault_dir):
        note = '---\ntags: [project]\nsource: "[[Reference]]"\n---\n'
        note += "# My Note\n\n"
        note += 'Content with "quotes", $dollars, `backticks`, and \'apostrophes\'.\n'
        note += "Price: $5 & tax | total > $6\n"
        note += "Emoji: \U0001f525 CJK: \u65e5\u672c\u8a9e\n"
        obsidian_put(http_client.base_url, "test-token",
                     "Notes/realistic.md", note)
        written = (vault_dir / "Notes" / "realistic.md").read_bytes()
        assert written == note.encode()
