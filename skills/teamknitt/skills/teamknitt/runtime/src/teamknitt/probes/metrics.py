"""Descriptive interaction traces, not inferred attractors, fractals or neural synchrony."""
from __future__ import annotations

from collections import Counter
import math
import statistics

from .scenarios import ACTS


def entropy(counts):
    total = sum(counts)
    return -sum((n / total) * math.log2(n / total) for n in counts if n) if total else None


def dynamics(episode, config):
    messages = [e for e in episode["events"] if e["kind"] == "message"]
    delivered = [e for e in messages if e["delivered"]]
    directed = {(e["source"], e["target"]) for e in delivered}
    series = []
    for snapshot in episode["rounds"]:
        round_ = snapshot["round"]
        sent = [e for e in messages if e["round"] == round_]
        received = [e for e in sent if e["delivered"]]
        counts = Counter(e["act"] for e in received)
        h = entropy(counts.values())
        series.append({**snapshot, "messages_sent": len(sent), "messages_delivered": len(received),
                       "messages_dropped": len(sent) - len(received),
                       "action_entropy_bits": h,
                       "normalized_action_entropy": h / math.log2(len(ACTS)) if h is not None else None,
                       "acts": dict(counts)})
    activity = [row["messages_delivered"] for row in series]
    mean_activity = statistics.mean(activity) if activity else 0
    variation = statistics.pstdev(activity) / mean_activity if mean_activity else None
    recoveries = []
    stability = config["dynamics"]["stable_rounds"]
    interventions = config["perturbations"] if episode["condition"] == "test" else []
    for p in interventions:
        first = p["at_round"]
        end = first + p["duration"] - 1
        seen = any(e["kind"] == "perturbation" and e["intervention"]["id"] == p["id"] for e in episode["events"])
        before = [s for s in series if s["round"] < first]
        established = len(before) >= stability and all(s["goal_ready"] for s in before[-stability:])
        after = [s for s in series if s["round"] >= end]
        found = None
        for i in range(len(after) - stability + 1):
            window = after[i:i + stability]
            if all(s["goal_ready"] for s in window) and window[-1]["round"] - window[0]["round"] == stability - 1:
                found = window[0]["round"] - end
                break
        overlapping = [q["id"] for q in interventions if q["id"] != p["id"]
                       and q["at_round"] <= (after[-1]["round"] if after else end)
                       and q["at_round"] + q["duration"] - 1 >= first]
        recoveries.append({"intervention": p["id"], "at_round": first, "end_round": end,
                           "status": "not_observed" if not seen else "baseline_not_established" if not established else
                           "right_censored" if found is None else "observed_return_or_maintenance",
                           "rounds_after_end": found if seen and established else None,
                           "first_stable_attainment_after_end": found if seen else None,
                           "stable_rounds_required": stability, "other_interventions_in_window": overlapping})
    participation = {m["id"]: sum(e["source"] == m["id"] for e in delivered) for m in config["team"]["members"]}
    return {"series": series, "sent": len(messages), "delivered": len(delivered),
            "delivery_ratio": len(delivered) / len(messages) if messages else None,
            "directed_edge_reciprocity": sum((b, a) in directed for a, b in directed) / len(directed) if directed else None,
            "message_activity_cv": variation, "rounds_observed": len(series), "participation": participation,
            "recovery": recoveries,
            "interpretation": "Descriptive counts and checked task-state stability. Not causal coupling, an attractor estimate or a validated human-team measure."}
