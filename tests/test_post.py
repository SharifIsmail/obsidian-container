"""Tests for POST / endpoint."""

import json


class TestPostEndpoint:
    def test_valid_command(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "result line\n"
        body = json.dumps({"commands": ["obsidian list"]})
        status, resp = http_client.post(body=body)
        assert status == 200
        assert b"result line" in resp

    def test_invalid_json(self, http_client):
        status, resp = http_client.post(body="not json{{{")
        assert status == 400
        assert b"Invalid JSON" in resp

    def test_missing_body(self, http_client):
        status, resp = http_client.post(body=None)
        assert status == 400

    def test_non_allowed_command(self, http_client, tmp_config):
        tmp_config["allowed_file"].write_text("obsidian\n")
        body = json.dumps({"commands": ["rm -rf /"]})
        status, resp = http_client.post(body=body)
        assert status == 200
        assert b"not allowed" in resp

    def test_empty_commands_array(self, http_client):
        body = json.dumps({"commands": []})
        status, resp = http_client.post(body=body)
        assert status == 400

    def test_multiple_commands(self, http_client, mock_run_obsidian):
        mock_run_obsidian.stdout = "ok\n"
        body = json.dumps({"commands": ["obsidian list", "obsidian read"]})
        status, resp = http_client.post(body=body)
        assert status == 200
