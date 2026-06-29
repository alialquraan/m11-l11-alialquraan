"""Observability layer for the M10 backend.

This module is where you (the learner) declare the three Prometheus metric
families and implement the three ASGI middleware classes that the autograder
exercises through the FastAPI app.
"""

import json
import time
import uuid
import logging
from contextvars import ContextVar
from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger("m11.api")
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# ==========================================
# 1️⃣ Metric Declarations (Module Scope)
# ==========================================
requests_total = Counter(
    "requests_total",
    "Total volume of HTTP requests",
    ["path", "status"]
)

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "HTTP request latency in seconds",
    ["path"]
)

inflight_requests = Gauge(
    "inflight_requests",
    "Number of HTTP requests currently in-flight"
)


# ==========================================
# 2️⃣ RequestIdMiddleware
# ==========================================
class RequestIdMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        req_id = uuid.uuid4().hex
        token = request_id_var.set(req_id)

        async def send_with_request_id(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", req_id.encode("utf-8")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_var.reset(token)


# ==========================================
# 3️⃣ StructuredLoggingMiddleware
# ==========================================
class StructuredLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.perf_counter()
        path = scope.get("path", "")
        status_code = [500] 

        async def send_with_logging(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            
            log_payload = {
                "request_id": request_id_var.get(),
                "path": path,
                "status": status_code[0],
                "latency_ms": latency_ms,
                "ts": time.time(),
                "level": "INFO"
            }
            logger.info(json.dumps(log_payload))


# ==========================================
# 4️⃣ MetricsMiddleware
# ==========================================
class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        inflight_requests.inc()
        
        start_time = time.perf_counter()
        path = scope.get("path", "")
        status_code = [500]

        async def send_with_metrics(message):
            if message["type"] == "http.response.start":
                status_code[0] = message.get("status", 200)
            await send(message)

        try:
            await self.app(scope, receive, send_with_metrics)
        finally:
            elapsed = time.perf_counter() - start_time
            
            requests_total.labels(path=path, status=str(status_code[0])).inc()
            request_latency_seconds.labels(path=path).observe(elapsed)
            
            inflight_requests.dec()