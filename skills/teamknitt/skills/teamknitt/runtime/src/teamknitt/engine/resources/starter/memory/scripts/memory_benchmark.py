"""Trusted synthetic benchmark and IPC supervisor. Never executes submitted source."""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import select
import signal
import resource
import subprocess
import sys
import time

import numpy as np
import psutil
from scipy.stats import beta
from memory_policy_contract import AUX_SIZE,FIFO_SOURCE,RESERVOIR_SOURCE,compile_policy,validate_update

FAMILIES=("recurrence","drift","returning_regime","mixed")


def interval(k,n):
    return None if not n else [0.0 if k==0 else float(beta.ppf(.025,k,n-k+1)),
                              1.0 if k==n else float(beta.ppf(.975,k+1,n-k))]


def proportion(k,n):
    row={"k":int(k),"n":int(n),"rate":float(k/n) if n else None,"cp95":interval(k,n),
         "unit":"one independent generated run; one fault per fault run"}
    return row


def rank_threshold(values,alpha):
    n=len(values);rank=math.ceil((n+1)*(1-alpha))
    if not n or rank>n: return {"status":"insufficient_calibration","value":None,"n":n,"rank":rank}
    return {"status":"estimated","value":float(np.sort(values)[rank-1]),"n":n,"rank":rank,
            "marginal_exchangeable_exceedance_bound":(n+1-rank)/(n+1),
            "assumption":"independent exchangeable calibration and null runs; no guarantee under arbitrary shifts"}


