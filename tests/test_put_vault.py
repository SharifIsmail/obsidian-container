"""Tests for PUT /vault/ endpoint."""

import os


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
