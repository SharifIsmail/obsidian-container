"""Shared fixtures for cmd_service tests.

Unit mode (default): in-process ThreadingHTTPServer on ephemeral port.
E2E mode (@pytest.mark.e2e): connects to a running container via env vars.
"""

import http.server
import os
import sys
import threading
import urllib.request

import pytest

# Make cmd_service importable from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cmd_service

# ---------------------------------------------------------------------------
# Unit-mode fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def tmp_config(tmp_path, monkeypatch):
    """Create temp config dir with seed files and monkeypatch module globals."""
    token_file = tmp_path / "tokens.md"
    token_file.write_text("permanent:test-token\n")

    allowed_file = tmp_path / "allowed-commands.md"
    allowed_file.write_text("obsidian\n")

    vault_path_file = tmp_path / "vault-path.md"
    vault_path_file.write_text("")  # empty → default

    monkeypatch.setattr(cmd_service, "TOKEN_FILE", str(token_file))
    monkeypatch.setattr(cmd_service, "ALLOWED_COMMANDS_FILE", str(allowed_file))
    monkeypatch.setattr(cmd_service, "VAULT_PATH_FILE", str(vault_path_file))
    monkeypatch.setattr(cmd_service, "OBSIDIAN_CONFIG", str(tmp_path / "obsidian.json"))

    return {
        "token_file": token_file,
        "allowed_file": allowed_file,
        "vault_path_file": vault_path_file,
        "config_dir": tmp_path,
    }


@pytest.fixture()
def vault_dir(tmp_path, monkeypatch, tmp_config):
    """Temp vault directory. Monkeypatches os.chown to no-op."""
    vault = tmp_path / "vault"
    vault.mkdir()
    tmp_config["vault_path_file"].write_text(str(vault) + "\n")
    monkeypatch.setattr(os, "chown", lambda *a, **kw: None)
    return vault


class FakeRunResult:
    """Controllable subprocess result with call capture."""
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.captured_calls = []


@pytest.fixture()
def mock_run_obsidian(monkeypatch):
    """Replace _run_obsidian with a controllable fake.

    Returns a FakeRunResult holder; set .stdout/.stderr to control output.
    Access .captured_calls for list of argv received by the mock.
    """
    result = FakeRunResult()

    def fake_run(argv, timeout=30):
        result.captured_calls.append(argv)
        return result

    monkeypatch.setattr(cmd_service, "_run_obsidian", fake_run)
    return result


@pytest.fixture()
def http_client(tmp_config, vault_dir, mock_run_obsidian):
    """Start a real ThreadingHTTPServer on an ephemeral port.

    Returns a helper object with .get(), .post(), .put() methods.
    """
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), cmd_service.CommandHandler)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class Client:
        base_url = f"http://{host}:{port}"
        token = "test-token"

        def request(self, method, path="/", body=None, headers=None, token=None):
            url = self.base_url + path
            data = body.encode() if isinstance(body, str) else body
            req = urllib.request.Request(url, data=data, method=method)
            if token is False:
                pass  # no auth header
            elif token is not None:
                req.add_header("Authorization", f"Bearer {token}")
            else:
                req.add_header("Authorization", f"Bearer {self.token}")
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            try:
                resp = urllib.request.urlopen(req)
                return resp.status, resp.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        def get(self, path="/", **kw):
            return self.request("GET", path, **kw)

        def post(self, path="/", body=None, **kw):
            return self.request("POST", path, body=body, **kw)

        def put(self, path="/", body=None, **kw):
            return self.request("PUT", path, body=body, **kw)

    client = Client()
    yield client
    server.shutdown()


# ---------------------------------------------------------------------------
# E2E-mode fixtures
# ---------------------------------------------------------------------------

def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: end-to-end tests against running container")


@pytest.fixture()
def e2e_client():
    """Client for e2e tests. Skips if env vars are not set."""
    url = os.environ.get("CMD_SERVICE_URL")
    token = os.environ.get("CMD_SERVICE_TOKEN")
    if not url or not token:
        pytest.skip("CMD_SERVICE_URL and CMD_SERVICE_TOKEN not set")

    class E2EClient:
        base_url = url.rstrip("/")

        def request(self, method, path="/", body=None, headers=None):
            full_url = self.base_url + path
            data = body.encode() if isinstance(body, str) else body
            req = urllib.request.Request(full_url, data=data, method=method)
            req.add_header("Authorization", f"Bearer {token}")
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            try:
                resp = urllib.request.urlopen(req)
                return resp.status, resp.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        def get(self, path="/", **kw):
            return self.request("GET", path, **kw)

        def post(self, path="/", body=None, **kw):
            return self.request("POST", path, body=body, **kw)

        def put(self, path="/", body=None, **kw):
            return self.request("PUT", path, body=body, **kw)

    return E2EClient()
