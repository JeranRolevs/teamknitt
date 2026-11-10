"""Shared runtime boundaries. These types do not implement the runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

JSON = Mapping[str, Any]


class DecisionStatus(StrEnum):
    ANSWERED = "answered"
    ABSTAINED = "abstained"
    UNSUPPORTED = "unsupported"
    UNAVAILABLE = "unavailable"
    INVALID = "invalid"
    BUDGET_EXHAUSTED = "budget_exhausted"


class EvaluationStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    INCONCLUSIVE = "inconclusive"
    ENVIRONMENT_FAILURE = "environment_failure"
    CONTRACT_FAILURE = "contract_failure"


class StatisticalApproach(StrEnum):
    FREQUENTIST = "frequentist"


class StatisticalStatus(StrEnum):
    NOT_REQUIRED = "not_required"
    NOT_RUN = "not_run"
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class StatisticalAssessment:
    approach: StatisticalApproach
    status: StatisticalStatus
    protocol_ref: str | None
    result_refs: tuple[str, ...]
    reason: str | None


@dataclass(frozen=True)
class CallerContext:
    actor_id: str
    prime_id: str
    mission_id: str
    episode_id: str
    configuration_snapshot_id: str
    knowledge_snapshot_id: str
    permitted_refs: tuple[str, ...]
    budget_ref: str


@dataclass(frozen=True)
class DecisionRequest:
    request_id: str
    spec_id: str
    purpose: str
    context_refs: tuple[str, ...]
    caller: CallerContext
    answer_space: JSON


@dataclass(frozen=True)
class DecisionResult:
    request_id: str
    status: DecisionStatus
    answer: Any
    backend_id: str
    context_refs: tuple[str, ...]
    usage: JSON
    probability_origin: str | None = None
    fallback_refs: tuple[str, ...] = ()
    model_id: str | None = None


@dataclass(frozen=True)
class EpisodeResult:
    episode_id: str
    actor_id: str
    event_refs: tuple[str, ...]
    artifact_refs: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class EvaluationReceipt:
    evaluation_id: str
    experiment_id: str
    candidate_hash: str
    evaluator_hash: str
    status: EvaluationStatus
    metrics: JSON
    evidence_refs: tuple[str, ...]
    resource_use: JSON
    statistics: StatisticalAssessment


@dataclass(frozen=True)
class SharingView:
    snapshot_id: str
    recipient_id: str
    configuration_snapshot_id: str
    files: tuple[str, ...]
    source_refs: tuple[str, ...]
    content_hash: str


@dataclass(frozen=True)
class ConfigurationChange:
    change_id: str
    requested_by: str
    previous_snapshot_id: str
    new_snapshot_id: str
    effective_at: str
    exposure_refs: tuple[str, ...]
