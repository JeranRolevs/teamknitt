"""Untrusted policy execution process. Only observations enter over stdin."""
import argparse
import errno
import json
import math
import os
from pathlib import Path
import resource
import socket
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from memory_policy_contract import BUILTINS,compile_policy,validate_update


def main():
    resource.setrlimit(resource.RLIMIT_CPU,(120,125))
    resource.setrlimit(resource.RLIMIT_NOFILE,(32,32))
    parser=argparse.ArgumentParser()
    parser.add_argument("source",type=Path)
    args=parser.parse_args()
    compiled=compile_policy(args.source.read_text())
    bank=[];ages=[];aux=[];dimension=capacity=counter=0
    for line in sys.stdin:
        try:
            request=json.loads(line)
            operation=request["op"]
            if operation=="close": break
            if operation=="selfcheck":
                private=Path(request["canary"])
                checks={}
                try: private.read_text();checks["hidden_file_read_denied"]=False
                except PermissionError: checks["hidden_file_read_denied"]=True
                try: private.with_name("forbidden-write.txt").write_text("probe");checks["external_write_denied"]=False
                except PermissionError: checks["external_write_denied"]=True
                try:
                    connection=socket.create_connection(("127.0.0.1",9),timeout=.2)
                    connection.close();checks["network_denied"]=False
                except OSError as error: checks["network_denied"]=error.errno in (errno.EPERM,errno.EACCES)
                try:
                    pid=os.fork()
                    if pid==0: os._exit(0)
                    os.waitpid(pid,0);checks["process_fork_denied"]=False
                except PermissionError: checks["process_fork_denied"]=True
                response={"checks":checks}
            elif operation=="reset":
                capacity=int(request["capacity"]);dimension=int(request["dimension"])
                if not 1<=capacity<=4096 or not 1<=dimension<=128: raise ValueError("Unsupported task dimensions.")
                bank=[];ages=[];aux=[];counter=0
                response={"status":"reset"}
            elif operation=="step":
                x=request["x"];t=request["t"]
                if not dimension or t!=counter or len(x)!=dimension or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in x):
                    raise ValueError("Invalid observation or time index.")
                namespace={"__builtins__":BUILTINS.copy(),"math":math}
                exec(compiled,namespace)
                result=namespace["select"]([v[:] for v in bank],ages[:],x[:],t,capacity,aux[:])
                keep,aux=validate_update(result,len(bank)+1,capacity)
                choices=bank+[x];times=ages+[t]
                bank=[choices[i] for i in keep];ages=[times[i] for i in keep]
                counter+=1
                response={"keep":keep,"aux":aux}
            else:
                raise ValueError("Unknown protocol operation.")
            print(json.dumps(response,allow_nan=False),flush=True)
        except Exception as error:
            print(json.dumps({"error":str(error)[:400],"kind":type(error).__name__}),flush=True)


if __name__=="__main__": main()
