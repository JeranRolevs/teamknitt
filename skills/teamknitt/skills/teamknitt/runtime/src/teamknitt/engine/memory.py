"""Model-authored retention policies evaluated by a trusted, separate local supervisor."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from uuid import uuid4

from .config import parse_yaml,project_file
from .research import ResearchError

FILES=("memory_evaluator.py","memory_benchmark.py","memory_policy_worker.py","memory_policy_contract.py")
QUALIFICATION="setup/memory_qualification/current.json"
ACTION_CONTRACT="""
Scientific tool for this mission:
{"action":"experiment.run","candidate":{"name":"your_policy","source":"def select(bank, ages, new, t, capacity, aux):\\n    ..."}}
Write your own executable Python retention policy, not a preset name.
Required signature: select(bank, ages, new, t, capacity, aux).
bank is a list of retained vectors; ages contains their observation indices; new is the current
vector; t is its index. The scorer has already scored new against the OLD bank.
Return exactly {"keep":[unique indices into bank+[new]],"aux":[up to 32 numbers]}.
Keep at least one and at most capacity vectors. Aux is your only additional persistent state.
You may use len, range, min, max, sum, abs, sorted, enumerate, zip, list, tuple, float, int,
round, reversed, all, any; math.sqrt/log/log1p/exp/sin/cos/floor/ceil/isfinite/fabs/pi/e; and
ordinary list/dict methods. No imports, private identifiers, globals, I/O, classes, decorators
or dynamic execution. Source limit 16384 UTF-8 bytes. Your namespace is fresh on every call.
A separate OS-sandboxed process runs the policy. It receives no labels, seeds, phase names or
future input. State overflow, malformed code and excessive runtime produce failed receipts.
Independent benign calibration runs set thresholds. The false-alarm unit is any alarm during a
fixed-horizon benign run, not one point. Fault recall is one labelled fault per independent run.
Use actual receipt IDs in findings. Development evidence may inform another policy; protected
confirmation is never returned to agents. Do not claim external-dataset transfer, compression, perpetual-run
control or general lab-style superiority from this synthetic retention-only pilot.
"""


def config_for(workspace,path):
    c=parse_yaml(project_file(workspace,path).read_text())
    required={"schema_version","adapter_kind","supervisor_script","private_seed_file","timeout_seconds","protocol"}
    if set(c)!=required or c["schema_version"]!=1 or c["adapter_kind"]!="memory_policy.v1" or not 1<=c["timeout_seconds"]<=600:
        raise ResearchError("Invalid memory adapter configuration.")
    project_file(workspace,c["supervisor_script"]);project_file(workspace,c["private_seed_file"])
    p=c["protocol"]
    if p.get("bayesian_prior") is not None:
        raise ResearchError("Bayesian priors are not supported in teamknitt.")
    for key in ("capacity","dimension","steps","warmup","calibration_runs","null_runs","fault_runs"):
        if isinstance(p.get(key),bool) or not isinstance(p.get(key),int) or p[key]<1:
            raise ResearchError("Memory protocol counts/dimensions must be positive integers.")
    if p["calibration_runs"]<9 or p["steps"]<=p["warmup"]+32 or not 8<=p["dimension"]<=128 or p["capacity"]>4096:
        raise ResearchError("Unsupported memory protocol shape or insufficient primary calibration.")
    if p.get("difficulty")=="research" and p["warmup"]<48:
        raise ResearchError("Research cases need at least 48 warmup observations.")
    if .1 not in p["alpha_targets"] or any(not 0<a<1 for a in p["alpha_targets"]):
        raise ResearchError("Include the primary 10% target; all targets must lie in (0,1).")
    return c


def execute(workspace,job,config,operation,candidate=None,split="development",approach="frequentist",author=None):
    if approach != "frequentist" or config.get("_reviewed_priors") or config["protocol"].get("bayesian_prior") is not None:
        raise ResearchError("teamknitt does not support Bayesian analysis; no method was silently changed.")
    job.mkdir(parents=True,exist_ok=False)
    script=project_file(workspace,config["supervisor_script"])
    payload={"receipt_id":"experiment:"+job.name,"operation":operation,"candidate":candidate,"split":split,
             "protocol":config["protocol"],"private_seed_file":str(project_file(workspace,config["private_seed_file"])),
             "statistical_approach":approach,"source_authorship":author}
    (job/"request.json").write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    env={"PATH":os.environ.get("PATH","/usr/bin:/bin"),"LANG":"en_US.UTF-8","PYTHONDONTWRITEBYTECODE":"1",
         "OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1",
         "VECLIB_MAXIMUM_THREADS":"1","PYTHONHASHSEED":"0"}
    started=time.monotonic()
    process=subprocess.Popen([sys.executable,"-B",str(script),str(job/"request.json")],cwd=workspace,
                  env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
        out,err=process.communicate(timeout=config["timeout_seconds"])
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL);out,err=process.communicate()
        (job/"stdout.log").write_text(out);(job/"stderr.log").write_text(err)
        return {"status":"timeout","receipt_id":payload["receipt_id"],"source_ref":str(job/"request.json")}
    (job/"stdout.log").write_text(out);(job/"stderr.log").write_text(err)
    path=job/"result.json"
    if process.returncode or not path.is_file():
        return {"status":"environment_or_execution_failure","receipt_id":payload["receipt_id"],
                "returncode":process.returncode,"source_ref":str(job/"stderr.log")}
    result=json.loads(path.read_text());json.dumps(result,allow_nan=False)
    if result.get("receipt_id")!=payload["receipt_id"]: raise ResearchError("Memory receipt mismatch.")
    result.update(source_ref=str(path),source_authorship=author,supervisor_wall_seconds=time.monotonic()-started)
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    return result


class MemoryResearchBackend:
    action_contract=ACTION_CONTRACT
    def __init__(self,workspace,config_path,trial_root,plan):
        self.workspace=workspace;self.plan=plan;self.config=config_for(workspace,config_path)
        current=workspace/QUALIFICATION
        if not current.is_file(): raise ResearchError("Qualify the memory task before research runs.")
        qualified=json.loads(current.read_text())
        if qualified.get("status")!="qualified": raise ResearchError("Memory task qualification failed.")
        root=project_file(workspace,self.config["supervisor_script"]).parent
        expected=qualified["operations"]["qualification"]["source_hashes"]
        if any(hashlib.sha256((root/name).read_bytes()).hexdigest()!=expected[name] for name in FILES):
            raise ResearchError("Memory task source changed; repeat qualification.")
        self.root=trial_root/"experiments";self.calls=0;self.receipts={};self.confirmation=None
        self.generation_model=None
        self.deadline=time.monotonic()+plan["budget"]["max_wall_seconds"]
        self.semaphore=asyncio.Semaphore(plan["resources"]["max_experiments"])

    @staticmethod
    def visible_result(result):
        keep=("status","receipt_id","reason","returncode","source_ref","candidate","metrics","results",
              "counts","memory_budget_bytes","limits","source_authorship")
        return {k:v for k,v in result.items() if k in keep}

    async def evaluate(self,actor,team,candidate):
        if not isinstance(candidate,dict) or set(candidate)!={"name","source"} or not all(isinstance(candidate[k],str) for k in candidate) or not candidate["name"].strip() or len(candidate["source"].encode())>16384:
            return {"status":"unsupported","reason":"Supply name and Python source, at most 16384 bytes."}
        allowance=self.plan["budget"]["max_evaluations"]-self.plan["budget"]["confirmation_evaluations_reserved"]
        author={"actor":actor,"team":team,"generation_model":self.generation_model,
                "source_sha256":hashlib.sha256(candidate["source"].encode()).hexdigest()}
        async with self.semaphore:
            if self.calls>=allowance: return {"status":"budget_exhausted","reason":"Development allowance exhausted."}
            remaining=self.deadline-time.monotonic()
            if remaining<=0: return {"status":"budget_exhausted","reason":"Research wall-time allowance exhausted."}
            bounded=dict(self.config,timeout_seconds=min(self.config["timeout_seconds"],remaining))
            self.calls+=1;job=self.root/(str(self.calls).zfill(3)+"-"+uuid4().hex[:12])
            result=await asyncio.to_thread(execute,self.workspace,job,bounded,"evaluate",candidate,"development",
                                         self.plan["statistics"]["approach"],author)
        self.receipts[result["receipt_id"]]={"actor":actor,"team":team,"candidate":candidate,"result":result}
        return result

    async def complete(self):
        valid=[e for e in self.receipts.values() if e["result"].get("status")=="valid"]
        if not valid or self.plan["budget"]["confirmation_evaluations_reserved"]<1: return
        def key(e):
            m=e["result"]["metrics"]
            return (max(0,m["run_false_alarm_rate"]-.1),-m["fault_recall"],
                    m["calibration_abs_error"],e["result"]["source_sha256"])
        remaining=self.deadline-time.monotonic()
        if remaining<=0: return
        bounded=dict(self.config,timeout_seconds=min(self.config["timeout_seconds"],remaining))
        selected=min(valid,key=key);self.calls+=1
        self.confirmation=await asyncio.to_thread(execute,self.workspace,
            self.root/("confirmation-"+uuid4().hex[:12]),bounded,"evaluate",selected["candidate"],"confirmation",
            self.plan["statistics"]["approach"],selected["result"]["source_authorship"])
        self.confirmation["selected_from_receipt"]=selected["result"]["receipt_id"]
        self.confirmation["selection_rule"]="min development FAR excess above 10%, then max fault recall, then calibration error; exploratory point estimates"
        (self.root.parent/"confirmation.json").write_text(json.dumps(self.confirmation,indent=2,allow_nan=False)+"\n")

    def finalize(self):
        confirmed=self.confirmation if self.confirmation and self.confirmation.get("status")=="valid" else None
        metrics={}
        if confirmed:
            m=confirmed["metrics"]
            metrics={"confirmation_run_false_alarm_rate":m["run_false_alarm_rate"],
                     "confirmation_fault_recall":m["fault_recall"],
                     "confirmation_calibration_error":m["calibration_abs_error"],
                     "confirmation_peak_memory_bytes":m["peak_memory_bytes"]}
            if m["benign_recurrence_alarm_rate"] is not None:
                metrics["confirmation_benign_recurrence_alarm_rate"]=m["benign_recurrence_alarm_rate"]
            (self.root.parent/"measurements.json").write_text(json.dumps({"metrics":metrics,"source_refs":[confirmed["source_ref"]]},indent=2)+"\n")
        summary={"status":"development_evaluated" if self.receipts else "no_evaluations",
                 "evaluation_invocations":self.calls,"receipts":list(self.receipts.values()),
                 "confirmation":self.confirmation,"confirmation_metrics":metrics,"automatic_lab_selection":False}
        (self.root.parent/"research_summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
        return summary


def qualify_memory(workspace,path):
    c=config_for(workspace,path);root=workspace/"setup/memory_qualification"
    root.mkdir(parents=True,exist_ok=True);stamp=uuid4().hex[:12]
    output={}
    output["qualification"]=execute(workspace,root/stamp/"qualification",c,"qualification")
    if output["qualification"].get("status")!="qualified":
        raise ResearchError("Memory policy sandbox/instrument failed qualification; inspect its artifacts.")
    output["baselines"]=execute(workspace,root/stamp/"baselines",c,"baselines")
    if output["baselines"].get("status")!="valid_diagnostic":
        raise ResearchError("Memory comparator evaluation failed.")
    result={"status":"qualified","qualified_at":time.time(),"operations":output}
    (root/"current.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    return {"status":"qualified","source_ref":str(root/"current.json"),
            "checks":output["qualification"]["checks"],"comparators":list(output["baselines"]["comparators"])}
