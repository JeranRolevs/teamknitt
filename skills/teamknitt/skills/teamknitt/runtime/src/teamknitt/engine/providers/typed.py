"""Configurable typed JSON decision endpoints."""
from __future__ import annotations

import json
from collections.abc import Mapping
from ..contracts import DecisionResult, DecisionStatus
from .http import JSONClient, ProviderError, validate_endpoint
from .questions import validate_question, validate_answer


class TypedDecisionClient(JSONClient):
    def __init__(self, api_key, *, model, base_url,
                 provider_id="decision/specialist", endpoint="/assess", timeout=90,
                 max_parallel=3, **kwargs):
        super().__init__(api_key, base_url=base_url, provider_id=provider_id,
                         timeout=timeout, max_parallel=max_parallel, max_request_bytes=1024 * 1024, **kwargs)
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("configuration", "Specify a decision model name.")
        self.model, self.endpoint = model, validate_endpoint(endpoint)

    async def assess_text(self, state, questions):
        if (not isinstance(state, str) or not state.strip() or not isinstance(questions, Mapping)
                or not questions or not all(isinstance(k, str) and k for k in questions)):
            raise ProviderError("invalid_question", "Use nonempty state and named typed questions.")
        checked = {key: validate_question(question) for key, question in questions.items()}
        body = {"model": self.model, "state": state, "questions": checked}
        if len(json.dumps(body, allow_nan=False).encode()) > 1024 * 1024:
            raise ProviderError("request_limit", "Decision request exceeds the local 1 MiB limit.")
        result = await self.request("POST", self.endpoint, body)
        answers = result.get("answers")
        if (not isinstance(answers, dict) or set(answers) != set(checked)
                or not isinstance(result.get("model"), str) or not result["model"].strip()):
            raise ProviderError("invalid_response", "Decision response needs matching answer IDs and a model identifier.")
        for key, question in checked.items():
            validate_answer(question, answers[key])
        return result


class TypedDecisionBackend:
    def __init__(self, client, resolve_context):
        self.client, self.resolve_context = client, resolve_context

    def supports(self, spec):
        try:
            validate_question(spec)
            return True
        except ProviderError:
            return False

    async def assess(self, request):
        identity = self.client.provider_id
        if not set(request.context_refs) <= set(request.caller.permitted_refs):
            return DecisionResult(request.request_id, DecisionStatus.INVALID, None, identity,
                                  request.context_refs, {"error_kind": "context_not_permitted"})
        if not self.supports(request.answer_space):
            return DecisionResult(request.request_id, DecisionStatus.UNSUPPORTED, None, identity,
                                  request.context_refs, {})
        try:
            response = await self.client.assess_text(self.resolve_context(request),
                                                     {request.spec_id: request.answer_space})
            return DecisionResult(request.request_id, DecisionStatus.ANSWERED,
                                  response["answers"][request.spec_id], identity, request.context_refs,
                                  response.get("usage", {}),
                                  probability_origin="model_reported_not_empirically_calibrated",
                                  model_id=response["model"])
        except ProviderError as error:
            status = DecisionStatus.INVALID if error.kind == "invalid_response" else DecisionStatus.UNAVAILABLE
            return DecisionResult(request.request_id, status, None, identity, request.context_refs,
                                  {"error_kind": error.kind, "http_status": error.http_status})
