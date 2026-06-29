"""YOUR tests for the observability layer.

Per the lab guide, write at least 3 substantive tests, each with at least
1 assertion.
"""

import json
import logging
import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.observability import requests_total

client = TestClient(app)


def test_request_id_header_present():
    response = client.get("/healthz")
    
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) >= 8


def test_metrics_counter_increments():
    path = "/healthz"
    status_code = "200"
    
    try:
        before_value = requests_total.labels(path=path, status=status_code)._value.get()
    except Exception:
        before_value = 0

    client.get(path)

    after_value = requests_total.labels(path=path, status=status_code)._value.get()
    
    assert after_value == before_value + 1


def test_structured_log_matches_header(caplog):
    with caplog.at_level(logging.INFO, logger="m11.api"):
        response = client.get("/healthz")
        
        header_request_id = response.headers.get("X-Request-ID")
        
        assert len(caplog.records) >= 1
        
        log_line = caplog.records[-1].message
        log_json = json.loads(log_line)
        
        assert "request_id" in log_json
        assert log_json["request_id"] == header_request_id