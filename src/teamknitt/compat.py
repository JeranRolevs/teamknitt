"""Read legacy workspace/record names without importing the upstream runtime.

Saved bindings are verified in their original form before display normalization. No
history, credentials, models, statistical choices or budgets are rewritten on read.
"""
from copy import deepcopy
from .engine.config import ConfigurationError

PLAN_ALIASES = {
    "labtune_plan": "engine_plan",
    "labtune_variant": "engine_variant",
    "labtune_configuration_sha256": "engine_configuration_sha256",
}
PERSPECTIVE_ALIASES = {"distributed_cognition": "distributed_problem_solving"}


def normalize_team_config(value):
    c = deepcopy(value)
    if not isinstance(c, dict):
        return c  # The schema supplies the structural error.
    if "labtune" in c:
        if "engine" in c:
            raise ConfigurationError("Conflicting legacy and current engine settings; choose one explicitly.")
        c["engine"] = c.pop("labtune")
    perspectives = c.get("cognition", {}).get("perspectives") if isinstance(c.get("cognition"), dict) else None
    if isinstance(perspectives, list):
        c["cognition"]["perspectives"] = [PERSPECTIVE_ALIASES.get(p, p) if isinstance(p, str) else p for p in perspectives]
    return c


def plan_for_display(value):
    p = deepcopy(value)
    for old, new in PLAN_ALIASES.items():
        if old in p:
            if new in p:
                raise ConfigurationError("Saved record contains conflicting engine identities.")
            p[new] = p.pop(old)
    p["configuration"] = normalize_team_config(p["configuration"])
    return p


def original_engine_plan(plan):
    if "engine_plan" in plan and "labtune_plan" in plan:
        raise ConfigurationError("Saved record contains conflicting engine plans.")
    return plan.get("engine_plan", plan.get("labtune_plan"))
