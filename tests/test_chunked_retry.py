"""Tests for CLI chunked retry fallback.

Tests all 7 content-bearing commands × 3 content lengths:
  - short (500 chars): no timeout, no chunking
  - medium (1200 chars): triggers timeout on first try, chunks succeed
  - long (2500 chars): no timeout, no chunking

21 tests total.
"""

import subprocess

import cmd_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SHORT = "A" * 500    # below danger zone
MEDIUM = "B" * 1200  # inside danger zone (~1060-1700)
LONG = "C" * 2500    # above danger zone


def _make_timeout_mock(monkeypatch):
    """Mock _run_obsidian that simulates the Electron bug.

    Times out when total content length is in the danger zone (1000-1800).
    Returns success otherwise.
    """
    calls = []

    def fake_run(argv, timeout=30):
        calls.append(argv)
        # Find content param in argv
        content_len = 0
        for arg in argv:
            if arg.startswith("content="):
                content_len = len(arg) - len("content=")
                break
        # Simulate Electron bug: timeout for danger zone content
        if 1000 <= content_len <= 1800:
            raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)
        return subprocess.CompletedProcess(
            args=argv, returncode=0,
            stdout=f"OK\n", stderr="",
        )

    monkeypatch.setattr(cmd_service, "_run_obsidian", fake_run)
    return calls


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

class TestCreateChunking:
    def test_short_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian create path="test.md" content="{SHORT}" overwrite'
        )
        assert "[error]" not in result
        assert len(calls) == 1  # single call, no retry

    def test_medium_chunks(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian create path="test.md" content="{MEDIUM}" overwrite'
        )
        assert "[error]" not in result
        # First call times out, then chunked: create + append(s)
        assert len(calls) >= 3  # 1 timeout + at least 2 chunks
        # First retry chunk is create
        assert calls[1][1] == "create"
        # Subsequent chunks are append with inline
        for call in calls[2:]:
            assert call[1] == "append"
            assert "inline" in call

    def test_long_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian create path="test.md" content="{LONG}" overwrite'
        )
        assert "[error]" not in result
        assert len(calls) == 1

    def test_medium_append_targets_actual_created_path(self, tmp_config, monkeypatch):
        """When Obsidian renames a file (e.g. 'Note.md' → 'Note 1.md'),
        the append must target the actual created path, not the requested one."""
        orig_calls = []

        def fake_run(argv, timeout=30):
            orig_calls.append(list(argv))
            content_len = 0
            for arg in argv:
                if arg.startswith("content="):
                    content_len = len(arg) - len("content=")
                    break
            if 1000 <= content_len <= 1800:
                raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)
            if argv[1] == "create":
                # Simulate Obsidian renaming because file exists
                return subprocess.CompletedProcess(
                    args=argv, returncode=0,
                    stdout="Created: Notes/Note 1.md\n", stderr="",
                )
            return subprocess.CompletedProcess(
                args=argv, returncode=0,
                stdout="Appended to: Notes/Note 1.md\n", stderr="",
            )

        monkeypatch.setattr(cmd_service, "_run_obsidian", fake_run)
        result = cmd_service.execute_command(
            f'obsidian create path="Notes/Note.md" content="{MEDIUM}" overwrite'
        )
        assert "[error]" not in result
        assert len(orig_calls) >= 3
        # The append must target the ACTUAL created path, not the original
        for call in orig_calls[2:]:
            assert call[1] == "append"
            # Check that file= or path= points to the renamed file
            file_args = [a for a in call if a.startswith("file=") or a.startswith("path=")]
            assert any("Note 1" in a for a in file_args), \
                f"Append should target 'Note 1.md' but got {file_args}"


# ---------------------------------------------------------------------------
# append
# ---------------------------------------------------------------------------

class TestAppendChunking:
    def test_short_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian append path="test.md" content="{SHORT}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1

    def test_medium_chunks(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian append path="test.md" content="{MEDIUM}"'
        )
        assert "[error]" not in result
        assert len(calls) >= 3
        # All chunks are append
        for call in calls[1:]:
            assert call[1] == "append"
        # Continuation chunks have inline flag
        for call in calls[2:]:
            assert "inline" in call

    def test_long_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian append path="test.md" content="{LONG}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# prepend
# ---------------------------------------------------------------------------

