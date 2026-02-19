"""Tests for PUT /vault/ endpoint."""

import json
import os

import cmd_service


class TestPutVault:
    def test_successful_write(self, http_client, vault_dir):
        status, body = http_client.put("/vault/test.md", body="hello world")
        assert status == 200
        assert b"OK test.md" in body
        assert (vault_dir / "test.md").read_bytes() == b"hello world"

    def test_traversal_dotdot(self, http_client, vault_dir):
        status, body = http_client.put("/vault/../etc/passwd", body="hack")
        assert status == 400
        assert b"Invalid path" in body

    def test_empty_path(self, http_client, vault_dir):
        status, body = http_client.put("/vault/", body="data")
        assert status == 400
        assert b"Invalid path" in body

    def test_parent_dir_creation(self, http_client, vault_dir):
        status, body = http_client.put("/vault/sub/dir/note.md", body="nested")
        assert status == 200
        assert (vault_dir / "sub" / "dir" / "note.md").read_bytes() == b"nested"

    def test_write_error_500(self, http_client, vault_dir, monkeypatch):
        def fail_write(path, content):
            raise PermissionError("denied")

        import cmd_service as cs
        monkeypatch.setattr(cs, "_write_file_as_abc", fail_write)
        status, body = http_client.put("/vault/fail.md", body="data")
        assert status == 500
        assert b"Write failed" in body

    def test_wrong_path_404(self, http_client):
        status, body = http_client.put("/other/path", body="data")
        assert status == 404

    def test_symlink_traversal(self, http_client, vault_dir, tmp_path):
        target = tmp_path / "outside"
        target.mkdir()
        link = vault_dir / "escape"
        link.symlink_to(target)
        status, body = http_client.put("/vault/escape/evil.md", body="hack")
        assert status == 400
        assert b"Path traversal denied" in body

    def test_put_lands_in_vault_root(self, http_client, vault_dir):
        """PUT /vault/Attachments/photo.png writes inside the vault, not elsewhere."""
        status, body = http_client.put("/vault/Attachments/photo.png", body=b"\x89PNG")
        assert status == 200
        written = vault_dir / "Attachments" / "photo.png"
        assert written.exists()
        assert written.read_bytes() == b"\x89PNG"

    def test_no_vault_configured_returns_503(self, http_client, tmp_config):
        """With no vault-path.md content and no obsidian.json, PUT returns 503."""
        # vault-path.md is empty by default in tmp_config; obsidian.json doesn't exist
        # We need a fresh http_client that doesn't use the vault_dir fixture
        # (vault_dir writes a path into vault-path.md). Overwrite it back to empty.
        tmp_config["vault_path_file"].write_text("")
        status, body = http_client.put("/vault/test.md", body="data")
        assert status == 503
        assert b"No vault configured" in body

    def test_vault_path_from_obsidian_json(self, http_client, tmp_config, tmp_path, monkeypatch):
        """When vault-path.md is empty, falls back to obsidian.json."""
        # Clear vault-path.md so priority 1 yields nothing
        tmp_config["vault_path_file"].write_text("")

        # Create a vault directory and mock obsidian.json
        obs_vault = tmp_path / "notes"
        obs_vault.mkdir()
        obsidian_json = tmp_path / "obsidian.json"
        obsidian_json.write_text(json.dumps({
            "vaults": {
                "abc123": {"path": str(obs_vault), "ts": 1700000000, "open": True}
            }
        }))
        monkeypatch.setattr(cmd_service, "OBSIDIAN_CONFIG", str(obsidian_json))
        monkeypatch.setattr(os, "chown", lambda *a, **kw: None)

        status, body = http_client.put("/vault/hello.md", body="from obsidian.json")
        assert status == 200
        assert (obs_vault / "hello.md").read_bytes() == b"from obsidian.json"
