"""Configuration and adapter registry, independent of generation-model selection."""
from __future__ import annotations

import math
from pathlib import Path
import re
from .config import ConfigurationError
from .providers.http import ProviderError, validate_base_url, validate_endpoint
from .providers.typed import TypedDecisionClient
from .providers.chat import ChatDecisionClient, validate_request_options

ADAPTERS = {"typed": TypedDecisionClient, "chat_completions": ChatDecisionClient}


def validate_provider(value):
    required = {"adapter", "base_url", "model", "api_key_env", "env_file",
                "timeout_seconds", "max_parallel_requests"}
    optional = {"endpoint", "max_output_tokens", "max_output_field", "request_options"}
    if not isinstance(value, dict) or not required <= set(value) or set(value) - required - optional:
        raise ConfigurationError("A decision provider has missing or unknown fields.")
    result = dict(value, endpoint=value.get("endpoint", "/assess" if value.get("adapter") == "typed" else "/chat/completions"))
    if not isinstance(result["adapter"], str) or result["adapter"] not in ADAPTERS:
        raise ConfigurationError("Unknown decision adapter. Available: " + ", ".join(ADAPTERS))
    for field in ("model", "env_file"):
        if not isinstance(result[field], str) or not result[field].strip():
            raise ConfigurationError("Decision provider " + field + " must be a nonempty string.")
    if result["api_key_env"] is not None and (not isinstance(result["api_key_env"], str) or not re.fullmatch(r"[A-Z][A-Z0-9_]*", result["api_key_env"])):
        raise ConfigurationError("Decision credentials must name an environment variable.")
    try:
        result["base_url"] = validate_base_url(result["base_url"])
        validate_endpoint(result["endpoint"])
    except ProviderError as error:
        raise ConfigurationError(str(error)) from None
    limit = result["timeout_seconds"]
    count = result["max_parallel_requests"]
    if (isinstance(limit, bool) or not isinstance(limit, (int, float))
            or not math.isfinite(limit) or limit <= 0
            or isinstance(count, bool) or not isinstance(count, int) or count < 1):
        raise ConfigurationError("Decision provider limits must be positive finite values.")
    if result["adapter"] == "typed" and set(value) & {"max_output_tokens", "max_output_field", "request_options"}:
        raise ConfigurationError("Chat request options apply to chat_completions decision endpoints only.")
    if result["adapter"] == "chat_completions":
        result.setdefault("max_output_tokens", 2048)
        result.setdefault("max_output_field", "max_tokens")
        if isinstance(result["max_output_tokens"], bool) or not isinstance(result["max_output_tokens"], int) or result["max_output_tokens"] < 1:
            raise ConfigurationError("Decision output limit must be a positive integer.")
        if result["max_output_field"] not in {"max_tokens", "max_completion_tokens"}:
            raise ConfigurationError("Unsupported decision output-limit field.")
        try:
            result["request_options"] = validate_request_options(result.get("request_options"))
        except ProviderError as error:
            raise ConfigurationError(str(error)) from None
    return result


def validate_declarations(config, workspace):
    declared = config.get("decision_providers", {})
    if not isinstance(declared, dict):
        raise ConfigurationError("decision_providers must be a mapping.")
    for name, value in declared.items():
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]*", name):
            raise ConfigurationError("Use a lowercase, path-safe decision provider ID.")
        settings = validate_provider(value)
        if not (workspace / settings["env_file"]).resolve().is_relative_to(workspace.resolve()):
            raise ConfigurationError("Decision private env file must stay inside the workspace.")


def resolve_specialist(config, name):
    settings = config.get("decision_providers", {}).get(name)
    if settings is None:
        raise ConfigurationError("Declare the selected specialist under decision_providers before using it.")
    result = validate_provider(settings)
    result["provider_id"] = "decision/" + name
    return result


def decision_client_for(settings, key, **kwargs):
    options = {"model": settings["model"], "base_url": settings["base_url"],
               "provider_id": settings["provider_id"], "endpoint": settings["endpoint"],
               "timeout": settings["timeout_seconds"], "max_parallel": settings["max_parallel_requests"]}
    if settings["adapter"] == "chat_completions":
        options.update(max_tokens=settings["max_output_tokens"], max_output_field=settings["max_output_field"],
                       request_options=settings["request_options"])
    return ADAPTERS[settings["adapter"]](key, **options, **kwargs)
