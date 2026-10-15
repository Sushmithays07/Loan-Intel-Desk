"""Frontend client behaviour when the backend misbehaves. Uses mocks; no server needed."""
import os
import unittest
from unittest import mock

import requests

import api_client


def fake_response(status=200, json_data=None, bad_json=False):
    r = mock.Mock()
    r.status_code = status
    if bad_json:
        r.json.side_effect = ValueError("no json")
    else:
        r.json.return_value = json_data
    return r


class ApiClientTests(unittest.TestCase):
    def test_backend_unreachable(self):
        with mock.patch("requests.request", side_effect=requests.exceptions.ConnectionError()):
            with self.assertRaises(api_client.ApiError) as cm:
                api_client.get_history()
        self.assertEqual(cm.exception.kind, "connection")
        self.assertIn("uvicorn", cm.exception.message)

    def test_real_connection_refused_on_unused_port(self):
        with mock.patch.dict(os.environ, {"API_BASE_URL": "http://127.0.0.1:9"}):
            with self.assertRaises(api_client.ApiError) as cm:
                api_client.get_health()
        self.assertEqual(cm.exception.kind, "connection")

    def test_timeout(self):
        with mock.patch("requests.request", side_effect=requests.exceptions.Timeout()):
            with self.assertRaises(api_client.ApiError) as cm:
                api_client.predict({})
        self.assertEqual(cm.exception.kind, "timeout")

    def test_validation_error_is_readable(self):
        detail = [{"loc": ["body", "credit_score"], "msg": "Input should be less than or equal to 900"}]
        with mock.patch("requests.request", return_value=fake_response(422, {"detail": detail})):
            with self.assertRaises(api_client.ApiError) as cm:
                api_client.predict({})
        self.assertEqual(cm.exception.kind, "validation")
        self.assertIn("credit_score", cm.exception.message)

    def test_server_error_503_message_passed_through(self):
        with mock.patch("requests.request", return_value=fake_response(503, {"detail": "Database unavailable"})):
            with self.assertRaises(api_client.ApiError) as cm:
                api_client.get_analytics()
        self.assertEqual(cm.exception.kind, "server")
        self.assertIn("Database unavailable", cm.exception.message)

    def test_invalid_json_body(self):
        with mock.patch("requests.request", return_value=fake_response(200, bad_json=True)):
            with self.assertRaises(api_client.ApiError) as cm:
                api_client.get_model_info()
        self.assertEqual(cm.exception.kind, "invalid_response")

    def test_success_and_query_params(self):
        with mock.patch("requests.request", return_value=fake_response(200, {"items": []})) as req:
            self.assertEqual(api_client.get_history(page=2, status="approved", search="LID"), {"items": []})
        self.assertEqual(req.call_args.kwargs["params"],
                         {"page": 2, "page_size": 10, "status": "approved", "search": "LID"})
        self.assertIn("timeout", req.call_args.kwargs)


if __name__ == "__main__":
    unittest.main()
