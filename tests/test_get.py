"""Tests for GET / endpoint."""


class TestGetEndpoint:
    def test_valid_auth(self, http_client):
        status, body = http_client.get()
        assert status == 200
        assert body == b"OK\n"

    def test_invalid_token(self, http_client):
        status, body = http_client.get(token="wrong-token")
        assert status == 401
        assert b"Invalid token" in body

    def test_missing_header(self, http_client):
        status, body = http_client.request("GET", "/", token=False,
                                           headers={})
        assert status == 401
        assert b"Missing or invalid Authorization" in body

    def test_empty_token(self, http_client):
        status, body = http_client.get(token="")
        assert status == 401

    def test_malformed_header(self, http_client):
        status, body = http_client.request("GET", "/", token=False,
                                           headers={"Authorization": "Token abc"})
        assert status == 401
        assert b"Missing or invalid Authorization" in body
