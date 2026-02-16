"""Tests for token parsing, writing, and authentication."""

import time

import cmd_service


class TestParseTokenFile:
    def test_permanent_token(self, tmp_config):
        tmp_config["token_file"].write_text("permanent:my-secret\n")
        entries = cmd_service.parse_token_file()
        assert len(entries) == 1
        assert entries[0]["kind"] == "permanent"
        assert entries[0]["token"] == "my-secret"

    def test_timed_token(self, tmp_config):
        ts = int(time.time())
        tmp_config["token_file"].write_text(f"{ts}:timed-tok\n")
        entries = cmd_service.parse_token_file()
        assert len(entries) == 1
        assert entries[0]["kind"] == "timed"
        assert entries[0]["token"] == "timed-tok"
        assert entries[0]["timestamp"] == ts

    def test_unused_token(self, tmp_config):
        tmp_config["token_file"].write_text("fresh-token\n")
        entries = cmd_service.parse_token_file()
        assert len(entries) == 1
        assert entries[0]["kind"] == "unused"
        assert entries[0]["token"] == "fresh-token"

    def test_comments_and_blanks_skipped(self, tmp_config):
        tmp_config["token_file"].write_text("# comment\n\npermanent:tok1\n")
        entries = cmd_service.parse_token_file()
        assert len(entries) == 1

    def test_missing_file(self, tmp_config):
        tmp_config["token_file"].unlink()
        entries = cmd_service.parse_token_file()
        assert entries == []

    def test_empty_file(self, tmp_config):
        tmp_config["token_file"].write_text("")
        entries = cmd_service.parse_token_file()
        assert entries == []

    def test_multiple_tokens(self, tmp_config):
        ts = int(time.time())
        tmp_config["token_file"].write_text(
            f"permanent:p1\n{ts}:t1\nunused1\n"
        )
        entries = cmd_service.parse_token_file()
        assert len(entries) == 3
        assert [e["kind"] for e in entries] == ["permanent", "timed", "unused"]


class TestWriteTokenFile:
    def test_roundtrip(self, tmp_config):
        ts = int(time.time())
        entries = [
            {"kind": "permanent", "token": "p1", "timestamp": None},
            {"kind": "timed", "token": "t1", "timestamp": ts},
            {"kind": "unused", "token": "u1", "timestamp": None},
        ]
        cmd_service.write_token_file(entries)
        content = tmp_config["token_file"].read_text()
        assert "permanent:p1\n" in content
        assert f"{ts}:t1\n" in content
        assert "u1\n" in content


class TestAuthenticate:
    def test_permanent_token_valid(self, tmp_config):
        tmp_config["token_file"].write_text("permanent:valid-tok\n")
        assert cmd_service.authenticate("valid-tok") is True

    def test_permanent_token_invalid(self, tmp_config):
        tmp_config["token_file"].write_text("permanent:valid-tok\n")
        assert cmd_service.authenticate("wrong-tok") is False

    def test_unused_token_becomes_timed(self, tmp_config):
        tmp_config["token_file"].write_text("fresh-tok\n")
        assert cmd_service.authenticate("fresh-tok") is True
        entries = cmd_service.parse_token_file()
        assert entries[0]["kind"] == "timed"
        assert entries[0]["timestamp"] is not None

    def test_timed_token_refreshed(self, tmp_config):
        old_ts = int(time.time()) - 100
        tmp_config["token_file"].write_text(f"{old_ts}:my-tok\n")
        assert cmd_service.authenticate("my-tok") is True
        entries = cmd_service.parse_token_file()
        assert entries[0]["timestamp"] > old_ts

    def test_expired_token_removed(self, tmp_config):
        expired_ts = int(time.time()) - cmd_service.SESSION_TIMEOUT - 1
        tmp_config["token_file"].write_text(f"{expired_ts}:old-tok\n")
        assert cmd_service.authenticate("old-tok") is False
        entries = cmd_service.parse_token_file()
        assert entries == []

    def test_empty_token(self, tmp_config):
        tmp_config["token_file"].write_text("permanent:valid\n")
        assert cmd_service.authenticate("") is False

    def test_missing_file(self, tmp_config):
        tmp_config["token_file"].unlink()
        assert cmd_service.authenticate("anything") is False

    def test_expired_cleaned_while_matching_another(self, tmp_config):
        expired_ts = int(time.time()) - cmd_service.SESSION_TIMEOUT - 1
        tmp_config["token_file"].write_text(
            f"{expired_ts}:old\npermanent:good\n"
        )
        assert cmd_service.authenticate("good") is True
        entries = cmd_service.parse_token_file()
        assert len(entries) == 1
        assert entries[0]["token"] == "good"
