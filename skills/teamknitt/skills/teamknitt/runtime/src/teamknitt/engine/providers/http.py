"""Bounded authenticated JSON transport shared by explicit provider adapters."""
from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
import json
import math
import ipaddress
import time
from urllib.parse import urlsplit
import urllib.error
import urllib.request
from uuid import uuid4


class ProviderError(RuntimeError):
    def __init__(self, kind, message, *, http_status=None):
        super().__init__(message)
        self.kind, self.http_status = kind, http_status


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_base_url(value):
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise ProviderError("configuration", "Provider base URL must be a string.")
    try:
        parts = urlsplit(value)
        parts.port  # Validate an explicitly supplied port before any request is reserved.
    except ValueError:
        raise ProviderError("configuration", "Provider base URL has an invalid host or port.") from None
    try:
        loopback = parts.hostname == "localhost" or ipaddress.ip_address(parts.hostname or "").is_loopback
    except ValueError:
        loopback = False
    if (parts.scheme not in {"https", "http"} or parts.scheme == "http" and not loopback
            or not parts.hostname or parts.username or parts.password
            or parts.query or parts.fragment):
        raise ProviderError("configuration", "Use HTTPS, or HTTP on loopback only, without credentials, query or fragment.")
    return value.rstrip("/")


def validate_endpoint(value):
    if (not isinstance(value, str) or not value.startswith("/") or value.startswith("//")
            or any(c in value for c in ("?", "#", "\\", ":")) or any(c.isspace() for c in value)
            or ".." in value.split("/")):
        raise ProviderError("configuration", "Endpoint must be an absolute API path without query, fragment or traversal.")
    return value


class JSONClient:
    def __init__(self, api_key, *, base_url, provider_id, timeout=90, max_parallel=3,
                 on_event=None, reserve=None, transport=None, shared_semaphore=None,
                 max_request_bytes=16 * 1024 * 1024):
        self.base_url = validate_base_url(base_url)
        if api_key is not None and (not isinstance(api_key, str) or not api_key.strip()):
            raise ProviderError("missing_key", "The selected provider needs a private API key.")
        if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout) or timeout <= 0
                or isinstance(max_parallel, bool) or not isinstance(max_parallel, int) or max_parallel < 1):
            raise ProviderError("configuration", "Provider time and concurrency limits must be positive.")
        self._key, self.provider_id, self.timeout = api_key, provider_id, timeout
        if isinstance(max_request_bytes, bool) or not isinstance(max_request_bytes, int) or max_request_bytes < 1:
            raise ProviderError("configuration", "Request byte limit must be a positive integer.")
        self.max_request_bytes = max_request_bytes
        self._semaphore = shared_semaphore or asyncio.Semaphore(max_parallel)
        self._provider_semaphore = asyncio.Semaphore(max_parallel) if shared_semaphore is not None else self._semaphore
        self._event, self._reserve = on_event or (lambda event: None), reserve or (lambda: None)
        self._transport = transport or self._http

    def _emit(self, event):
        def clean(value):
            if isinstance(value, str):
                return value.replace(self._key, "[REDACTED]") if self._key else value
            if isinstance(value, dict):
                return {clean(k): clean(v) for k, v in value.items()}
            if isinstance(value, (list, tuple)):
                return [clean(v) for v in value]
            return value
        self._event(clean(event))

    def _http(self, method, path, body):
        data = None if body is None else json.dumps(body, allow_nan=False).encode()
        headers = {"Content-Type": "application/json"}
        if self._key:
            headers["Authorization"] = "Bearer " + self._key
        request = urllib.request.Request(
            self.base_url + path, data=data, method=method,
            headers=headers)
        try:
            with urllib.request.build_opener(_NoRedirect).open(request, timeout=self.timeout) as response:
                raw = response.read(16 * 1024 * 1024 + 1)
            if len(raw) > 16 * 1024 * 1024:
                raise ProviderError("invalid_response", "Provider response exceeds the local limit.")
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError()
            json.dumps(result, allow_nan=False)
            return result
        except urllib.error.HTTPError as error:
            kinds = {400: "invalid_request", 401: "authentication", 403: "access_or_credit",
                     404: "unknown_model_or_path", 413: "request_limit", 422: "invalid_request",
                     429: "rate_limit", 503: "busy", 529: "busy"}
            raise ProviderError(kinds.get(error.code, "http_error"),
                                self.provider_id + " returned HTTP " + str(error.code),
                                http_status=error.code) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise ProviderError("transport_uncertain", "Request failed or timed out; execution/billing may be unknown. No automatic retry.") from None
        except (ValueError, UnicodeError):
            raise ProviderError("invalid_response", "Provider returned invalid JSON.") from None

    async def request(self, method, path, body=None):
        validate_endpoint(path)
        if body is not None:
            try:
                encoded = json.dumps(body, allow_nan=False).encode()
            except (TypeError, ValueError):
                raise ProviderError("invalid_question", "Request must contain finite JSON.") from None
            if len(encoded) > self.max_request_bytes:
                raise ProviderError("request_limit", "Request exceeds the local byte limit.")
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(self._provider_semaphore)
            if self._provider_semaphore is not self._semaphore:
                await stack.enter_async_context(self._semaphore)
            if method == "POST":
                self._reserve()
            started, request_id = time.monotonic(), uuid4().hex
            metadata = {"request_id": request_id, "provider": self.provider_id,
                        "path": path, "model": (body or {}).get("model")}
            self._emit({"kind": "provider_request", **metadata, "request": body})
            try:
                result = await asyncio.to_thread(self._transport, method, path, body)
                if not isinstance(result, dict):
                    raise ProviderError("invalid_response", "Provider response must be an object.")
                try:
                    json.dumps(result, allow_nan=False)
                except (TypeError, ValueError):
                    raise ProviderError("invalid_response", "Provider response must contain finite JSON.") from None
                self._emit({"kind": "provider_response", **metadata,
                             "elapsed_seconds": time.monotonic() - started, "response": result})
                return result
            except ProviderError as error:
                self._emit({"kind": "provider_error", **metadata, "error_kind": error.kind,
                             "http_status": error.http_status,
                             "elapsed_seconds": time.monotonic() - started})
                raise
