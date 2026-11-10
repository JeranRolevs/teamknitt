"""Trusted controller: private scenario seeds and labels never enter the policy process."""
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import time
import numpy as np

from memory_policy_contract import FIFO_SOURCE,RESERVOIR_SOURCE,compile_policy,validate_update
from memory_benchmark import PolicyProcess,evaluate,interval

SCRIPTS=("memory_evaluator.py","memory_benchmark.py","memory_policy_worker.py","memory_policy_contract.py")


def qualification(protocol,job):
    canary=job/"hidden-label-canary.txt";canary.write_text("NONSECRET HIDDEN LABEL CANARY")
    x=np.random.default_rng(3744).normal(size=(24,protocol["dimension"]))
    with PolicyProcess(FIFO_SOURCE,job/"policy") as worker:
        checks=worker.ask({"op":"selfcheck","canary":str(canary)})["checks"]
        a,_=worker.run(x,4)
        y=x.copy();y[16:]+=100
        b,_=worker.run(y,4)
        checks["future_tail_invariant"]=bool(np.allclose(a[:16],b[:16],equal_nan=True))
        reference=np.array([np.nan]+[np.sqrt(np.mean((x[max(0,t-4):t]-x[t])**2,axis=1)).min() for t in range(1,len(x))])
        checks["raw_distance_matches_direct_past"]=bool(np.allclose(a,reference,equal_nan=True))
    rejected=False
    try: validate_update({"keep":[0,1,2],"aux":[]},3,2)
    except ValueError: rejected=True
    checks["memory_overflow_rejected"]=rejected
    checks["clopper_pearson_endpoints"]=abs(interval(0,10)[1]-(1-.025**.1))<1e-12
    return {"status":"qualified" if all(checks.values()) else "qualification_failed","checks":checks,
            "separation":"trusted supervisor owns seeds/labels; untrusted policy receives only reset dimensions and causal observations"}


def validate_panels(splits,protocol):
    values=[seed for phase in ("development","confirmation") for kind in ("calibration","null","fault") for seed in splits[phase][kind]]
    if len(values)!=len(set(values)):
        raise ValueError("Calibration, scored and confirmation seed panels must be disjoint.")
    for phase in ("development","confirmation"):
        for kind,count in (("calibration",protocol["calibration_runs"]),("null",protocol["null_runs"]),("fault",protocol["fault_runs"])):
            if len(splits[phase][kind])<count: raise ValueError("Private split has fewer runs than requested.")


def main():
    parser=argparse.ArgumentParser();parser.add_argument("request",type=Path);args=parser.parse_args()
    request=json.loads(args.request.read_text());job=args.request.resolve().parent
    protocol=request["protocol"]
    started=time.monotonic()
    operation=request["operation"]
    if request.get("statistical_approach", "frequentist") != "frequentist" or protocol.get("bayesian_prior") is not None:
        raise ValueError("Bayesian/probabilistic analysis is not supported by teamknitt.")
    if operation=="qualification":
        result=qualification(protocol,job)
    elif operation in ("evaluate","baselines"):
        private=Path(request["private_seed_file"])
        splits=json.loads(private.read_text())
        seed_hash=hashlib.sha256(private.read_bytes()).hexdigest()
        validate_panels(splits,protocol)
        split=request.get("split","development")
        seeds=splits[split]
        if operation=="evaluate":
            candidate=request["candidate"]
            try:
                compile_policy(candidate["source"])
                result=evaluate(candidate["source"],protocol,seeds,split,job)
                result["candidate"]={"name":candidate["name"],"source_sha256":hashlib.sha256(candidate["source"].encode()).hexdigest()}
            except (ValueError,RuntimeError,BrokenPipeError) as error:
                result={"status":"invalid_candidate","reason":str(error)[:600]}
        else:
            result={"status":"valid_diagnostic","comparators":{}}
            for name,source,capacity in (("fifo",FIFO_SOURCE,protocol["capacity"]),
                                         ("reservoir",RESERVOIR_SOURCE,protocol["capacity"]),
                                         ("growing_unbounded",FIFO_SOURCE,protocol["steps"])):
                place=job/name;place.mkdir()
                row=evaluate(source,protocol,seeds,"development",place,capacity=capacity)
                row["within_primary_memory_budget"]=name!="growing_unbounded"
                result["comparators"][name]=row
    else: raise ValueError("Unsupported operation.")
    if operation in ("evaluate","baselines"): result["seed_manifest_sha256"]=seed_hash
    result.update(receipt_id=request["receipt_id"],adapter_kind="memory_policy.v1",
          statistical_approach=request.get("statistical_approach","frequentist"),wall_seconds=time.monotonic()-started,
          evaluator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          source_hashes={name:hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest() for name in SCRIPTS},
          supervisor_execution="trusted local code; candidate execution is isolated in a separate OS-sandboxed process")
    (job/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":result["status"],"receipt_id":result["receipt_id"],"wall_seconds":result["wall_seconds"]}))


if __name__=="__main__": main()
