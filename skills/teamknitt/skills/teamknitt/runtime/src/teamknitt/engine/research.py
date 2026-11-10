"""OS-sandboxed, explicit scientific experiment bridge for a trusted workspace evaluator."""
from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from uuid import uuid4

from .config import parse_yaml, project_file


class ResearchError(ValueError):
    pass


def _literal(path):
    return json.dumps(str(Path(path).resolve()))


def sandbox_profile(workspace, job, script):
    # Broad reads permit installed Python/scientific packages and the read-only reference.
    # Workspace secrets and peer trials are denied; only this job and the trusted script are reopened.
    return "\n".join([
        "(version 1)", "(deny default)", "(allow process*)", "(allow sysctl-read)",
        "(allow mach-lookup)",
        "(allow file-read* (require-not (subpath "+_literal(workspace)+")))",
        "(allow file-read* (subpath "+_literal(job)+"))",
        "(allow file-read* (literal "+_literal(script)+"))",
        "(allow file-write* (subpath "+_literal(job)+"))",
        '(allow file-write* (literal "/dev/null"))',
    ])+"\n"


def worker_environment(reference, job):
    # Never inherit provider keys or arbitrary user PYTHONPATH into scientific workers.
    keep=("PATH","LANG","LC_ALL","SYSTEMROOT","DYLD_LIBRARY_PATH")
    env={key:os.environ[key] for key in keep if key in os.environ}
    env.update(PYTHONPATH=str(reference/"src"),PYTHONDONTWRITEBYTECODE="1",
               TMPDIR=str(job/"tmp"),MPLCONFIGDIR=str(job/"mpl"),NUMBA_CACHE_DIR=str(job/"numba"),
               OPENBLAS_NUM_THREADS="1",OMP_NUM_THREADS="1",MKL_NUM_THREADS="1",
               VECLIB_MAXIMUM_THREADS="1",PYTHONHASHSEED="0")
    return env


def execute_job(workspace, job, config, operation, candidate=None, split="development", statistical_approach="frequentist"):
    if config.get("adapter_kind")=="memory_policy.v1":
        from .memory import execute
        return execute(workspace,job,config,operation,candidate,split,statistical_approach)
    job.mkdir(parents=True,exist_ok=False)
    (job/"tmp").mkdir()
    script=project_file(workspace,config["evaluator_script"])
    reference=Path(config["reference_root"]).resolve()
    sandbox=Path("/usr/bin/sandbox-exec")
    if sys.platform!="darwin" or not sandbox.is_file():
        raise ResearchError("The configured macOS OS sandbox is unavailable; no unrestricted fallback.")
    receipt="experiment:"+job.name
    payload={"receipt_id":receipt,"operation":operation,"reference_root":str(reference),
             "protocol":config["protocol"],"candidate":candidate,"split":split,"statistical_approach":statistical_approach}
    (job/"request.json").write_text(json.dumps(payload,indent=2,allow_nan=False)+"\n")
    profile=job/"sandbox.sb"
    profile.write_text(sandbox_profile(workspace,job,script))
    arguments=[str(sandbox),"-f",str(profile),sys.executable,"-B",str(script),str(job/"request.json")]
    started=time.monotonic()
    process=subprocess.Popen(arguments,cwd=reference,env=worker_environment(reference,job),
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:
        stdout,stderr=process.communicate(timeout=config["timeout_seconds"])
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL)
        stdout,stderr=process.communicate()
        (job/"stdout.log").write_text(stdout)
        (job/"stderr.log").write_text(stderr)
        return {"status":"timeout","receipt_id":receipt,"wall_seconds":time.monotonic()-started,
                "source_ref":str(job/"request.json")}
    (job/"stdout.log").write_text(stdout)
    (job/"stderr.log").write_text(stderr)
    path=job/"result.json"
    if process.returncode or not path.is_file():
        return {"status":"environment_or_execution_failure","receipt_id":receipt,
                "returncode":process.returncode,"wall_seconds":time.monotonic()-started,
                "source_ref":str(job/"stderr.log")}
    result=json.loads(path.read_text())
    json.dumps(result,allow_nan=False)
    if result.get("receipt_id")!=receipt:
        raise ResearchError("Worker receipt ID mismatch.")
    result["source_ref"]=str(path)
    return result


