"""Tests for get_allowed_commands and get_vault_path."""

import cmd_service


class TestGetAllowedCommands:
    def test_default_when_missing(self, tmp_config):
        tmp_config["allowed_file"].unlink()
        assert cmd_service.get_allowed_commands() == {"obsidian"}

    def test_default_when_empty(self, tmp_config):
        tmp_config["allowed_file"].write_text("")
        assert cmd_service.get_allowed_commands() == {"obsidian"}

    def test_default_when_comments_only(self, tmp_config):
        tmp_config["allowed_file"].write_text("# just a comment\n\n")
        assert cmd_service.get_allowed_commands() == {"obsidian"}

    def test_custom_commands(self, tmp_config):
        tmp_config["allowed_file"].write_text("obsidian\ncurl\nwget\n")
        assert cmd_service.get_allowed_commands() == {"obsidian", "curl", "wget"}

    def test_skips_comments(self, tmp_config):
        tmp_config["allowed_file"].write_text("# header\nobsidian\n# another\ncurl\n")
        assert cmd_service.get_allowed_commands() == {"obsidian", "curl"}

    def test_single_command(self, tmp_config):
        tmp_config["allowed_file"].write_text("mytool\n")
        assert cmd_service.get_allowed_commands() == {"mytool"}


class TestGetVaultPath:
    def test_default_when_empty(self, tmp_config):
        tmp_config["vault_path_file"].write_text("")
        assert cmd_service.get_vault_path() == "/config"

    def test_default_when_missing(self, tmp_config):
        tmp_config["vault_path_file"].unlink()
        assert cmd_service.get_vault_path() == "/config"

    def test_custom_path(self, tmp_config):
        tmp_config["vault_path_file"].write_text("/data/vault\n")
        assert cmd_service.get_vault_path() == "/data/vault"

    def test_skips_comments(self, tmp_config):
        tmp_config["vault_path_file"].write_text("# comment\n/my/vault\n")
        assert cmd_service.get_vault_path() == "/my/vault"
