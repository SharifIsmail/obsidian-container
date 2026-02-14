#!/usr/bin/env bash
set -e

echo "[cmd-setup] Starting command service setup..."

# --- Write command service ---
cat > /usr/local/bin/obsidian-cmd-service.py << 'SERVICEEOF'
#!/usr/bin/env python3
"""HTTPS Command API for Obsidian vault.

Token file format (tokens.md):
  permanent:<token>        — always valid
  <unix_timestamp>:<token> — valid if now - timestamp < SESSION_TIMEOUT
  <token>                  — unused, valid on first use

Allowed commands file (allowed-commands.md):
  One command name per line. Falls back to {"obsidian"} if missing.

POST / — execute commands from JSON body {"commands": [...]}
GET /  — health check / token validation
"""

import http.server
import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time

TOKEN_FILE = "/config/cmd-service/tokens.md"
ALLOWED_COMMANDS_FILE = "/config/cmd-service/allowed-commands.md"
SESSION_TIMEOUT = 600  # 10 minutes
DEFAULT_ALLOWED = {"obsidian"}

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

    try:
        result = _run_obsidian(argv)
        # Filter Electron noise from stdout and stderr
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
    except subprocess.TimeoutExpired:
        return "[error] Command timed out after 30s\n"
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

    def log_message(self, format, *args):
        sys.stderr.write("[cmd-service] %s - %s\n" % (self.client_address[0], format % args))


def main():
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 9999), CommandHandler)
    print("[cmd-service] Listening on 0.0.0.0:9999", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
SERVICEEOF
chmod +x /usr/local/bin/obsidian-cmd-service.py
echo "[cmd-setup] Command service written."

# --- Create s6 service directory ---
mkdir -p /run/service/svc-cmd
cat > /run/service/svc-cmd/run << 'S6EOF'
#!/usr/bin/execlineb -P
/usr/bin/python3 /usr/local/bin/obsidian-cmd-service.py
S6EOF
chmod +x /run/service/svc-cmd/run
cat > /run/service/svc-cmd/type << 'S6EOF'
longrun
S6EOF

echo "[cmd-setup] s6 service directory created."
echo "[cmd-setup] Setup complete!"
