"""Explicit, user-selected communication topology. No organizational optimizer."""
from importlib.resources import files
import json
import math

from teamknitt.engine.config import ConfigurationError

# Labels and diagram captions originate in diagrams/specs.py, not a UI-only list.
TOPOLOGY_CATALOG = json.loads(files("teamknitt.resources").joinpath("topology-catalog.json").read_text())
TOPOLOGIES = {kind: row["description"] for kind, row in TOPOLOGY_CATALOG.items()}


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

    def connect(a, b, *, directed=False):
        if a != b:
            pairs.add((a, b))
            if not directed:
                pairs.add((b, a))

    if kind in {"hub_and_spoke", "wheel", "broadcast", "gather"}:
        for b in ids[1:]:
            a, target = (b, ids[0]) if kind == "gather" else (ids[0], b)
            connect(a, target, directed=kind in {"broadcast", "gather"})
        if kind == "wheel":
            spokes = ids[1:]
            for i, a in enumerate(spokes):
                connect(a, spokes[(i + 1) % len(spokes)])
    elif kind in {"ring", "directed_ring"}:
        for i, a in enumerate(ids):
            connect(a, ids[(i + 1) % len(ids)], directed=kind == "directed_ring")
    elif kind in {"chain", "directed_chain"}:
        for a, b in zip(ids, ids[1:]):
            connect(a, b, directed=kind == "directed_chain")
    elif kind == "hierarchical":
        for i in range(1, len(ids)):
            connect(ids[(i - 1) // 2], ids[i])
    elif kind == "grid":
        cols = math.ceil(math.sqrt(len(ids)))
        for i, a in enumerate(ids):
            if i % cols:
                connect(ids[i - 1], a)
            if i >= cols:
                connect(ids[i - cols], a)
    elif kind == "bipartite":
        split = (len(ids) + 1) // 2
        for a in ids[:split]:
            for b in ids[split:]:
                connect(a, b)
    elif kind == "clustered":
        pods = [ids[i:i + 3] for i in range(0, len(ids), 3)]
        for pod in pods:
            for i, a in enumerate(pod):
                for b in pod[i + 1:]:
                    connect(a, b)
        for a, b in zip(pods, pods[1:]):
            connect(a[0], b[0])
    else:
        raise ConfigurationError("Topology preset has no routing implementation.")
    order = {a: i for i, a in enumerate(ids)}
    return sorted(pairs, key=lambda p: (order[p[0]], order[p[1]]))