class ResearchBackend:
    def __init__(self,workspace,config_path,trial_root,plan):
        self.workspace=workspace
        self.config=parse_yaml(project_file(workspace,config_path).read_text())
        if set(self.config)!={"schema_version","reference_root","evaluator_script","timeout_seconds","protocol"}:
            raise ResearchError("Unexpected research adapter configuration.")
        if self.config["schema_version"]!=1 or not 1<=self.config["timeout_seconds"]<=600:
            raise ResearchError("Invalid research adapter version/timeout.")
        script=project_file(workspace,self.config["evaluator_script"])
        qualification=workspace/"setup/research_qualification/current.json"
        if not qualification.is_file() or json.loads(qualification.read_text()).get("status")!="qualified":
            raise ResearchError("Run study qualify before any research pilot.")
        import hashlib
        expected=json.loads(qualification.read_text())["operations"]["qualification"]["evaluator_sha256"]
        if hashlib.sha256(script.read_bytes()).hexdigest()!=expected:
            raise ResearchError("Scientific evaluator changed; repeat qualification.")
        self.root=trial_root/"experiments"
        self.plan=plan
        self.calls=0
        self.deadline=time.monotonic()+plan["budget"]["max_wall_seconds"]
        self.receipts={}
        self.confirmation=None
        self.semaphore=asyncio.Semaphore(plan["resources"]["max_experiments"])

    @staticmethod
    def visible_result(result):
        if result.get("status")!="valid":
            return {k:v for k,v in result.items() if k in {"status","receipt_id","reason","returncode","source_ref"}}
        rows=[]
        data=json.loads(json.dumps(result))
        for ch in data["channels"]:
            rows.append({key:ch[key] for key in ("mission","channel","m","age","scan","calibration_blocks_used",
                                                "null_blocks_used","results")})
            for item in rows[-1]["results"]:
                # Event-level details remain in the receipt; summary counts and delays are sufficient here.
                item.pop("event_frames",None)
        return {"status":result["status"],"receipt_id":result["receipt_id"],"candidate":result["candidate"],
                "metrics":result["metrics"],"channels":rows,"limits":result["limits"],"source_ref":result["source_ref"]}

    async def evaluate(self,actor,team,candidate):
        allowed={"statistic","reference","window","threshold","gamma"}
        if not isinstance(candidate,dict) or set(candidate)!=allowed:
            return {"status":"unsupported","reason":"Use the declared complete candidate specification; no arbitrary code."}
        if candidate["statistic"] not in ("damp_raw","knn5_raw","mean_distance_raw") or candidate["reference"] not in ("growing","bounded") or candidate["window"] not in (2000,3000,4500,6000,10000) or candidate["threshold"] not in ("short_rank","age_matched_rank","age_scaled_rank"):
            return {"status":"unsupported","reason":"Candidate is outside the initial Task-A method registry."}
        if isinstance(candidate["gamma"],bool) or not isinstance(candidate["gamma"],(float,int)) or not 0<=candidate["gamma"]<=1:
            return {"status":"unsupported","reason":"Gamma must lie in [0,1]."}
        # Protected confirmation is not exposed by an agent tool.
        allowance=self.plan["budget"]["max_evaluations"]-self.plan["budget"]["confirmation_evaluations_reserved"]
        async with self.semaphore:
            if self.calls>=allowance:
                return {"status":"budget_exhausted","reason":"Development-evaluation allowance exhausted."}
            remaining=self.deadline-time.monotonic()
            if remaining<=0:
                return {"status":"budget_exhausted","reason":"Research wall-time allowance exhausted."}
            bounded=dict(self.config,timeout_seconds=min(self.config["timeout_seconds"],remaining))
            self.calls+=1
            job=self.root/(str(self.calls).zfill(3)+"-"+uuid4().hex[:12])
            result=await asyncio.to_thread(execute_job,self.workspace,job,bounded,"evaluate",candidate,"development",self.plan["statistics"]["approach"])
        self.receipts[result["receipt_id"]]={"actor":actor,"team":team,"result":result}
        return result

    async def complete(self):
        valid=[entry for entry in self.receipts.values()
               if entry["result"].get("status")=="valid"
               and entry["result"]["metrics"].get("calibration_abs_error") is not None]
        reserve=self.plan["budget"]["confirmation_evaluations_reserved"]
        if not valid or reserve<1:
            return
        remaining=self.deadline-time.monotonic()
        if remaining<=0:
            return
        bounded=dict(self.config,timeout_seconds=min(self.config["timeout_seconds"],remaining))
        # Select a detector candidate, never a lab style. This rule is declared before the pilot.
        selected=min(valid,key=lambda e:(e["result"]["metrics"]["calibration_abs_error"],
                     -(e["result"]["metrics"]["event_frame_hit_rate"] or 0),
                     json.dumps(e["result"]["candidate"],sort_keys=True)))
        self.calls+=1
        job=self.root/("confirmation-"+uuid4().hex[:12])
        self.confirmation=await asyncio.to_thread(execute_job,self.workspace,job,bounded,"evaluate",
                     selected["result"]["candidate"],"confirmation",self.plan["statistics"]["approach"])
        self.confirmation["selected_from_receipt"]=selected["result"]["receipt_id"]
        self.confirmation["selection_rule"]="development calibration error, then event-frame power; no holdout feedback"
        (self.root.parent/"confirmation.json").write_text(json.dumps(self.confirmation,indent=2,allow_nan=False)+"\n")

    def finalize(self):
        valid=[entry for entry in self.receipts.values() if entry["result"].get("status")=="valid"]
        errors=[entry["result"]["metrics"]["calibration_abs_error"] for entry in valid
                if entry["result"]["metrics"]["calibration_abs_error"] is not None]
        power=[entry["result"]["metrics"]["event_frame_hit_rate"] for entry in valid
               if entry["result"]["metrics"]["event_frame_hit_rate"] is not None]
        summary={"status":"development_evaluated" if valid else "no_valid_measurements",
                 "candidates_evaluated":self.calls,"receipts":list(self.receipts.values()),
                 "confirmation_opened":self.confirmation is not None,"confirmation":self.confirmation,"automatic_lab_selection":False,
                 "extrema_are_not_a_single_jointly_achieved_detector":True,
                 "metrics":{"measured_candidates":len(valid),
                            "min_candidate_calibration_error":min(errors) if errors else None,
                            "max_candidate_event_hit_rate":max(power) if power else None}}
        (self.root.parent/"research_summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
        confirmed=self.confirmation if self.confirmation and self.confirmation.get("status")=="valid" else None
        metrics={}
        if confirmed:
            source=confirmed["metrics"]
            if source["calibration_abs_error"] is not None:
                metrics["confirmation_calibration_error"]=source["calibration_abs_error"]
            if source["event_frame_hit_rate"] is not None:
                metrics["confirmation_event_frame_hit_rate"]=source["event_frame_hit_rate"]
            metrics["confirmation_measured_candidates"]=1
            (self.root.parent/"measurements.json").write_text(json.dumps(
                {"metrics":metrics,"source_refs":[confirmed["source_ref"]]},indent=2,allow_nan=False)+"\n")
        summary["confirmation_metrics"]=metrics
        (self.root.parent/"research_summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
        return summary


def create_backend(workspace,config_path,trial_root,plan):
    config=parse_yaml(project_file(workspace,config_path).read_text())
    if config.get("adapter_kind")=="memory_policy.v1":
        from .memory import MemoryResearchBackend
        return MemoryResearchBackend(workspace,config_path,trial_root,plan)
    if plan["statistics"].get("prior_records"):
        raise ResearchError("This adapter does not implement reviewed priors; refusing to ignore the selected protocol.")
    return ResearchBackend(workspace,config_path,trial_root,plan)


def qualify_workspace(workspace,config_path):
    config=parse_yaml(project_file(workspace,config_path).read_text())
    if config.get("adapter_kind")=="memory_policy.v1":
        from .memory import qualify_memory
        return qualify_memory(workspace,config_path)
    root=workspace/"setup"/"research_qualification"
    root.mkdir(parents=True,exist_ok=True)
    (root/"_sandbox_secret_canary.txt").write_text("NONSECRET-SANDBOX-CANARY\n")
    stamp=uuid4().hex[:12]
    output={}
    for operation in ("qualification","census","cached_baseline"):
        output[operation]=execute_job(workspace,root/stamp/operation,config,operation)
        if operation=="qualification" and output[operation].get("status")!="qualified":
            raise ResearchError("OS sandbox/instrument qualification failed; inspect qualification artifacts.")
        if operation!="qualification" and output[operation].get("status")!="valid_diagnostic":
            raise ResearchError("Reference-data inventory failed; inspect qualification artifacts.")
    result={"status":"qualified","qualified_at":time.time(),"operations":output}
    (root/"current.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    return {"status":"qualified","source_ref":str(root/"current.json"),
            "checks":output["qualification"]["checks"],
            "eligible_channel_split_rows":len(output["census"]["rows"]),
            "cached_baseline_rows":len(output["cached_baseline"]["rows"])}
