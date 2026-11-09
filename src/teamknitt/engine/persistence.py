"""User-chosen, finite effort controls for the single-scientist design."""
from .config import ConfigurationError

PERSISTENCE_PASSES = {"low": 1, "medium": 3, "persistent": 6}
EFFORT_MODES = ("fixed_passes", "budget")
SEQUENCE_CONTEXTS = ("continue", "fresh_sequence")


def resolve_execution(config, design, roles, delegation):
    if design["governance"] != "single_scientist":
        return {"kind": "phase_graph"}
    if len(roles) != 1 or roles[0]["role"] != "prime":
        raise ConfigurationError("The single-scientist design requires exactly one prime scientist.")
    if delegation["max_depth"] or delegation["max_children_per_agent"]:
        raise ConfigurationError("The single-scientist design has no delegated children; use zero depth and child count.")
    controls = config["single_scientist"]
    if controls["effort_mode"] == "budget":
        if controls["persistence"] != "persistent":
            raise ConfigurationError("Budget-driven effort is an option for the persistent level.")
        if config["budget"]["max_llm_calls"] < controls["sequences"]:
            raise ConfigurationError("Each budget-driven sequence needs at least one request in the shared request budget.")
    passes = PERSISTENCE_PASSES[controls["persistence"]] if controls["effort_mode"] == "fixed_passes" else None
    return {"kind": "single_scientist", **controls, "passes_per_sequence": passes,
            "planned_passes": passes * controls["sequences"] if passes is not None else None,
            "budget_scope": "all_sequences", "confirmation_boundary": "after_all_sequences"}


def scientist_graph(actor, execution):
    nodes = [{"id": "qualify_domain", "kind": "qualification", "actors": ["system:domain"],
              "depends_on": [], "input_contract": "mission", "output_contract": "evaluation_receipt",
              "read_scope": "declared_qualification_inputs", "research_activity": "planned"}]
    for sequence in range(1, execution["sequences"] + 1):
        passes = execution["passes_per_sequence"] or 1
        for step in range(1, passes + 1):
            budget = execution["effort_mode"] == "budget"
            identity = f"sequence-{sequence}:budget:{actor}" if budget else f"sequence-{sequence}:pass-{step}:{actor}"
            nodes.append({"id": identity, "kind": "research_episode", "actors": [actor],
                          "depends_on": [nodes[-1]["id"]],
                          "input_contract": "mission" if len(nodes) == 1 or (step == 1 and execution["context_policy"] == "fresh_sequence") else "research_event",
                          "output_contract": "research_event", "read_scope": "own_team_and_permitted_snapshot",
                          "research_activity": "planned", "sequence": sequence, "pass": 0 if budget else step,
                          "label": "Work to allowance" if budget else "Investigate" if step == 1 else "Audit and refine"})
    return nodes


def pass_task(execution, sequence, step):
    descriptions = {
        "low": "Pursue one focused approach. Use permitted tools when needed; report your result and remaining uncertainty.",
        "medium": "Investigate, test and refine your approach. Audit earlier reasoning and address a concrete weakness or alternative.",
        "persistent": "Persist with the mission: investigate a concrete alternative after a dead end, test when possible, and critically revise earlier work."
    }
    return {"sequence": sequence, "sequences": execution["sequences"], "pass": step,
            "passes_per_sequence": execution["passes_per_sequence"], "persistence": execution["persistence"],
            "effort_mode": execution["effort_mode"], "context_policy": execution["context_policy"],
            "instructions": descriptions[execution["persistence"]] +
                " Return a final action to end this pass, not to certify the mission solved."
                " Preserve failures and evidence limits. All passes and sequences share the user's budgets."
                " Do not change lab settings or request protected confirmation results."}