class TestPrependChunking:
    def test_short_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian prepend path="test.md" content="{SHORT}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1

    def test_medium_chunks_reversed(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        content = "AAAA\n" * 240  # 1200 chars, has newlines for split points
        escaped = content.replace("\n", "\\n")
        result = cmd_service.execute_command(
            f'obsidian prepend path="test.md" content="{escaped}"'
        )
        assert "[error]" not in result
        assert len(calls) >= 3
        # First retry chunk is prepend (last chunk of content, applied first)
        assert calls[1][1] == "prepend"
        # Subsequent chunks are also prepend with inline
        for call in calls[2:]:
            assert call[1] == "prepend"
            assert "inline" in call

    def test_long_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian prepend path="test.md" content="{LONG}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# daily:append
# ---------------------------------------------------------------------------

class TestDailyAppendChunking:
    def test_short_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian daily:append content="{SHORT}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1

    def test_medium_chunks(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian daily:append content="{MEDIUM}"'
        )
        assert "[error]" not in result
        assert len(calls) >= 3
        # First retry chunk is daily:append
        assert calls[1][1] == "daily:append"
        # Continuation chunks are also daily:append with inline
        for call in calls[2:]:
            assert call[1] == "daily:append"
            assert "inline" in call

    def test_long_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian daily:append content="{LONG}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# daily:prepend
# ---------------------------------------------------------------------------

class TestDailyPrependChunking:
    def test_short_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian daily:prepend content="{SHORT}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1

    def test_medium_chunks_reversed(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian daily:prepend content="{MEDIUM}"'
        )
        assert "[error]" not in result
        assert len(calls) >= 3
        # First retry chunk is daily:prepend (last chunk, applied first)
        assert calls[1][1] == "daily:prepend"
        # Continuation chunks are also daily:prepend with inline (reversed order)
        for call in calls[2:]:
            assert call[1] == "daily:prepend"
            assert "inline" in call

    def test_long_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian daily:prepend content="{LONG}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# unique
# ---------------------------------------------------------------------------

class TestUniqueChunking:
    def test_short_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian unique content="{SHORT}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1

    def test_medium_chunks(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        # unique returns a created path that we need for appends
        call_count = [0]
        orig_calls = []

        def fake_run(argv, timeout=30):
            orig_calls.append(list(argv))
            content_len = 0
            for arg in argv:
                if arg.startswith("content="):
                    content_len = len(arg) - len("content=")
                    break
            if 1000 <= content_len <= 1800:
                raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)
            # unique returns the created file path
            if argv[1] == "unique":
                return subprocess.CompletedProcess(
                    args=argv, returncode=0,
                    stdout="Created 202601011200.md\n", stderr="",
                )
            return subprocess.CompletedProcess(
                args=argv, returncode=0,
                stdout="OK\n", stderr="",
            )

        monkeypatch.setattr(cmd_service, "_run_obsidian", fake_run)
        result = cmd_service.execute_command(
            f'obsidian unique content="{MEDIUM}"'
        )
        assert "[error]" not in result
        assert len(orig_calls) >= 3
        # First retry chunk is unique
        assert orig_calls[1][1] == "unique"
        # Subsequent chunks are append targeting the created file
        for call in orig_calls[2:]:
            assert call[1] == "append"
            assert "inline" in call

    def test_long_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian unique content="{LONG}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# base:create
# ---------------------------------------------------------------------------

class TestBaseCreateChunking:
    def test_short_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian base:create file="tasks.base" content="{SHORT}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1

    def test_medium_chunks(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)

        orig_calls = []

        def fake_run(argv, timeout=30):
            orig_calls.append(list(argv))
            content_len = 0
            for arg in argv:
                if arg.startswith("content="):
                    content_len = len(arg) - len("content=")
                    break
            if 1000 <= content_len <= 1800:
                raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)
            # base:create returns the created file path
            if argv[1] == "base:create":
                return subprocess.CompletedProcess(
                    args=argv, returncode=0,
                    stdout="Created Notes/new-item.md\n", stderr="",
                )
            return subprocess.CompletedProcess(
                args=argv, returncode=0,
                stdout="OK\n", stderr="",
            )

        monkeypatch.setattr(cmd_service, "_run_obsidian", fake_run)
        result = cmd_service.execute_command(
            f'obsidian base:create file="tasks.base" content="{MEDIUM}"'
        )
        assert "[error]" not in result
        assert len(orig_calls) >= 3
        # First retry chunk is base:create
        assert orig_calls[1][1] == "base:create"
        # Subsequent chunks are append (file append, not base:append)
        for call in orig_calls[2:]:
            assert call[1] == "append"
            assert "inline" in call

    def test_long_no_chunking(self, tmp_config, monkeypatch):
        calls = _make_timeout_mock(monkeypatch)
        result = cmd_service.execute_command(
            f'obsidian base:create file="tasks.base" content="{LONG}"'
        )
        assert "[error]" not in result
        assert len(calls) == 1


# ---------------------------------------------------------------------------
# Helpers unit tests
# ---------------------------------------------------------------------------

class TestParseObsidianArgs:
    def test_basic(self):
        argv = ["obsidian", "create", "path=test.md", "content=hello", "overwrite"]
        cmd, params, flags = cmd_service._parse_obsidian_args(argv)
        assert cmd == "create"
        assert params == {"path": "test.md", "content": "hello"}
        assert flags == {"overwrite"}

    def test_empty(self):
        cmd, params, flags = cmd_service._parse_obsidian_args(["obsidian"])
        assert cmd is None
        assert params == {}
        assert flags == set()


class TestSplitContent:
    def test_short_no_split(self):
        assert cmd_service._split_content("hello", 800) == ["hello"]

    def test_splits_at_newline(self):
        content = "a" * 700 + "\n" + "b" * 700
        chunks = cmd_service._split_content(content, 800)
        assert len(chunks) == 2
        assert chunks[0] == "a" * 700 + "\n"
        assert chunks[1] == "b" * 700

    def test_splits_at_limit_without_newline(self):
        content = "x" * 2000
        chunks = cmd_service._split_content(content, 800)
        assert len(chunks) == 3
        assert "".join(chunks) == content


class TestBuildCommand:
    def test_roundtrip(self):
        cmd = cmd_service._build_command(
            "obsidian", "create",
            {"path": "test.md", "content": "hello world"},
            {"overwrite"},
        )
        assert 'path="test.md"' in cmd
        assert 'content="hello world"' in cmd
        assert "overwrite" in cmd
        assert cmd.startswith("obsidian create")
