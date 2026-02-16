"""Tests for execute_command function."""

import subprocess

import cmd_service


class TestExecuteCommand:
    def test_allowed_command(self, tmp_config, mock_run_obsidian):
        mock_run_obsidian.stdout = "hello\n"
        result = cmd_service.execute_command("obsidian list")
        assert "hello" in result

    def test_disallowed_command(self, tmp_config):
        result = cmd_service.execute_command("rm -rf /")
        assert "not allowed" in result

    def test_empty_command(self, tmp_config):
        result = cmd_service.execute_command("")
        assert "Empty command" in result

    def test_invalid_syntax(self, tmp_config):
        result = cmd_service.execute_command("obsidian 'unclosed")
        assert "Invalid command syntax" in result

    def test_timeout(self, tmp_config, monkeypatch):
        def fake_run(argv, timeout=30):
            raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout)
        monkeypatch.setattr(cmd_service, "_run_obsidian", fake_run)
        result = cmd_service.execute_command("obsidian list")
        assert "timed out" in result

    def test_electron_noise_filtered(self, tmp_config, mock_run_obsidian):
        mock_run_obsidian.stdout = "Loading the app package\nreal output\n"
        result = cmd_service.execute_command("obsidian list")
        assert "Loading" not in result
        assert "real output" in result
