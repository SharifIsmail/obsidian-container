#!/usr/bin/env python3
"""HTTPS Command API for Obsidian vault.

Token file format (tokens.md):
  permanent:<token>        — always valid
  <unix_timestamp>:<token> — valid if now - timestamp < SESSION_TIMEOUT
  <token>                  — unused, valid on first use

Allowed commands file (allowed-commands.md):
  One command name per line. Falls back to {"obsidian"} if missing.

POST /        — execute commands from JSON body {"commands": [...]}
GET /         — health check / token validation
PUT /vault/<path> — write a file to the vault
"""

import http.server
import json
import os
import pwd
import re
import shlex
import subprocess
import sys
import threading
import time
import urllib.parse

TOKEN_FILE = "/config/cmd-service/tokens.md"
ALLOWED_COMMANDS_FILE = "/config/cmd-service/allowed-commands.md"
VAULT_PATH_FILE = "/config/cmd-service/vault-path.md"
OBSIDIAN_CONFIG = "/config/.config/obsidian/obsidian.json"
SESSION_TIMEOUT = 600  # 10 minutes
DEFAULT_ALLOWED = {"obsidian"}

# Electron bug mitigation: additionalData is silently dropped for certain
# ProcessSingleton IPC message sizes (~1060-1700 chars of content).
# When a content-bearing CLI command times out, we retry with chunked content.
CONTENT_COMMANDS = {
    "create", "append", "prepend",
    "daily:append", "daily:prepend",
    "unique", "base:create",
}
CHUNK_SIZE = 800  # conservative limit per chunk (chars)
CLI_TIMEOUT = 5   # seconds — normal completion is <1s

try:
    _abc = pwd.getpwnam("abc")
    ABC_UID, ABC_GID = _abc.pw_uid, _abc.pw_gid
except KeyError:
    ABC_UID, ABC_GID = 1000, 1000

lock = threading.Lock()


def parse_token_file():
    """Parse token file. Returns list of dicts with keys:
    raw_line, token, kind ('permanent'|'timed'|'unused'), timestamp (or None)
    """
    entries = []
    if not os.path.isfile(TOKEN_FILE):
        return entries
    with open(TOKEN_FILE, "r") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("permanent:"):
                token = stripped[len("permanent:"):].strip()
                entries.append({"raw_line": line, "token": token,
                                "kind": "permanent", "timestamp": None})
            else:
                # Check for timestamp prefix: <digits>:<token>
                m = re.match(r"^(\d{10,}):(.+)$", stripped)
                if m:
                    entries.append({"raw_line": line, "token": m.group(2).strip(),
                                    "kind": "timed", "timestamp": int(m.group(1))})
                else:
                    entries.append({"raw_line": line, "token": stripped,
                                    "kind": "unused", "timestamp": None})
    return entries


def write_token_file(entries):
    """Rewrite the token file from entries."""
    with open(TOKEN_FILE, "w") as f:
        for e in entries:
            if e["kind"] == "permanent":
                f.write(f"permanent:{e['token']}\n")
            elif e["kind"] == "timed":
                f.write(f"{e['timestamp']}:{e['token']}\n")
            else:
                f.write(f"{e['token']}\n")


def authenticate(provided_token):
    """Validate token. Returns True if valid, False otherwise.

    Side effects: updates timestamp for timed/unused tokens, removes expired tokens.
    """
    now = int(time.time())

    with lock:
        entries = parse_token_file()
        changed = False
        matched = False

        # Clean up expired tokens and find match in one pass
        kept = []
        for e in entries:
            if e["kind"] == "timed" and now - e["timestamp"] >= SESSION_TIMEOUT:
                # Expired — drop it
                changed = True
                continue

            if not matched and e["token"] == provided_token:
                matched = True
                if e["kind"] == "unused":
                    # First use — stamp it
                    e["kind"] = "timed"
                    e["timestamp"] = now
                    changed = True
                elif e["kind"] == "timed":
                    # Refresh timestamp
                    e["timestamp"] = now
                    changed = True
                # permanent: no change needed

            kept.append(e)

        if changed:
            write_token_file(kept)

    return matched


