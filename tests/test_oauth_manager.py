import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from unittest.mock import patch, MagicMock
from core.oauth_manager import OAuthManager

@pytest.fixture
def oauth(tmp_path):
    return OAuthManager(
        client_id="test_client",
        client_secret="test_secret",
        db_path=str(tmp_path / "oauth.db")
    )

def test_generate_pkce_pair(oauth):
    verifier, challenge = oauth.generate_pkce_pair()
    assert len(verifier) > 40
    assert len(challenge) > 40
    assert verifier != challenge

def test_build_authorization_url(oauth):
    url = oauth.build_authorization_url(redirect_uri="http://localhost:3000/callback")
    assert "response_type=code" in url
    assert "code_challenge" in url
    assert "code_challenge_method=S256" in url
    assert "test_client" in url

def test_store_and_retrieve_token(oauth):
    oauth.store_token(
        access_token="access_abc",
        refresh_token="refresh_xyz",
        expires_in=3600
    )
    token = oauth.get_valid_token()
    assert token == "access_abc"

def test_log_token_usage(oauth):
    oauth.store_token("access_abc", "refresh_xyz", 3600)
    oauth.log_usage(
        access_token="access_abc",
        endpoint="/v1/messages",
        model="claude-opus-4-7",
        input_tokens=500,
        output_tokens=1200
    )
    stats = oauth.get_cost_stats()
    assert stats["total_requests"] == 1
    assert stats["total_cost_usd"] > 0

def test_token_not_stored_returns_none(oauth):
    assert oauth.get_valid_token() is None
