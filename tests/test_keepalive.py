"""Tests for keepalive operational contract."""
import unittest
from unittest.mock import patch, MagicMock
import urllib.error


class TestKeepalive(unittest.TestCase):
    def test_ping_returns_true_on_200(self):
        import scripts.keepalive as ka
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.status = 200
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = ka.ping("TestAPI", "http://test/health")
        self.assertTrue(result)

    def test_ping_returns_false_on_url_error(self):
        import scripts.keepalive as ka
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            result = ka.ping("TestAPI", "http://test/health")
        self.assertFalse(result)

    def test_env_var_overrides_endpoints(self):
        import json, os, importlib
        custom = [{"name": "TestAPI", "url": "http://custom/health"}]
        with patch.dict(os.environ, {"KEEPALIVE_ENDPOINTS": json.dumps(custom)}):
            import scripts.keepalive as ka
            endpoints = ka._load_endpoints()
        self.assertEqual(endpoints[0][0], "TestAPI")

    def test_default_endpoints_loaded_when_no_env(self):
        import os, scripts.keepalive as ka
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KEEPALIVE_ENDPOINTS", None)
            endpoints = ka._load_endpoints()
        self.assertEqual(len(endpoints), 3)

    def test_interval_from_env(self):
        import os, importlib
        with patch.dict(os.environ, {"KEEPALIVE_INTERVAL": "60"}):
            import importlib
            import scripts.keepalive as ka
            importlib.reload(ka)
            self.assertEqual(ka.INTERVAL, 60)


if __name__ == "__main__":
    unittest.main()
