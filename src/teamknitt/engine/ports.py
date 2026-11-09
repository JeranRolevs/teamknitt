"""Replaceable components for later implementation; no implicit fake execution."""

from __future__ import annotations

from typing import Any, Protocol, Sequence

from .contracts import (
    CallerContext, DecisionRequest, DecisionResult, EpisodeResult,
    ConfigurationChange, EvaluationReceipt, JSON, SharingView,
)


class LLMClient(Protocol):
    async def generate(self, messages: Sequence[JSON], *, budget_ref: str) -> JSON: ...


class DecisionBackend(Protocol):
    def supports(self, spec: JSON) -> bool: ...
    async def assess(self, request: DecisionRequest) -> DecisionResult: ...


class AgentWorker(Protocol):
    async def run_episode(self, task: JSON, caller: CallerContext) -> EpisodeResult: ...


class ResourceScheduler(Protocol):
    def lease(self, task_id: str, requested: JSON, *, budget_ref: str) -> JSON: ...
    def reconcile(self, lease_id: str) -> JSON: ...


class DomainAdapter(Protocol):
    async def qualify(self, mission: JSON) -> JSON: ...
    async def evaluate(self, experiment: JSON, *, statistical_policy: JSON) -> EvaluationReceipt: ...


class CandidateRuntime(Protocol):
    async def execute(self, frozen_inputs: JSON, *, lease_ref: str) -> JSON: ...


class EvidenceStore(Protocol):
    def append(self, validated_record: JSON) -> str: ...
    def read(self, record_id: str, *, caller: CallerContext) -> JSON: ...


class PlaybookStore(Protocol):
    def propose_delta(self, delta: JSON, *, caller: CallerContext) -> str: ...
    def retrieve(self, query: JSON, *, caller: CallerContext) -> Sequence[JSON]: ...


class CommunicationPublisher(Protocol):
    def materialize(self, source_refs: Sequence[str], *, caller: CallerContext) -> SharingView: ...
    def record_read(self, view: SharingView, *, entries_read: Sequence[str]) -> str: ...


class ConfigurationControl(Protocol):
    """Apply a user's settings change and record its effective boundary; no ranking gate."""
    def apply_user_change(self, change: ConfigurationChange) -> str: ...


class AssetRegistry(Protocol):
    def register(self, asset: JSON, *, confirmation_refs: Sequence[str]) -> str: ...
    def schedule_recheck(self, asset_id: str, conditions: JSON) -> Any: ...
