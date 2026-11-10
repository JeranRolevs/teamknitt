"""Public retention-policy contract. No generator, labels or split seeds."""
import ast
import math

MAX_SOURCE_BYTES=16384
AUX_SIZE=32
MATH_NAMES={"sqrt","log","log1p","exp","sin","cos","floor","ceil","isfinite","fabs","pi","e"}
METHODS={"append","pop","sort","copy","get","items","keys","values","extend","index","count","insert","remove","clear","update","setdefault"}
BUILTINS={"len":len,"range":range,"min":min,"max":max,"sum":sum,"abs":abs,
          "sorted":sorted,"enumerate":enumerate,"zip":zip,"list":list,"tuple":tuple,
          "float":float,"int":int,"round":round,"reversed":reversed,"all":all,"any":any}

FIFO_SOURCE="""def select(bank, ages, new, t, capacity, aux):
    count = len(bank) + 1
    return {"keep": list(range(max(0, count-capacity), count)), "aux": []}
"""

RESERVOIR_SOURCE="""def select(bank, ages, new, t, capacity, aux):
    count = len(bank)
    seed = int(aux[0]) if aux else 123456789
    seed = (1664525*seed + 1013904223) % 4294967296
    if count < capacity:
        keep = list(range(count+1))
    else:
        slot = seed % (t+1)
        keep = [i for i in range(count) if i != slot] + [count] if slot < capacity else list(range(count))
    return {"keep": keep, "aux": [seed]}
"""


def compile_policy(source):
    if not isinstance(source,str) or len(source.encode())>MAX_SOURCE_BYTES:
        raise ValueError("Policy source must be a string of at most 16384 UTF-8 bytes.")
    try: tree=ast.parse(source,filename="candidate.py")
    except SyntaxError as error: raise ValueError("Invalid policy syntax at line "+str(error.lineno)+": "+error.msg) from None
    if len(tree.body)!=1 or not isinstance(tree.body[0],ast.FunctionDef) or tree.body[0].name!="select":
        raise ValueError("Submit exactly one top-level function named select.")
    function=tree.body[0]
    if [a.arg for a in function.args.args]!=["bank","ages","new","t","capacity","aux"]:
        raise ValueError("Required signature: select(bank, ages, new, t, capacity, aux).")
    forbidden=(ast.Import,ast.ImportFrom,ast.Global,ast.Nonlocal,ast.ClassDef,ast.AsyncFunctionDef,
               ast.Await,ast.Yield,ast.YieldFrom,ast.With,ast.AsyncWith)
    for node in ast.walk(tree):
        if isinstance(node,forbidden):
            raise ValueError("Imports, global state, classes and async/context operations are not permitted.")
        if isinstance(node,(ast.Name,ast.arg)):
            name=node.id if isinstance(node,ast.Name) else node.arg
            if name.startswith("_"):
                raise ValueError("Private and introspection identifiers are not permitted.")
        if isinstance(node,ast.FunctionDef):
            if node.decorator_list or node.args.defaults or node.args.kw_defaults or node.returns or node.args.vararg or node.args.kwarg or node.args.posonlyargs or node.args.kwonlyargs or any(a.annotation for a in node.args.args):
                raise ValueError("No decorators, annotations, defaults or variadic arguments.")
        if isinstance(node,ast.Attribute):
            if not isinstance(node.ctx,ast.Load):
                raise ValueError("Attribute mutation is not permitted.")
            if isinstance(node.value,ast.Name) and node.value.id=="math":
                if node.attr not in MATH_NAMES: raise ValueError("Unsupported math member.")
            elif node.attr not in METHODS:
                raise ValueError("Only declared list/dict methods and math members are permitted.")
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {
                "eval","exec","compile","open","print","input","getattr","setattr","delattr","globals","locals",
                "vars","dir","type","object","super","help","breakpoint","exit","quit"}:
            raise ValueError("I/O, introspection and dynamic execution are not part of the policy API.")
    return compile(tree,"candidate.py","exec")


def validate_update(result,count,capacity):
    if not isinstance(result,dict) or set(result)!={"keep","aux"}:
        raise ValueError("Return exactly keep and aux.")
    keep,aux=result["keep"],result["aux"]
    if not isinstance(keep,list) or not 1<=len(keep)<=min(count,capacity):
        raise ValueError("Keep between 1 and capacity available vectors.")
    if any(isinstance(i,bool) or not isinstance(i,int) or not 0<=i<count for i in keep) or len(set(keep))!=len(keep):
        raise ValueError("Keep indices must be unique available integer indices.")
    if not isinstance(aux,list) or len(aux)>AUX_SIZE or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or abs(v)>2**53 for v in aux):
        raise ValueError("Aux must contain at most 32 finite bounded numeric values.")
    return keep,[float(v) for v in aux]
