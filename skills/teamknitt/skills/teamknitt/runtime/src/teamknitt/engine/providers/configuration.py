"""Validate public provider settings without opening a connection or reading a key."""
import math
import re
from urllib.parse import urlsplit
from .chat import validate_request_options
from .http import ProviderError, validate_base_url, validate_endpoint


def generation_settings(value):
    required = {"base_url", "model", "api_key_env", "env_file", "timeout_seconds",
                "max_output_tokens", "max_parallel_requests"}
    optional = {"adapter", "endpoint", "models_endpoint", "max_output_field", "request_options"}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - optional:
        raise ProviderError("configuration", "Provider settings have missing or unknown fields; see docs/PROVIDERS.md.")
    result = {"adapter": "chat_completions", "endpoint": "/chat/completions", "models_endpoint": None,
              "max_output_field": "max_tokens", **value}
    if result["adapter"] != "chat_completions":
        raise ProviderError("configuration", "Generation currently requires the chat_completions protocol.")
    for name in ("model", "env_file"):
        if not isinstance(result[name], str) or not result[name].strip():
            raise ProviderError("configuration", name + " must be a nonempty string.")
    key_name = result["api_key_env"]
    if key_name is not None and (not isinstance(key_name, str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", key_name)):
        raise ProviderError("configuration", "api_key_env must name an environment variable, or be null for explicit unauthenticated use.")
    result["base_url"] = validate_base_url(result["base_url"])
    validate_endpoint(result["endpoint"])
    if result["models_endpoint"] is not None:
        validate_endpoint(result["models_endpoint"])
    timeout = result["timeout_seconds"]
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ProviderError("configuration", "Provider timeout must be positive and finite.")
    for name in ("max_output_tokens", "max_parallel_requests"):
        if isinstance(result[name], bool) or not isinstance(result[name], int) or result[name] < 1:
            raise ProviderError("configuration", "Provider count limits must be positive integers.")
    if result["max_output_field"] not in {"max_tokens", "max_completion_tokens"}:
        raise ProviderError("configuration", "Unsupported output-limit field.")
    result["request_options"] = validate_request_options(result.get("request_options"))
    return result


def require_configured(settings):
    host = urlsplit(settings["base_url"]).hostname or ""
    if host.endswith(".invalid") or settings["model"].upper().startswith("YOUR_") or settings["model"].lower() == "unconfigured":
        raise ProviderError("configuration", "Set your provider base_url and model before an explicit live check or run.")
