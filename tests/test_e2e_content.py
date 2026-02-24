"""E2E tests for content-bearing CLI commands.

Tests all 7 content-bearing commands × 3 content lengths against a running
Obsidian container, verifying that content is delivered intact at sizes that
previously triggered the Electron IPC bug (~1060-1700 chars).

Matrix: 7 commands × 3 lengths = 21 tests
  - short (500 chars): below old danger zone
  - medium (1200 chars): inside old danger zone
  - long (2500 chars): above old danger zone

Requires CMD_SERVICE_URL and CMD_SERVICE_TOKEN env vars (auto-skips without).
"""

import json
import uuid

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_content(length, prefix="line"):
    """Produce verifiable content with numbered lines, close to `length` chars."""
    lines = []
    total = 0
    i = 0
    while total < length:
        line = f"{prefix}-{i:04d} " + "x" * 40 + "\n"
        if total + len(line) > length:
            remaining = length - total
            if remaining > 0:
                lines.append(line[:remaining])
            break
        lines.append(line)
        total += len(line)
        i += 1
    return "".join(lines)


def _make_test_path(command, length):
    """Generate a unique vault path under _e2e_test/ to avoid collisions."""
    uid = uuid.uuid4().hex[:8]
    safe_cmd = command.replace(":", "-")
    return f"_e2e_test/{safe_cmd}-{length}-{uid}.md"


