"""Configurable chat-completions generation and decision clients."""
from __future__ import annotations

from collections.abc import Mapping
import json
from .http import JSONClient, ProviderError, validate_endpoint
from .questions import validate_question, validate_answer


RESERVED_OPTIONS = {"model", "messages", "stream", "max_tokens", "max_completion_tokens",
                    "state", "questions", "api_key", "authorization", "headers", "base_url"}


def validate_request_options(value):
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ProviderError("configuration", "request_options must be a JSON mapping.")
    def check(item):
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str) or key.lower() in {"api_key", "authorization", "password", "secret", "access_token"}:
                    raise ProviderError("configuration", "Credentials belong in the configured environment variable.")
                check(child)
        elif isinstance(item, list):
            for child in item:
                check(child)
    if RESERVED_OPTIONS & {k.lower() for k in value}:
        raise ProviderError("configuration", "request_options cannot override identity, messages, streaming, or output bounds.")
    check(value)
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (ValueError, TypeError):
        raise ProviderError("configuration", "request_options must contain finite JSON.") from None


class ChatCompletionsClient(JSONClient):
    def __init__(self, api_key, *, model, base_url, endpoint="/chat/completions",
                 models_endpoint=None, provider_id="generation", timeout=90, max_tokens=1024,
                 max_output_field="max_tokens", max_parallel=3, request_options=None, **kwargs):
        super().__init__(api_key, base_url=base_url, provider_id=provider_id, timeout=timeout,
                         max_parallel=max_parallel, **kwargs)
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("configuration", "Specify a generation model identifier.")
        if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens < 1:
            raise ProviderError("configuration", "Output token limit must be a positive integer.")
        if max_output_field not in {"max_tokens", "max_completion_tokens"}:
            raise ProviderError("configuration", "Unsupported output-limit field.")
        self.model, self.endpoint = model, validate_endpoint(endpoint)
        self.models_endpoint = validate_endpoint(models_endpoint) if models_endpoint is not None else None
        self.max_tokens, self.max_output_field = max_tokens, max_output_field
        self.request_options = validate_request_options(request_options)

    async def models(self):
        if self.models_endpoint is None:
            raise ProviderError("configuration", "Set models_endpoint to explicitly enable model listing.")
        result = await self.request("GET", self.models_endpoint)
        data = result.get("data")
        if not isinstance(data, list):
            raise ProviderError("invalid_response", "Model listing needs a data array.")
        return [row["id"] for row in data if isinstance(row, dict) and isinstance(row.get("id"), str)]

    async def generate(self, messages, *, budget_ref):
        body = {**self.request_options, "model": self.model, "messages": list(messages),
                self.max_output_field: self.max_tokens, "stream": False}
        result = await self.request("POST", self.endpoint, body)
        choices = result.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderError("invalid_response", "Provider returned no chat choice.")
        if choices[0].get("finish_reason") == "length":
            raise ProviderError("output_limit", "Text output reached its configured limit.")
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str) or not message["content"].strip():
            raise ProviderError("invalid_response", "Provider returned no text content.")
        return {"content": message["content"], "model": result.get("model", self.model),
                "usage": result.get("usage", {}), "request_id": result.get("id"),
                "finish_reason": choices[0].get("finish_reason"), "budget_ref": budget_ref}


class ChatDecisionClient(ChatCompletionsClient):
    async def assess_text(self, state, questions):
        if not isinstance(state, str) or not state.strip() or not isinstance(questions, Mapping) or not questions or not all(isinstance(k,str) and k for k in questions):
            raise ProviderError("invalid_question", "Use nonempty state and named typed questions.")
        checked = {key: validate_question(question) for key, question in questions.items()}
        reply = await self.generate([
            {"role": "system", "content": 'Answer the supplied bounded questions as JSON only: {"answers": {question_id: answer}}. '
                'For noul use {"noul": probability_yes}; for choice use {"choice": id, "confidence": probability, '
                '"probabilities": {id: probability}}; for score use {"score": expected_zero_based_position, '
                '"confidence": probability, "probabilities": [probability,...]}. Probabilities must sum to one. Do not call tools.'},
            {"role": "user", "content": json.dumps({"state": state, "questions": checked}, allow_nan=False)}
        ], budget_ref="decision")
        try:
            answers = json.loads(reply["content"])["answers"]
            if not isinstance(answers, dict) or set(answers) != set(checked):
                raise ValueError()
            for key, question in checked.items():
                validate_answer(question, answers[key])
        except (KeyError, ValueError, TypeError):
            raise ProviderError("invalid_response", "Decision response needs matching, valid typed answers.") from None
        return {"answers": answers, "model": reply["model"], "usage": reply["usage"]}