def scenario(seed,protocol,fault=False,split="development"):
    rng=np.random.default_rng(seed)
    steps=protocol["steps"];m=protocol["dimension"];warm=protocol["warmup"]
    family=FAMILIES[int(rng.integers(len(FAMILIES)))]
    phase=np.linspace(0,2*np.pi,m,endpoint=False)
    shift=float(rng.uniform(-.2,.2));amp=float(rng.uniform(.8,1.2))
    motifs=np.stack([np.sin(phase),np.cos(phase),np.sin(2*phase+.4),np.where(phase<np.pi,1.,-1.)])
    research=protocol.get("difficulty")=="research"
    if research:
        count=int(rng.choice([8,16,40]))
        basis=np.stack([np.sin(phase),np.cos(phase),np.sin(2*phase),np.cos(2*phase),np.sin(3*phase)])
        coefficients=rng.normal(size=(count,5))
        motifs=coefficients@basis
        motifs/=np.sqrt(np.mean(motifs*motifs,axis=1))[:,None]
    motifs=amp*motifs+shift
    selected=rng.integers(0,2,size=steps)
    if research:
        uncommon=rng.random(steps)<.2
        selected[uncommon]=rng.integers(2,len(motifs),size=int(uncommon.sum()))
    x=motifs[selected].copy()+rng.normal(0,.04,size=(steps,m))
    # Every mode is observed during warmup; full cases can exceed memory capacity.
    locations=range(4,4+len(motifs)) if research else [4+j*6 for j in range(4)]
    for j,t in enumerate(locations): x[t]=motifs[j]+rng.normal(0,.04,m)
    period=int(rng.integers(64,97) if split=="development" else rng.integers(104,145))
    rare=np.zeros(steps,dtype=bool)
    for t in range(warm-4 if research else 12,steps,period):
        x[t]=motifs[-1]+rng.normal(0,.04,m);rare[t]=True
    if family in ("drift","mixed"):
        drift=np.maximum(0,np.arange(steps)-warm)/(steps-warm)*rng.uniform(.1,.45)
        x+=drift[:,None]*np.sin(phase+.2)
    if family in ("returning_regime","mixed"):
        a=int(rng.integers(warm+4,warm+24));b=int(rng.integers(steps//2,steps-24))
        x[a:b]=motifs[2]+rng.normal(0,.04,size=(b-a,m))
    for t in np.flatnonzero(rare):
        x[t]=motifs[3]+rng.normal(0,.04,m)
    labels=np.zeros(steps,dtype=bool)
    onset=None;kind=None
    if fault:
        onset=int(rng.integers(warm+8,steps-16))
        duration=int(rng.integers(4,13))
        kind=("spike","shape_change","level_change")[int(rng.integers(3))]
        if kind=="spike":
            x[onset:onset+duration,m//2]+=rng.uniform(.8,2.5) if research else rng.uniform(2,3.5)
        elif kind=="shape_change":
            x[onset:onset+duration]+=(rng.uniform(.3,1.)*np.sin(5*phase+.7) if research else 1.25*np.sin(3*phase+.7))
        else:
            x[onset:onset+duration]+=rng.uniform(.25,.9) if research else rng.uniform(.7,1.3)
        labels[onset:onset+duration]=True
        rare[labels]=False
    return {"x":x,"fault":labels,"benign_recurrence":rare,"family":family,
            "onset":onset,"fault_kind":kind}


def policy_sandbox(worker,contract,source):
    literal=lambda p:json.dumps(str(Path(p).resolve()))
    return "\n".join([
        "(version 1)","(deny default)","(allow process-exec)","(allow sysctl-read)",
        "(allow file-read-metadata)",
        # The system loader opens the root directory before Python starts.
        '(allow file-read* (literal "/"))',
        "(allow file-read* (subpath "+literal(sys.base_prefix)+"))",
        '(allow file-read* (subpath "/System/Library") (subpath "/usr/lib") (subpath "/private/var/db/dyld"))',
        "(allow file-read* (literal "+literal(worker)+") (literal "+literal(Path(worker).parent)+") (literal "+literal(contract)+") (literal "+literal(source)+"))",
        '(allow file-read* (literal "/dev/null") (literal "/dev/urandom"))',
        '(allow file-write* (literal "/dev/null"))',
    ])+"\n"


class PolicyProcess:
    def __init__(self,source,job):
        compile_policy(source)  # AST validation only; no exec in the supervisor.
        self.job=Path(job);self.job.mkdir(parents=True,exist_ok=False)
        path=self.job/"candidate.py";path.write_text(source)
        worker=Path(__file__).with_name("memory_policy_worker.py")
        contract=Path(__file__).with_name("memory_policy_contract.py")
        self.profile=self.job/"sandbox.sb"
        self.profile.write_text(policy_sandbox(worker,contract,path))
        if sys.platform!="darwin" or not Path("/usr/bin/sandbox-exec").is_file():
            raise RuntimeError("macOS sandbox unavailable; no unsandboxed candidate fallback.")
        self.stderr=(self.job/"stderr.log").open("w")
        env={"PATH":"/usr/bin:/bin","LANG":"en_US.UTF-8","PYTHONDONTWRITEBYTECODE":"1"}
        self.process=subprocess.Popen(["/usr/bin/sandbox-exec","-f",str(self.profile),str(Path(getattr(sys,"_base_executable",sys.executable)).resolve()),
                          "-I","-S","-B",str(worker),str(path)],stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE,stderr=self.stderr,env=env)
        self.buffer=b"";self.started=time.monotonic()
        self.usage_before=resource.getrusage(resource.RUSAGE_CHILDREN)
        self.cpu_seconds=0.;self.rss_bytes=0
        self.bank=np.empty((0,1));self.ages=[];self.aux=[];self.peak_bytes=0

    def ask(self,request):
        if self.process.poll() is not None: raise RuntimeError("Policy worker exited; inspect its stderr.")
        self.process.stdin.write((json.dumps(request,allow_nan=False)+"\n").encode())
        self.process.stdin.flush()
        deadline=time.monotonic()+2
        while b"\n" not in self.buffer:
            remaining=deadline-time.monotonic()
            if remaining<=0: raise RuntimeError("Policy response timed out.")
            if psutil.Process(self.process.pid).memory_info().rss>128*1024*1024:
                raise RuntimeError("Policy process exceeds the 128 MiB RSS allowance.")
            if not select.select([self.process.stdout],[],[],min(remaining,.05))[0]:
                continue
            chunk=os.read(self.process.stdout.fileno(),65536)
            if not chunk: raise RuntimeError("Policy worker closed its output.")
            self.buffer+=chunk
            if len(self.buffer)>65536: raise RuntimeError("Policy response exceeds the byte limit.")
        line,self.buffer=self.buffer.split(b"\n",1)
        result=json.loads(line)
        json.dumps(result,allow_nan=False)
        if "error" in result: raise ValueError("Policy rejected: "+result["error"])
        return result

    def run(self,x,capacity):
        self.ask({"op":"reset","capacity":capacity,"dimension":x.shape[1]})
        bank=np.empty((0,x.shape[1]));scores=np.empty(len(x));ages=[]
        peak=0
        for t,row in enumerate(x):
            # Score strictly before inserting this observation.
            scores[t]=float(np.sqrt(np.mean((bank-row)**2,axis=1)).min()) if len(bank) else np.nan
            reply=self.ask({"op":"step","x":row.tolist(),"t":t})
            keep,aux=validate_update(reply,len(bank)+1,capacity)
            bank=np.concatenate((bank,row[None,:]),axis=0)[keep]
            ages=[(ages+[t])[i] for i in keep]
            used=bank.nbytes+len(ages)*8+len(aux)*8
            bound=capacity*(x.shape[1]+1)*8+AUX_SIZE*8
            if used>bound: raise ValueError("Numeric state exceeds its memory budget.")
            peak=max(peak,used)
        self.peak_bytes=max(self.peak_bytes,peak)
        return scores,peak

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.write(b'{"op":"close"}\n');self.process.stdin.flush()
                self.process.wait(timeout=2)
            except (BrokenPipeError,subprocess.TimeoutExpired):
                self.process.kill();self.process.wait()
        usage=resource.getrusage(resource.RUSAGE_CHILDREN)
        self.cpu_seconds=usage.ru_utime+usage.ru_stime-self.usage_before.ru_utime-self.usage_before.ru_stime
        self.rss_bytes=int(usage.ru_maxrss*(1 if sys.platform=='darwin' else 1024))
        self.stderr.close()
        if self.process.stdin: self.process.stdin.close()
        if self.process.stdout: self.process.stdout.close()

    def __enter__(self): return self
    def __exit__(self,*args): self.close()


def evaluate(source,protocol,seeds,split,job,capacity=None):
    capacity=capacity or protocol["capacity"]
    warm=protocol["warmup"]
    groups={}
    raw={"calibration":[],"null":[],"fault":[]}
    started=time.monotonic()
    with PolicyProcess(source,Path(job)/"policy") as worker:
        for kind in raw:
            count=protocol[{"calibration":"calibration_runs","null":"null_runs","fault":"fault_runs"}[kind]]
            for seed in seeds[kind][:count]:
                case=scenario(seed,protocol,fault=kind=="fault",split=split)
                scores,peak=worker.run(case["x"],capacity)
                if not np.all(np.isfinite(scores[warm:])): raise ValueError("Nonfinite scored output.")
                row={"run_id":hashlib.sha256(str(seed).encode()).hexdigest()[:16],"family":case["family"],
                     "maximum":float(scores[warm:].max()),"peak_memory_bytes":peak}
                if kind!="calibration":
                    row["scores"]=scores
                    row["case"]=case
                raw[kind].append(row)
        peak=worker.peak_bytes
    if worker.rss_bytes>128*1024*1024: raise ValueError("Policy peak RSS exceeded 128 MiB.")
    results=[]
    for alpha in protocol["alpha_targets"]:
        fitted=rank_threshold([r["maximum"] for r in raw["calibration"]],alpha)
        if fitted["value"] is None:
            results.append({"alpha":alpha,"status":"insufficient_calibration","threshold":fitted});continue
        h=fitted["value"]
        null=raw["null"];fault=raw["fault"]
        hit=sum(bool(np.any(r["scores"][r["case"]["fault"]]>h)) for r in fault)
        alarm=sum(r["maximum"]>h for r in null)
        recurrence=[r for r in null if np.any(r["case"]["benign_recurrence"][warm:])]
        rare_alarm=sum(bool(np.any(r["scores"][warm:][r["case"]["benign_recurrence"][warm:]]>h)) for r in recurrence)
        delays=[]
        for r in fault:
            positions=np.flatnonzero((r["scores"]>h)&r["case"]["fault"])
            if len(positions): delays.append(int(positions[0]-r["case"]["onset"]))
        by_family={}
        for family in FAMILIES:
            negatives=[r for r in null if r["family"]==family]
            positives=[r for r in fault if r["family"]==family]
            by_family[family]={"run_false_alarms":proportion(sum(r["maximum"]>h for r in negatives),len(negatives)),
                  "fault_recall":proportion(sum(bool(np.any(r["scores"][r["case"]["fault"]]>h)) for r in positives),len(positives))}
        results.append({"alpha":alpha,"status":"measured","threshold":fitted,
               "run_false_alarms":proportion(alarm,len(null)),
               "fault_recall":proportion(hit,len(fault)),
               "benign_recurrence_alarm_runs":proportion(rare_alarm,len(recurrence)),
               "median_detected_delay_ticks":float(np.median(delays)) if delays else None,
               "by_family":by_family})
    main=next(r for r in results if r["alpha"]==.1)
    # Calibration closeness is a separate objective, never a lab-design optimizer.
    metrics={"calibration_abs_error":abs(main["run_false_alarms"]["rate"]-.1),
             "fault_recall":main["fault_recall"]["rate"],"run_false_alarm_rate":main["run_false_alarms"]["rate"],
             "benign_recurrence_alarm_rate":main["benign_recurrence_alarm_runs"]["rate"],
             "peak_memory_bytes":peak,"worker_peak_rss_bytes":worker.rss_bytes,"worker_cpu_seconds":worker.cpu_seconds,
             "elapsed_seconds":time.monotonic()-started}
    ids={kind:[r["run_id"] for r in rows] for kind,rows in raw.items()}
    return {"status":"valid","adapter_kind":"memory_policy.v1","split":split,"metrics":metrics,"results":results,
            "counts":{kind:len(rows) for kind,rows in raw.items()},"run_ids":ids,
            "memory_budget_bytes":capacity*(protocol["dimension"]+1)*8+AUX_SIZE*8,
            "source_sha256":hashlib.sha256(source.encode()).hexdigest(),
            "limits":["One independent null run is the false-alarm unit, not one point or a perpetual-operation guarantee.",
                      "A fixed horizon and synthetic mechanism family; ESA transfer and compression remain future work.",
                      "Candidate functions retain observations and auxiliary scalars; no labels or future input are passed.",
                      "Timing includes IPC and supervisor costs; process RSS and source bytes are separate from numeric policy state."]}