def _escape(value):
    """Escape backslashes and double-quotes for embedding in CLI command strings."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _cmd(client, command_str):
    """POST a single command and return (status, response_text)."""
    body = json.dumps({"commands": [command_str]})
    status, data = client.post("/", body=body)
    return status, data.decode()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def cleanup(e2e_client):
    """Collect file paths during a test, delete them via obsidian delete after."""
    paths = []

    class Cleanup:
        def add(self, path):
            paths.append(path)

    c = Cleanup()
    yield c

    for path in paths:
        _cmd(e2e_client, f'obsidian delete file="{_escape(path)}"')


# ---------------------------------------------------------------------------
# Content lengths
# ---------------------------------------------------------------------------

SHORT = 500
MEDIUM = 1200
LONG = 2500

LENGTHS = [
    pytest.param(SHORT, id="short-500"),
    pytest.param(MEDIUM, id="medium-1200"),
    pytest.param(LONG, id="long-2500"),
]


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestCreateE2E:
    @pytest.mark.parametrize("length", LENGTHS)
    def test_create(self, e2e_client, cleanup, length):
        path = _make_test_path("create", length)
        cleanup.add(path)
        content = _generate_content(length, prefix="create")

        status, resp = _cmd(
            e2e_client,
            f'obsidian create path="{_escape(path)}" content="{_escape(content)}" overwrite',
        )
        assert status == 200, f"HTTP {status}: {resp}"
        assert "[error]" not in resp, resp

        # Read back and verify
        status, resp = _cmd(e2e_client, f'obsidian read file="{_escape(path)}"')
        assert status == 200, f"Read HTTP {status}: {resp}"
        assert content in resp


# ---------------------------------------------------------------------------
# append
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestAppendE2E:
    @pytest.mark.parametrize("length", LENGTHS)
    def test_append(self, e2e_client, cleanup, length):
        path = _make_test_path("append", length)
        cleanup.add(path)
        preamble = "PREAMBLE\n"
        content = _generate_content(length, prefix="append")

        # Create prerequisite file
        status, resp = _cmd(
            e2e_client,
            f'obsidian create path="{_escape(path)}" content="{_escape(preamble)}" overwrite',
        )
        assert status == 200 and "[error]" not in resp, resp

        # Append
        status, resp = _cmd(
            e2e_client,
            f'obsidian append path="{_escape(path)}" content="{_escape(content)}"',
        )
        assert status == 200, f"HTTP {status}: {resp}"
        assert "[error]" not in resp, resp

        # Read back and verify both parts present
        status, resp = _cmd(e2e_client, f'obsidian read file="{_escape(path)}"')
        assert status == 200, f"Read HTTP {status}: {resp}"
        assert preamble.strip() in resp
        assert content in resp


# ---------------------------------------------------------------------------
# prepend
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestPrependE2E:
    @pytest.mark.parametrize("length", LENGTHS)
    def test_prepend(self, e2e_client, cleanup, length):
        path = _make_test_path("prepend", length)
        cleanup.add(path)
        trailer = "TRAILER\n"
        content = _generate_content(length, prefix="prepend")

        # Create prerequisite file
        status, resp = _cmd(
            e2e_client,
            f'obsidian create path="{_escape(path)}" content="{_escape(trailer)}" overwrite',
        )
        assert status == 200 and "[error]" not in resp, resp

        # Prepend
        status, resp = _cmd(
            e2e_client,
            f'obsidian prepend path="{_escape(path)}" content="{_escape(content)}"',
        )
        assert status == 200, f"HTTP {status}: {resp}"
        assert "[error]" not in resp, resp

        # Read back and verify both parts present
        status, resp = _cmd(e2e_client, f'obsidian read file="{_escape(path)}"')
        assert status == 200, f"Read HTTP {status}: {resp}"
        assert trailer.strip() in resp
        assert content in resp


# ---------------------------------------------------------------------------
# unique
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestUniqueE2E:
    @pytest.mark.parametrize("length", LENGTHS)
    def test_unique(self, e2e_client, cleanup, length):
        content = _generate_content(length, prefix="unique")

        status, resp = _cmd(
            e2e_client,
            f'obsidian unique content="{_escape(content)}"',
        )
        assert status == 200, f"HTTP {status}: {resp}"
        assert "[error]" not in resp, resp

        # Parse created path from output.
        # Output may be "Created 202601011200.md", "Created: path.md",
        # or just the filename "2026-02-24T11-12.md".
        created_path = None
        for line in resp.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("Created"):
                created_path = line.split("Created", 1)[1].strip().lstrip(":").strip()
            else:
                # Bare filename output
                created_path = line
            if created_path:
                break
        assert created_path, f"Could not parse created path from: {resp}"
        cleanup.add(created_path)

        # Read back and verify
        status, resp = _cmd(e2e_client, f'obsidian read file="{_escape(created_path)}"')
        assert status == 200, f"Read HTTP {status}: {resp}"
        assert content in resp


# ---------------------------------------------------------------------------
# daily:append
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestDailyAppendE2E:
    @pytest.mark.parametrize("length", LENGTHS)
    def test_daily_append(self, e2e_client, length):
        content = _generate_content(length, prefix="dailyap")

        status, resp = _cmd(
            e2e_client,
            f'obsidian daily:append content="{_escape(content)}"',
        )
        assert status == 200, f"HTTP {status}: {resp}"
        assert "[error]" not in resp, resp


# ---------------------------------------------------------------------------
# daily:prepend
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestDailyPrependE2E:
    @pytest.mark.parametrize("length", LENGTHS)
    def test_daily_prepend(self, e2e_client, length):
        content = _generate_content(length, prefix="dailypr")

        status, resp = _cmd(
            e2e_client,
            f'obsidian daily:prepend content="{_escape(content)}"',
        )
        assert status == 200, f"HTTP {status}: {resp}"
        assert "[error]" not in resp, resp


# ---------------------------------------------------------------------------
# base:create
# ---------------------------------------------------------------------------

@pytest.mark.e2e
class TestBaseCreateE2E:
    @pytest.mark.parametrize("length", LENGTHS)
    def test_base_create(self, e2e_client, cleanup, length):
        content = _generate_content(length, prefix="basecr")

        # Create a .base file as setup via PUT
        uid = uuid.uuid4().hex[:8]
        base_name = f"_e2e_test/test-{uid}.base"
        base_body = "---\nname: E2E Base\n---\n"
        put_status, put_resp = e2e_client.put(
            f"/vault/{base_name}",
            body=base_body,
        )
        assert put_status == 200, f"PUT base file failed: {put_resp.decode()}"
        cleanup.add(base_name)

        # Run base:create
        status, resp = _cmd(
            e2e_client,
            f'obsidian base:create file="{_escape(base_name)}" content="{_escape(content)}"',
        )
        assert status == 200, f"HTTP {status}: {resp}"
        assert "[error]" not in resp, resp

        # Parse created path from output
        created_path = None
        for line in resp.strip().splitlines():
            line = line.strip()
            if "Created" in line:
                # Output may be "Created Notes/Item.md" or "Created: Notes/Item.md"
                after = line.split("Created", 1)[1].strip().lstrip(":").strip().rstrip(".")
                if after:
                    created_path = after
                    break
        if created_path:
            cleanup.add(created_path)
            # Read back and verify
            status, resp = _cmd(e2e_client, f'obsidian read file="{_escape(created_path)}"')
            assert status == 200, f"Read HTTP {status}: {resp}"
            assert content in resp
