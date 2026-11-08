"""Explicit, user-selected communication topology. No organizational optimizer."""
from labtune.config import ConfigurationError

TOPOLOGIES = {
    "fully_connected": "Every member can send permitted information to every other member.",
    "hub_and_spoke": "Member 1 is the communication hub; spokes exchange through it.",
    "ring": "Each member connects to its two neighbors in a bidirectional ring.",
    "hierarchical": "A bidirectional binary-tree communication layout; it does not grant decision authority.",
    "custom": "Only the explicitly declared directed links exist; reverse links are not implied.",
}


def members(count):
    if type(count) is not int or not 1 <= count <= 16:
        raise ConfigurationError("Choose 1–16 team members; a single member has no peer links.")
    return [f"member.{i}" for i in range(1, count + 1)]


def links(team):
    ids = members(team["members"])
    kind = team["topology"]
    if kind not in TOPOLOGIES:
        raise ConfigurationError("Unknown team topology.")
    if kind == "custom":
        pairs = [(x["source"], x["target"]) for x in team["links"]]
        if len(set(pairs)) != len(pairs) or any(a not in ids or b not in ids or a == b for a, b in pairs):
            raise ConfigurationError("Custom links must be unique directed pairs of distinct configured member IDs.")
        return pairs
    if team["links"]:
        raise ConfigurationError("Explicit links belong only to a custom topology; do not combine two topology authorities.")
    if kind == "fully_connected":
        return [(a, b) for a in ids for b in ids if a != b]
    pairs = set()
    def connect(a, b):
        if a != b:
            pairs.update(((a, b), (b, a)))
    if kind == "hub_and_spoke":
        for b in ids[1:]:
            connect(ids[0], b)
    elif kind == "ring":
        for i, a in enumerate(ids):
            connect(a, ids[(i + 1) % len(ids)])
    else:
        for i in range(1, len(ids)):
            connect(ids[(i - 1) // 2], ids[i])
    order = {a: i for i, a in enumerate(ids)}
    return sorted(pairs, key=lambda p: (order[p[0]], order[p[1]]))
