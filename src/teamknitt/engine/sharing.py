"""Bounded structured sharing, used within a lab and between labs."""
import json


def filtered_view(rows, policy, valid_receipts=()):
    if not policy["research_exchange"]:
        return {}, 0
    detail, entries = policy["detail"], []
    valid = set(valid_receipts)
    for row in rows:
        output = row["output"]
        if detail in {"intermediate", "high"}:
            entry = {"summary": output["summary"]}
            if detail == "high":
                entry.update(findings=output["findings"], candidate_output=output["candidate_output"])
            entries.append(entry)
        elif detail == "low":
            for finding in output["findings"]:
                refs = finding.get("evidence_refs", [])
                if finding.get("kind") == "dead_end" and isinstance(refs, list) and any(
                        ref in valid for ref in refs if isinstance(ref, str)):
                    entries.append({"agent_interpretation": finding.get("text"), "evidence_refs": refs,
                                    "status": "measured_development_evidence_not_a_confirmed_general_claim"})
    view = {detail + ".md": "\n\n".join(json.dumps(item) for item in entries)} if detail != "none" else {}
    if policy["wisdom"]:
        # Only the declared abstraction fields enter this channel; no extra model-supplied fields.
        wisdom = [{key: item[key] for key in ("lesson", "conditions", "limits") if isinstance(item.get(key), str)}
                  for row in rows for item in row["output"]["wisdom"]]
        view["wisdom.md"] = "\n\n".join(json.dumps(item) for item in wisdom if item)
    remaining = policy["max_read_words"]
    for name, value in view.items():
        view[name] = " ".join(value.split()[:remaining])
        remaining -= len(view[name].split())
    return view, len(entries) if detail == "low" else 0
