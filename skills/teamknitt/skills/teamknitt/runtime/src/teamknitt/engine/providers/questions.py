"""The bounded text-only question/answer contract shared by decision adapters."""
from __future__ import annotations
import math
from collections.abc import Mapping
from typing import Any
from .http import ProviderError


def _probability(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and 0 <= value <= 1


def validate_question(question: Mapping) -> dict:
    if not isinstance(question,Mapping):
        raise ProviderError("invalid_question","Question must be an object with type and instructions fields.")
    kind = question.get("type")
    allowed = {"type", "instructions", "criteria"}
    if set(question) - allowed or kind not in {"noul", "choice", "score"}:
        raise ProviderError("invalid_question", "Unsupported question field or type; spell instructions exactly.")
    if not isinstance(question.get("instructions"), str) or not question["instructions"].strip():
        raise ProviderError("invalid_question", "A nonempty instructions field is required.")
    criteria = question.get("criteria")
    if kind == "noul":
        if criteria is not None:
            raise ProviderError("invalid_question", "noul questions do not use criteria.")
    elif kind == "choice":
        if not isinstance(criteria, dict) or len(criteria) < 2 or not all(
            isinstance(k, str) and k and isinstance(v, str) and v for k, v in criteria.items()
        ):
            raise ProviderError("invalid_question", "choice criteria must name at least two options.")
    elif not isinstance(criteria, list) or len(criteria) < 2 or not all(isinstance(v, str) and v for v in criteria):
        raise ProviderError("invalid_question", "score criteria must be an ordered list.")
    return dict(question)


def validate_answer(question: Mapping, answer: Any) -> dict:
    if not isinstance(answer, dict):
        raise ProviderError("invalid_response", "Decision provider returned an invalid answer object.")
    kind = question["type"]
    if "type" in answer and answer["type"] != kind:
        raise ProviderError("invalid_response", "Answer type does not match the question.")
    if kind == "noul":
        if not _probability(answer.get("noul")):
            raise ProviderError("invalid_response", "Invalid yes-probability in Decision provider response.")
        return answer
    probabilities = answer.get("probabilities")
    if isinstance(probabilities, dict):
        if kind == "choice" and set(probabilities) != set(question["criteria"]):
            raise ProviderError("invalid_response", "Decision provider returned unexpected option IDs.")
        if kind == "score" and set(probabilities) != {str(i) for i in range(len(question["criteria"]))}:
            raise ProviderError("invalid_response", "Score probabilities need zero-based level IDs.")
        values = list(probabilities.values())
    elif kind == "score" and isinstance(probabilities, list):
        values = probabilities
    else:
        raise ProviderError("invalid_response", "Decision provider returned invalid probabilities.")
    if len(values) != len(question["criteria"]) or not all(_probability(p) for p in values) or not math.isclose(sum(values), 1, abs_tol=0.01):
        raise ProviderError("invalid_response", "Decision provider probabilities are not a valid distribution.")
    if not _probability(answer.get("confidence")):
        raise ProviderError("invalid_response", "Invalid Decision provider confidence.")
    if kind == "choice" and answer.get("choice") not in question["criteria"]:
        raise ProviderError("invalid_response", "Decision provider chose an unknown option.")
    if kind == "score":
        score = answer.get("score")
        if isinstance(score, bool) or not isinstance(score, (float, int)) or not math.isfinite(score) or not 0 <= score <= len(values)-1:
            raise ProviderError("invalid_response", "Invalid Decision provider score.")
    return answer