def get_allowed_commands():
    """Read allowed command names from file, one per line."""
    if not os.path.isfile(ALLOWED_COMMANDS_FILE):
        return DEFAULT_ALLOWED
    allowed = set()
    with open(ALLOWED_COMMANDS_FILE, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                allowed.add(stripped)
    return allowed or DEFAULT_ALLOWED


def get_vault_path():
    """Read vault root from config file, Obsidian config, or return None."""
    # 1. Explicit config file
    if os.path.isfile(VAULT_PATH_FILE):
        with open(VAULT_PATH_FILE, "r") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    return stripped

    # 2. Auto-detect from Obsidian's own config
    if os.path.isfile(OBSIDIAN_CONFIG):
        try:
            with open(OBSIDIAN_CONFIG, "r") as f:
                data = json.load(f)
            for vault in data.get("vaults", {}).values():
                if vault.get("open"):
                    return vault["path"]
        except (json.JSONDecodeError, KeyError):
            pass

    # 3. No vault found
    return None


def _write_file_as_abc(full_path, content):
    """Write file, create parent dirs, chown to abc user."""
    parent = os.path.dirname(full_path)
    dirs_to_chown = []
    d = parent
    while not os.path.exists(d):
        dirs_to_chown.append(d)
        d = os.path.dirname(d)
    if dirs_to_chown:
        os.makedirs(parent, exist_ok=True)
        for new_dir in dirs_to_chown:
            os.chown(new_dir, ABC_UID, ABC_GID)
    with open(full_path, "wb") as f:
        f.write(content)
    os.chown(full_path, ABC_UID, ABC_GID)


OBS_ENV = {
    "DISPLAY": ":1",
    "HOME": "/config",
    "XDG_RUNTIME_DIR": "/config/.XDG",
    "PATH": "/config/.local/bin:/usr/local/bin:/usr/bin:/bin",
    "ELECTRON_DISABLE_SANDBOX": "1",
    "LANG": "en_US.UTF-8",
    "LANGUAGE": "en_US.UTF-8",
}


def _run_obsidian(argv, timeout=30):
    """Run obsidian command via s6-setuidgid abc."""
    return subprocess.run(
        ["s6-setuidgid", "abc"] + argv,
        env=OBS_ENV,
        capture_output=True,
        text=True,
        timeout=timeout,
    )



def _parse_obsidian_args(argv):
    """Parse obsidian CLI argv into (command, params, flags).

    After shlex.split, argv looks like:
      ['obsidian', 'create', 'path=Notes/test.md', 'content=hello', 'overwrite']
    Returns:
      ('create', {'path': 'Notes/test.md', 'content': 'hello'}, {'overwrite'})
    """
    command = argv[1] if len(argv) > 1 else None
    params = {}
    flags = set()
    for arg in argv[2:]:
        if "=" in arg:
            key, _, value = arg.partition("=")
            params[key] = value
        else:
            flags.add(arg)
    return command, params, flags


def _build_command(base_cmd, command, params, flags):
    """Rebuild a CLI command string from parsed components."""
    parts = [base_cmd, command]
    for key, value in params.items():
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        parts.append(f'{key}="{escaped}"')
    parts.extend(sorted(flags))
    return " ".join(parts)


def _split_content(content, chunk_size):
    """Split content into chunks, preferring newline boundaries."""
    if len(content) <= chunk_size:
        return [content]
    chunks = []
    while content:
        if len(content) <= chunk_size:
            chunks.append(content)
            break
        # Try to split at a newline within the chunk
        cut = content.rfind("\n", 0, chunk_size)
        if cut <= 0:
            cut = chunk_size
        else:
            cut += 1  # include the newline in this chunk
        chunks.append(content[:cut])
        content = content[cut:]
    return chunks


def _run_with_output(argv, timeout=30):
    """Run obsidian command and return filtered output string."""
    result = _run_obsidian(argv, timeout=timeout)

    def _filter(text):
        return "\n".join(
            l for l in text.splitlines()
            if not ("Loading" in l and "app package" in l)
        )

    output = _filter(result.stdout)
    if output and not output.endswith("\n"):
        output += "\n"
    if result.stderr:
        filtered_err = _filter(result.stderr)
        if filtered_err:
            output += filtered_err + "\n"
    return output


def _chunked_retry(base_cmd, command, params, flags):
    """Retry a content command by splitting content into chunks.

    Returns output string from all chunk executions combined.
    """
    content = params.get("content", "")
    chunks = _split_content(content, CHUNK_SIZE)
    file_param = params.get("path") or params.get("name") or params.get("file")

    # For prepend: reverse chunks so last chunk is prepended first.
    # Each prepend inserts after frontmatter, so reversed order reconstructs
    # the original content order.
    is_prepend = command in ("prepend", "daily:prepend")
    if is_prepend:
        chunks = list(reversed(chunks))

    # Determine the follow-up command for continuation chunks.
    # Prepend stays prepend (reversed order); everything else uses append.
    if is_prepend:
        followup_cmd = command  # keep prepending in reverse
    elif command in ("daily:append", "daily:prepend"):
        followup_cmd = "daily:append"
    else:
        followup_cmd = "append"

    outputs = []
    for i, chunk in enumerate(chunks):
        chunk_params = dict(params)
        chunk_params["content"] = chunk
        chunk_flags = set(flags)

        if i == 0:
            # First chunk: use original command with all original params/flags
            cmd = command
        else:
            # Continuation chunks: switch to follow-up command, add inline flag
            cmd = followup_cmd
            chunk_flags.add("inline")
            chunk_flags.discard("overwrite")
            chunk_flags.discard("template")
            chunk_flags.discard("open")
            chunk_flags.discard("newtab")
            # Remove template param for continuation
            chunk_params.pop("template", None)
            # For non-daily appends, ensure we target the right file
            if cmd == "append" and file_param:
                # Use file= for name-based, path= for path-based
                if "path" in params:
                    chunk_params["path"] = params["path"]
                elif "name" in params:
                    chunk_params["file"] = params["name"]
                elif "file" in params:
                    chunk_params["file"] = params["file"]
                # Remove keys not needed for append
                chunk_params.pop("name", None)

        cmd_str = _build_command(base_cmd, cmd, chunk_params, chunk_flags)
        argv = shlex.split(cmd_str)
        output = _run_with_output(argv, timeout=CLI_TIMEOUT)
        outputs.append(output)

        # If first chunk of a create/unique/base:create, try to extract file path
        # from output for subsequent appends
        if i == 0 and command in ("create", "unique", "base:create") and not file_param:
            # Try to parse created file path from output (e.g., "Created Notes/test.md")
            for line in output.splitlines():
                if line.startswith("Created ") or line.endswith(".md"):
                    candidate = line.replace("Created ", "").strip()
                    if candidate:
                        file_param = candidate
                        break

    return "".join(outputs)


def execute_command(cmd):
    """Execute a command as abc user with Obsidian environment."""
    try:
        argv = shlex.split(cmd)
    except ValueError as e:
        return f"[error] Invalid command syntax: {e}\n"

    if not argv:
        return "[error] Empty command\n"

    allowed = get_allowed_commands()
    if argv[0] not in allowed:
        return f"[error] Command '{argv[0]}' not allowed. Allowed: {', '.join(sorted(allowed))}\n"

    base_cmd = argv[0]
    command, params, flags = _parse_obsidian_args(argv)
    content = params.get("content", "")
    is_content_cmd = command in CONTENT_COMMANDS and content

    try:
        timeout = CLI_TIMEOUT if is_content_cmd else 30
        return _run_with_output(argv, timeout=timeout)
    except subprocess.TimeoutExpired:
        if is_content_cmd:
            try:
                return _chunked_retry(base_cmd, command, params, flags)
            except subprocess.TimeoutExpired:
                return f"[error] Command timed out after chunked retry\n"
            except Exception as e:
                return f"[error] CLI timed out and chunked retry failed: {e}\n"
        return f"[error] Command timed out after 30s\n"
    except Exception as e:
        return f"[error] {e}\n"


class CommandHandler(http.server.BaseHTTPRequestHandler):
    def _authenticate(self):
        auth_header = self.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            self.send_response(401)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Missing or invalid Authorization header.\n"
                             b"Expected: Authorization: Bearer <token>\n")
            return False

        provided_token = auth_header[len("Bearer "):].strip()
        if not provided_token:
            self.send_response(401)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Empty token.\n")
            return False

        if not authenticate(provided_token):
            self.send_response(401)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Invalid token.\n")
            return False

        return True

    def do_GET(self):
        if not self._authenticate():
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK\n")

    def do_POST(self):
        if not self._authenticate():
            return

        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b'Missing body. Expected: {"commands": [...]}\n')
            return

        try:
            body = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Invalid JSON.\n")
            return

        commands = body.get("commands", [])
        if not isinstance(commands, list) or not commands:
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b'Expected {"commands": ["cmd1", "cmd2", ...]}\n')
            return

        output_parts = []
        for cmd in commands:
            if not isinstance(cmd, str):
                continue
            output_parts.append(execute_command(cmd))

        result = "".join(output_parts)
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(result.encode())

    def do_PUT(self):
        if not self._authenticate():
            return

        if not self.path.startswith("/vault/"):
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found. PUT /vault/<path>\n")
            return

        rel_path = urllib.parse.unquote(self.path[len("/vault/"):])
        if not rel_path or "\x00" in rel_path or ".." in rel_path.split("/"):
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Invalid path.\n")
            return

        vault_path = get_vault_path()
        if not vault_path:
            self.send_response(503)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"No vault configured. Create a vault in Obsidian or set vault-path.md.\n")
            return
        vault_root = os.path.realpath(vault_path)
        full_path = os.path.realpath(os.path.join(vault_root, rel_path))
        if not full_path.startswith(vault_root + "/"):
            self.send_response(400)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Path traversal denied.\n")
            return

        content_length = int(self.headers.get("Content-Length", 0))
        content = self.rfile.read(content_length) if content_length else b""

        try:
            _write_file_as_abc(full_path, content)
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(f"Write failed: {e}\n".encode())
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(f"OK {rel_path}\n".encode())

    def log_message(self, format, *args):
        sys.stderr.write("[cmd-service] %s - %s\n" % (self.client_address[0], format % args))


def main():
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 9999), CommandHandler)
    print("[cmd-service] Listening on 0.0.0.0:9999", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
