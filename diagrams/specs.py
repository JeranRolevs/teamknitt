"""Canonical diagram descriptions: export the same nodes/edges to images and Mermaid."""
DATE = "2026-10-31"
STYLE = {
    "background": "#F5F1E8",
    "ink": "#342F28",
    "secondary": "#6B6255",
    "fine_rule": "#D2C9BC",
    "connector": "#887E6B",
    "accent": "#87744F",
    "body_font": "DejaVu Sans",
    "display_font": "DejaVu Serif",
}
COLORS = {
    "artifact": ("#FCFAF4", "#99876F"),
    "llm": ("#E9EEEE", "#5B7580"),
    "code": ("#EDF0E6", "#697957"),
    "evidence": ("#F1EADD", "#93805D"),
    "optional": ("#F6EDDC", "#9A7440"),
    "future": ("#EEEDE8", "#999389"),
}


def graph(stem, title, subtitle, width=20, height=12, direction="LR"):
    return dict(stem=stem, title=title, subtitle=subtitle, width=width, height=height,
                direction=direction, nodes=[], edges=[],
                footer="User chooses organization and sharing. Candidate iteration does not redesign the lab.")


def node(g, key, x, y, title, body="", kind="artifact", w=3.6, h=1.35):
    g["nodes"].append(dict(key=key, x=x, y=y, title=title, body=body, kind=kind, w=w, h=h))


def edge(g, source, target, start="right", end="left", via=(), label="", at=None, optional=False):
    g["edges"].append(dict(source=source, target=target, start=start, end=end,
                           via=via, label=label, at=at, optional=optional))


def diagrams():
    result = []
    g=graph("01-compact-researcher", "One generation agent", "Baseline: one configured LLM proposes, writes and interprets; code measures and accounts.")
    for args in [
        ("task",2.5,3.1,"Mission","Comparator + constraints"),
        ("agent",7.5,3.1,"One LLM agent","User-selected endpoint + model","llm"),
        ("run",12.5,3.1,"Experiment tool","Qualified domain adapter","code"),
        ("evidence",17.5,3.1,"Measured receipts","Source, counts and costs","evidence"),
        ("decision",7.5,6.2,"Optional decision call","LLM-only / active / shadow","optional"),
        ("budget",12.5,6.2,"Budget and eligibility","Continue candidate research?","code"),
        ("confirm",17.5,6.2,"Reserved confirmation","Fixed candidate; no feedback","code"),
        ("out",17.5,9.2,"Candidate + evidence","Include failures and limits")]:
        node(g,*args)
    for a,b in [("task","agent"),("agent","run"),("run","evidence")]:edge(g,a,b)
    edge(g,"evidence","budget","bottom","top",via=((17.5,4.75),(12.5,4.75)))
    edge(g,"budget","agent","left","bottom",via=((7.5,6.2),),label="development",at=(9.4,5.85))
    edge(g,"agent","decision","bottom","top",optional=True)
    edge(g,"decision","agent","left","left",via=((5.25,6.2),(5.25,3.1)),label="resume",at=(5.25,4.65),optional=True)
    edge(g,"budget","confirm",label="if reserved",at=(15,5.85))
    edge(g,"confirm","out","bottom","top")
    result.append(g)

    g=graph("02-shared-model-mas", "Parallel teams, one shared generation model", "Distinct contexts and approaches; bounded children and dependency-wave concurrency.")
    node(g,"user",3,3,"User-selected design","A / B / C / D / E / F")
    node(g,"runtime",10,3,"Bounded scheduler","Ready waves + shared budgets","code",w=4.1)
    node(g,"model",17,3,"Configured generation model","One model fills all roles","llm",w=4.1)
    for key,x,title in [("a",3,"Prime A"),("b",10,"Prime B"),("c",17,"Prime N")]:
        node(g,key,x,6,title,"Own approach + context\nOptional children 0..K, depth D","llm",w=4.2,h=1.6)
        edge(g,"runtime",key,"bottom","top",via=((10,4.4),(x,4.4)) if key!="b" else ())
    node(g,"sharing",10,9.3,"Barrier + filtered Markdown","none / low / intermediate / high\nWisdom alone or with detail","evidence",w=5.0,h=1.6)
    node(g,"receipts",17,9.3,"Experiment receipts","Qualified local evaluator","evidence",w=4.2)
    edge(g,"user","runtime");edge(g,"runtime","model")
    for key in ("a","b"):edge(g,key,"sharing","bottom","top",via=((next(n["x"] for n in g["nodes"] if n["key"]==key),7.7),(10,7.7)))
    edge(g,"c","receipts","bottom","top")
    edge(g,"sharing","runtime","left","left",via=((6.6,9.3),(6.6,3)),label="next permitted phase",at=(6.6,7.1))
    result.append(g)

    g=graph("03-optional-decisions", "Optional specialist decision routing", "User-configured chat or typed JSON endpoints; separate accounts and model choices.")
    node(g,"agent",2.5,3.2,"LLM episode","Prime or child","llm")
    node(g,"tool",7.5,3.2,"decision.assess","Scope + spec + inherited budget","code")
    node(g,"router",12.5,3.2,"Configured mode","llm_only / shadow / selected_active","code",w=4.2)
    node(g,"same",7.5,6.7,"Same generation LLM","LLM-only or logged fallback","llm",w=4.0)
    node(g,"chat_judge",12.5,6.7,"Chat decision adapter","Bounded JSON judgment","optional",w=4.0)
    node(g,"typed_judge",17.5,6.7,"Typed decision adapter","Separate key, endpoint and model","optional",w=4.0)
    node(g,"validate",12.5,9.7,"Validate + record answer","Typed result and actual usage","code",w=4.2)
    node(g,"resume",17.5,9.7,"Resume same episode","Continue generation/tool work","llm",w=4.0)
    edge(g,"agent","tool");edge(g,"tool","router")
    edge(g,"router","same","left","top",via=((10.1,3.2),(10.1,5.2),(7.5,5.2)),label="LLM-only",at=(8.5,5.2))
    edge(g,"router","chat_judge","bottom","top",label="eligible",at=(12.5,4.95),optional=True)
    edge(g,"router","typed_judge","right","top",via=((17.5,3.2),),label="selected provider",at=(17.5,4.9),optional=True)
    edge(g,"same","validate","bottom","left",via=((7.5,9.7),))
    edge(g,"chat_judge","validate","bottom","top",label="active result",at=(12.5,8.3),optional=True)
    edge(g,"typed_judge","validate","bottom","top",via=((17.5,8.4),(12.5,8.4)),optional=True)
    edge(g,"validate","resume")
    g["footer"]="Shadow specialist results stay hidden from acting agents. No specialist certifies scientific truth."
    result.append(g)

    g=graph("04-scientific-lifecycle", "Research evidence and confirmation", "Iterate on a candidate; preserve independent calibration, scored cases and a final evidence boundary.")
    for args in [
        ("mission",2.5,3.1,"Define useful improvement","Comparator + metrics + constraints"),
        ("hyp",7.5,3.1,"Competing approaches","Hypotheses + falsifiers","llm"),
        ("experiment",12.5,3.1,"Build and evaluate","Qualified bounded experiment","code"),
        ("receipt",17.5,3.1,"Evidence + failures","Counts, uncertainty and source","evidence"),
        ("revise",12.5,6.5,"Interpret and revise","Development feedback only","llm"),
        ("fix",7.5,9.6,"Fix candidate source","Before confirmation","code"),
        ("confirm",12.5,9.6,"Independent confirmation","Fresh separate calibration panel","code",4.2),
        ("artifact",17.5,9.6,"Candidate + evidence","Scope, costs and unresolved cases")]:
        node(g,*args)
    edge(g,"mission","hyp");edge(g,"hyp","experiment");edge(g,"experiment","receipt")
    edge(g,"receipt","revise","bottom","right",via=((17.5,6.5),))
    edge(g,"revise","hyp","left","bottom",via=((7.5,6.5),),label="within budget",at=(9.8,6.1))
    edge(g,"revise","fix","bottom","top",via=((12.5,8),(7.5,8)),label="declared selection",at=(10,8))
    edge(g,"fix","confirm");edge(g,"confirm","artifact")
    g["footer"]="Confirmation never fits thresholds on scored cases or returns feedback to the acting agents."
    result.append(g)

    g=graph("05-standalone-components", "Standalone repository and workspace", "The independent teamknitt package owns its implementation and ships wheel-ready starter resources.")
    for args in [
        ("package",3,3,"teamknitt Python package","CLI + schemas + study runner","code",4.2),
        ("init",10,3,"Workspace initializer","Bundled presets + examples","code",4.2),
        ("workspace",17,3,"User workspace","Editable designs, study and mission","artifact",4.2),
        ("provider",3,6.4,"Generation + decision adapters","Configured generation and decisions","optional",4.2),
        ("orchestrate",10,6.4,"Study orchestration","Contexts, budgets and barriers","code",4.2),
        ("domain",17,6.4,"Qualified domain adapter","Separate sandboxed policy worker","code",4.2),
        ("config",3,9.5,"User choices","Style, sharing, models, statistics","artifact",4.2),
        ("evidence",10,9.5,"Trial evidence","Plans, events, receipts and costs","evidence",4.2),
        ("private",17,9.5,"Private local inputs","Fresh seed panels; no shipped data","evidence",4.2)]:
        node(g,*args)
    edge(g,"package","init");edge(g,"init","workspace")
    edge(g,"workspace","orchestrate","bottom","top",via=((17,4.7),(10,4.7)))
    edge(g,"provider","orchestrate");edge(g,"orchestrate","domain")
    edge(g,"orchestrate","evidence","bottom","top")
    edge(g,"private","domain","top","bottom")
    edge(g,"config","orchestrate","top","left",via=((3,8.1),(7.5,8.1),(7.5,6.4)))
    g["footer"]="No legacy parent imports, CLI, image or source. Credentials and private seeds stay outside public Git."
    result.append(g)

    g=graph("06-integrated-lab", "Integrated configurable discovery lab", "Current bounded execution, plus clearly marked future asset services.",width=20,height=18,direction="TB")
    for args in [
        ("setup",10,2.8,"Mission + user-selected Markdown lab","A silos / B integrated / C co-leaders / D hub / E flat / F single\nAdjust personas, children, sharing, statistics and budgets","artifact",9.8,1.5),
        ("control",10,5.1,"Controller + bounded scheduler","Dependency waves, accounting and confirmation reserve","code",5.2,1.5),
        ("admin",3.5,5.1,"User / administration","Outside the research generator","artifact",4.2),
        ("model",16.5,5.1,"One generation model","User-selected endpoint + model","llm",4.2),
        ("a",3.5,7.9,"Prime A + optional children","Distinct approach; bounded depth","llm",4.2,1.5),
        ("b",10,7.9,"Prime B + optional children","Distinct approach; inherited budgets","llm",4.2,1.5),
        ("n",16.5,7.9,"Prime N + optional children","Own context; configurable count","llm",4.2,1.5),
        ("decision",3.5,10.8,"Agent-local decision tool","LLM-only / active / shadow\nShared budgets and per-backend usage","optional",4.5,1.6),
        ("sharing",10,10.8,"Barrier + recipient-filtered MD","none / low / intermediate / high\nwisdom alone or alongside detail","evidence",4.6,1.6),
        ("execute",16.5,10.8,"Qualified experiment adapter","Trusted evaluator; separate policy sandbox\nCounts, intervals, memory and cost","code",4.6,1.6),
        ("output",3.5,14,"Candidate + evidence package","Source, recipe, limits and failures","artifact",4.4,1.5),
        ("confirm",10,14,"Reserved confirmation","Fixed candidate; fresh clean calibration\nNo return to acting agents","code",4.6,1.5),
        ("evidence",16.5,14,"Saved measured receipts","Source/model/input identity; failures","evidence",4.4,1.5),
        ("future",10,16.5,"General integration and asset registry","Planned services; no automatic organizational redesign","future",8.0,1.2)]:
        node(g,*args)
    edge(g,"setup","control","bottom","top")
    edge(g,"admin","control");edge(g,"control","model")
    for key,x in [("a",3.5),("b",10),("n",16.5)]:
        edge(g,"control",key,"bottom","top",via=((10,6.4),(x,6.4)) if key!="b" else ())
    edge(g,"a","decision","bottom","top",optional=True)
    edge(g,"b","sharing","bottom","top")
    edge(g,"n","execute","bottom","top")
    edge(g,"a","sharing","right","top",via=((6,7.9),(6,9.3),(10,9.3)))
    edge(g,"b","execute","right","left",via=((12.6,7.9),(12.6,10.8)))
    edge(g,"sharing","b","left","left",via=((7.2,10.8),(7.2,7.9)),label="next phase",at=(7.2,9.3))
    edge(g,"execute","evidence","bottom","top")
    edge(g,"evidence","confirm","left","right")
    edge(g,"confirm","output","left","right")
    edge(g,"output","future","bottom","left",via=((3.5,16.5),),optional=True)
    result.append(g)

    g=graph("07-agent-decision-loop", "Decision model inside the same LLM process", "Prime or child yields for a compatible decision, then resumes its own work.",height=12)
    for args in [
        ("agent",2.5,3,"Prime / child LLM","Own task and caller-visible evidence","llm"),
        ("tool",7.5,3,"decision.assess","Bounded question + typed spec","code"),
        ("check",12.5,3,"Scope and budget checks","No hidden peer context","code"),
        ("router",17.5,3,"Configured routing","LLM-only / shadow / active","code"),
        ("same",7.5,6.5,"Same configured LLM","Default or logged fallback","llm"),
        ("chat_judge",12.5,6.5,"Configured specialist","Configured chat or typed endpoint","optional"),
        ("shadow",17.5,6.5,"Private shadow receipt","Hidden from acting context","evidence"),
        ("validated",7.5,9.6,"Validate typed answer","Record source and usage","code"),
        ("resume",2.5,9.6,"Same agent resumes","Next permitted action","llm")]:
        node(g,*args)
    edge(g,"agent","tool");edge(g,"tool","check");edge(g,"check","router")
    edge(g,"router","chat_judge","bottom","top",via=((17.5,4.6),(12.5,4.6)),optional=True)
    edge(g,"check","same","bottom","top",via=((12.5,4.9),(7.5,4.9)))
    edge(g,"chat_judge","same","left","right",label="logged fallback",at=(10,6.15),optional=True)
    edge(g,"chat_judge","shadow",label="shadow only",at=(15,6.15),optional=True)
    edge(g,"same","validated","bottom","top")
    edge(g,"chat_judge","validated","bottom","right",via=((12.5,9.6),),optional=True)
    edge(g,"validated","resume","left","right")
    edge(g,"resume","agent","left","left",via=((.4,9.6),(.4,3)))
    g["footer"]="Only this episode yields; other ready tasks continue. An unavailable answer remains explicit."
    result.append(g)

    g=graph("08-horizontal-lab", "teamknitt lab — mission to measured output", "User-selected organization; parallel research; local measurements; protected confirmation.",width=30,height=10)
    for args in [
        ("setup",2.5,3.4,"Choose mission + lab","Six editable Markdown styles","artifact",4.15),
        ("control",7.5,3.4,"Orchestrate","Dependencies + global budgets","code",4.15),
        ("teams",12.5,3.4,"Configured researchers","One scientist or bounded teams","llm",4.15),
        ("run",17.5,3.4,"Execute and measure","Qualified local sandbox + evaluator","code",4.15),
        ("confirm",22.5,3.4,"Confirm candidate","Reserved; no agent feedback","code",4.15),
        ("out",27.5,3.4,"Candidate + receipts","Measured tradeoffs and limits","artifact",4.15),
        ("user",2.5,6.9,"User / administration","Selects and changes settings","artifact",4.15,1.6),
        ("settings",7.5,6.9,"Recorded configuration","Models, counts, depth and budgets\nNo automatic redesign","evidence",4.15,1.6),
        ("sharing",12.5,6.9,"Horizontal Markdown","none / low / intermediate / high\nwisdom alone or with detail","evidence",4.15,1.6),
        ("decision",17.5,6.9,"Optional local decisions","LLM → decision endpoint → LLM\nShared budgets and per-backend usage","optional",4.15,1.6),
        ("stats",22.5,6.9,"User-selected statistics","CP95 counts; explicit-prior intervals\nDomain-owned analysis","code",4.15,1.6),
        ("future",27.5,6.9,"General asset lifecycle","Integration and registry planned","future",4.15,1.6)]:
        node(g,*args)
    for a,b in [("setup","control"),("control","teams"),("teams","run"),("run","confirm"),("confirm","out")]:edge(g,a,b)
    for a,b in [("user","setup"),("settings","control"),("sharing","teams"),("decision","run"),("stats","confirm")]:
        edge(g,a,b,"top","bottom",optional=a=="decision")
    edge(g,"out","future","bottom","top",optional=True)
    edge(g,"run","control","bottom","bottom",via=((17.5,5.1),(7.5,5.1)),label="development evidence → candidate refinement",at=(12.5,5.1))
    result.append(g)

    g=graph("09-memory-policy", "Memory-policy research and sandbox boundary", "Retention-only v1: fixed distance scorer, matched instances, independent complete-run evaluation.",width=24,height=13)
    for args in [
        ("generation",3,3.2,"Model authors policy source","Configured model + actor provenance","llm",4.5),
        ("validate",9,3.2,"Source/API validation","select(bank, ages, new, t, capacity, aux)","code",4.8),
        ("supervisor",15,3.2,"Trusted supervisor","Score current x against OLD bank","code",4.6),
        ("worker",21,3.2,"OS-sandboxed policy","Causal x,t; retained indices + aux\nNo labels, seeds or future","code",4.8,1.65),
        ("chat_judge",3,7,"Optional decision backend","Configured chat or typed endpoint","optional",4.5),
        ("panels",9,7,"Private scenario panels","Clean calibration / benign / fault\nDevelopment separate from confirmation","evidence",4.8,1.65),
        ("metrics",15,7,"Independent-run evaluation","Any-alarm rate, fault recall, recurrence\nCP95 / supported count intervals","code",4.8,1.65),
        ("receipts",21,7,"Actual experiment receipts","Source hash, counts, state, RSS and time","evidence",4.8),
        ("feedback",3,10.5,"Development feedback","Within declared research budget","evidence",4.5),
        ("output",15,10.5,"Source + evidence + limits","Include failed / inconclusive outcomes","artifact",4.8),
        ("confirm",21,10.5,"One reserved confirmation","Fixed source; fresh clean calibration\nNever feedback to the acting agents","code",4.8,1.65)]:
        node(g,*args)
    edge(g,"generation","validate");edge(g,"validate","supervisor");edge(g,"supervisor","worker",label="causal input",at=(18,2.8))
    edge(g,"worker","supervisor","bottom","bottom",via=((21,5.1),(15,5.1)),label="retained indices + aux",at=(18,5.1))
    edge(g,"panels","supervisor","top","left",via=((9,5.1),(12.4,5.1),(12.4,3.2)))
    edge(g,"supervisor","metrics","bottom","top")
    edge(g,"metrics","receipts")
    edge(g,"generation","chat_judge","bottom","top",optional=True)
    edge(g,"chat_judge","generation","left","left",via=((.4,7),(.4,3.2)),optional=True)
    edge(g,"receipts","feedback","bottom","top",via=((21,8.7),(3,8.7)),label="development only",at=(9,8.7))
    edge(g,"feedback","generation","left","left",via=((.15,10.5),(.15,3.2)))
    edge(g,"receipts","confirm","bottom","top")
    edge(g,"confirm","output","left","right")
    g["footer"]="Numeric policy state ≤ 3,520 bytes in the default profile. Process RSS is separate. No perpetual-run guarantee."
    result.append(g)
    g=graph("10-lab-observatory", "Optional lab observatory — two local agents", "The user opts into a local web view of the chosen setup and observed computation.",width=24,height=12)
    for args in [
        ("plan",3,3.2,"User-selected lab plan","Design, personas, sharing and budgets","artifact",4.8),
        ("setup",10,3.2,"Agent 1: setup visualizer","Resolve process and team maps","code",5.0),
        ("page",20,5.7,"Local web observatory","Workflow / team / activity / inspect\nLive updates or offline HTML snapshot","artifact",5.0,1.7),
        ("runner",3,7.2,"teamknitt research runtime","User-authorized study execution","code",4.8),
        ("activity",10,7.2,"Metadata + heartbeat","Nodes, actors, request/evaluation bounds","evidence",5.0),
        ("observer",10,10.0,"Agent 2: runtime observer","Correlate activity; mark stale/failed work","code",5.0),
    ]:
        node(g,*args)
    edge(g,"plan","setup")
    edge(g,"setup","page","right","top",via=((20,3.2),))
    edge(g,"runner","activity")
    edge(g,"activity","observer","bottom","top")
    edge(g,"observer","page","right","bottom",via=((20,10.0),))
    g["footer"]="Both agents are read-only and make no model calls. No prompts, answers, source, seeds or research measurements enter the view."
    result.append(g)
    g=graph("11-single-scientist", "Single scientist — user-selected persistence and sequences", "Design F: one scientist, continued working context by default, finite effort and shared resource limits.",width=24,height=13)
    for args in [
        ("choices",3,3.3,"User-selected effort","Low 1 / medium 3 / persistent 6\nOr persistent to budget allowance","artifact",4.8,1.65),
        ("scientist",10,3.3,"One scientist","Investigate, implement and interpret\nNo peer teams or delegated children","llm",5.0,1.65),
        ("tools",17,3.3,"Permitted tools + evidence","Development receipts and failures","code",5.0,1.65),
        ("budget",3,7.1,"Shared study budgets","Requests, time and evaluations\nNo replenishment at sequence changes","code",4.8,1.65),
        ("review",10,7.1,"Next investigative pass","Audit, test, revise, try alternatives","llm",5.0,1.65),
        ("boundary",17,7.1,"Pass / sequence boundary","Run selected sequences in order (1..N)\nContinue the same context by default","code",5.0,1.65),
        ("confirm",17,10.6,"One final confirmation","After all development; no agent feedback","code",5.0,1.65),
        ("out",10,10.6,"Candidate + saved evidence","Execution end is separate from validity","artifact",5.0,1.65),
    ]:
        node(g,*args)
    edge(g,"choices","scientist");edge(g,"scientist","tools")
    edge(g,"tools","boundary","bottom","top")
    edge(g,"boundary","review","left","right",label="more passes / sequences",at=(13.5,6.85))
    edge(g,"budget","review",label="check before requests",at=(6.5,6.85))
    edge(g,"review","scientist","top","bottom")
    edge(g,"boundary","confirm","bottom","top",label="development ends",at=(17,8.85))
    edge(g,"confirm","out","left","right")
    g["footer"]="All sequences share the user's budgets. Controlled allowance stops do not certify a solved mission. No automatic lab redesign."
    result.append(g)
    g=graph("12-multi-lab", "Multiple labs — research, meetings and selected sequences", "The user chooses the same or different designs, inter-lab sharing, meeting type and sequence count.",width=24,height=13)
    for args in [
        ("choices",3,3.3,"User-selected collection","Lab variants, representatives and N sequences","artifact",4.8,1.65),
        ("lab1",10,3.3,"Lab 1 / selected design","Own histories, agents and evidence","llm",4.8,1.65),
        ("lab2",10,7,"Lab 2..N / selected designs","Same or different designs; separate context","llm",4.8,1.65),
        ("sharing",17,3.3,"Filtered lab exchange","None / low / intermediate / high\nOptional conditional wisdom","code",5,1.65),
        ("meeting",17,7,"Conference / symposium","Presentations; optional discussion rounds\nSame inter-lab restrictions apply","llm",5,1.65),
        ("budget",3,7,"Group and per-lab limits","Requests and wall time across all sequences\nBounded labs, requests and experiments","code",4.8,1.65),
        ("next",10,10.6,"User-selected next sequence","Carry own context + permitted peer views\nStop after the chosen sequence count","code",5,1.65),
        ("confirm",17,10.6,"Per-lab final confirmation","After every sequence and meeting\nNo confirmation feedback to agents","code",5,1.65),
        ("out",3,10.6,"Lab evidence + proceedings","Retain limits, failures and admitted views","artifact",4.8,1.65),
    ]:
        node(g,*args)
    edge(g,"choices","lab1")
    edge(g,"choices","lab2","bottom","left",via=((3,4.8),(6.4,4.8),(6.4,7)))
    edge(g,"lab1","sharing")
    edge(g,"lab2","sharing","right","left",via=((13.2,7),(13.2,3.3)))
    edge(g,"sharing","meeting","bottom","top")
    edge(g,"meeting","next","bottom","right",via=((17,9),(13.5,9),(13.5,10.6)))
    edge(g,"budget","next","right","left",via=((6.4,7),(6.4,10.6)))
    edge(g,"next","lab2","top","bottom",label="continue within N",at=(10,9.1),optional=True)
    edge(g,"next","lab1","left","left",via=((6.9,10.6),(6.9,3.3)),optional=True)
    edge(g,"next","confirm",label="all sequences end",at=(13.5,10.3))
    edge(g,"confirm","out","bottom","bottom",via=((17,12),(3,12)))
    g["footer"]="Meetings are operational only when research sharing is disabled. No automatic lab winner, redesign or extra sequence."
    result.append(g)
    g=graph("13-teamknitt-system", "teamknitt — team configuration and runtime", "User-selected tasks and topology; own bounded engine; Non-system/System explanations differ from emergence forms and process/state/outcome evidence.",width=24,height=13)
    g.update(brand="TEAMKNITT", date="2026-11-09")
    for args in [
        ("baseline",3,3.2,"User-directed team configuration","Task / brainstorm / goal\nTopology, members and communication","artifact",4.8,1.65),
        ("backbone",10,3.2,"Standalone teamknitt engine","Own scheduler, adapters and resources\nExplicit models, tools and finite budgets","artifact",5.0,1.65),
        ("temporal",17,3.2,"Non-system / System views","Member reports / differentiated interaction\nSeparate emergence and process/state axes","optional",5.0,1.65),
        ("roles",3,6.8,"Chosen members and connections","Complementary responsibilities and inputs\nExplicit directed routes; no implied authority","llm",4.8,1.65),
        ("reps",10,6.8,"External representations","Complementary sources; shared workspaces\nExplicit readers, writers and provenance","evidence",5.0,1.65),
        ("work",17,6.8,"Work and coordination","Task structure, handoffs and timework\nCapability-conditioned action opportunities","code",5.0,1.65),
        ("authority",3,10.3,"Explicit execution authority","User-selected tools, providers and limits\nNo automatic changes or budget increases","artifact",4.8,1.65),
        ("runtime",10,10.3,"Task execution and monitoring","Scoped frames and versioned contributions\nRead-only metadata; explicit operator commands","code",5.0,1.65),
        ("record",17,10.3,"Contributions for user review","Visible process is not goal achievement\nNo automatic winner or organization change","evidence",5.0,1.65),
    ]:
        node(g,*args)
    edge(g,"baseline","backbone");edge(g,"backbone","temporal",optional=True)
    for key,x in [("roles",3),("reps",10),("work",17)]:
        edge(g,"backbone",key,"bottom","top",via=((10,4.9),(x,4.9)) if key!="reps" else ())
    edge(g,"temporal","work","bottom","right",via=((20.5,4.6),(20.5,6.8)),optional=True)
    for key,x in [("roles",3),("reps",10),("work",17)]:
        edge(g,key,"runtime","bottom","top",via=((x,8.6),(10,8.6)) if key!="reps" else ())
    edge(g,"authority","runtime");edge(g,"runtime","record")
    g["footer"]="Based on Labtune; research follow-up to Goran Mitevski’s 2022/2023 work. Pioneertown B.V.; Teamknitt Noncommercial Licence 1.0; see LICENSE."
    result.append(g)

    g=graph("14-teamknitt-protocol", "From a user brief to observable team contributions", "Configure or draft explicitly; route information by topology and sharing; keep completion separate from user-goal achievement.",width=24,height=14)
    g.update(brand="TEAMKNITT", date="2026-11-09")
    for args in [
        ("sources",3,3.3,"User brief and task context","Task, brainstorming prompt or goal\nComplementary inputs are optional","artifact",4.8,1.65),
        ("actor",10,3.3,"Actor's permitted observation","Own responsibilities and representations\nCapabilities + available action opportunities","llm",5.0,1.65),
        ("produce",17,3.3,"Externalize a contribution","Bounded notes with input provenance\nNo unrestricted code or external execution","code",5.0,1.65),
        ("control",3,7,"Team choices + engine bounds","Topology and sharing filter exposure\nModels, tools and budgets stay explicit","artifact",4.8,1.65),
        ("barrier",10,7,"Dependency-wave barrier","Validate all publications before commit\nImmutable representation versions","code",5.0,1.65),
        ("consumer",17,7,"Another role's later observation","Permitted representation exposure\nVersion-specific handoff acknowledgement","llm",5.0,1.65),
        ("viewer",3,11,"Configure, monitor and review","Draft previews do not write or run models\nPrivate deliverable; user reviews the result","artifact",4.8,1.65),
        ("record",10,11,"Distinct process observations","Available / exposed / published / acknowledged\nExplicit reports, freshness and missingness","evidence",5.0,1.65),
        ("timework",17,11,"Additional observation tools","Complexity science + team dynamics\nAttractors / synchrony / fractals not estimated","optional",5.0,1.65),
    ]:
        node(g,*args)
    edge(g,"sources","actor");edge(g,"actor","produce")
    edge(g,"produce","barrier","bottom","top",via=((17,5.4),(10,5.4)))
    edge(g,"control","barrier");edge(g,"barrier","consumer")
    edge(g,"consumer","timework","bottom","top")
    edge(g,"barrier","record","bottom","top")
    edge(g,"timework","record","left","right",optional=True)
    edge(g,"record","viewer","left","right")
    edge(g,"consumer","actor","right","top",via=((21,7),(21,2.3),(10,2.3)),label="next work phase",at=(21,5.7))
    g["footer"]="Availability is not comprehension. Acknowledgement is not agreement. Similarity is not accuracy. Human-team constructs require validation."
    result.append(g)
    g=graph("15-teamknitt-views", "Team views: non-system and system explanations", "Explanatory locus is not the same axis as compositional/compilational emergence or process/state/outcome evidence.",width=30,height=18)
    g.update(brand="TEAMKNITT", date="2026-11-09")
    node(g,"user",15,3,"Your task and chosen configuration","Explicit membership, roles, topology, sharing, models, tools and budgets","artifact",23,1.5)
    node(g,"non_system",7,6,"NON-SYSTEM — member/component-centered","Attributes, behavior, knowledge, reports and aggregates\nIPO/IMOI also includes interaction, feedback and conditional relations","artifact",12.7,1.7)
    node(g,"system",22.5,6,"SYSTEM — situated interaction/configuration","Work across members, artifacts, tools and time\nNot synonymous with complexity science or demonstrated emergence","artifact",13.2,1.7)
    node(g,"behavior",4,9.2,"Collaborative intelligence","Member-focused behavioral evaluation\nOptional separate saved protocol\nNot an official CIB score","optional",5.5,1.95)
    node(g,"models",10,9.2,"Shared models + reports","Explicit plans and perceived alignment\nSimilarity is not accuracy\nNo latent mental-model inference","evidence",5.5,1.95)
    node(g,"distributed",19,9.2,"Distributed problem-solving","Complementary inputs and representations\nWork dependencies + transformations\nHutchins / McNeese, Salas & Endsley","evidence",6.3,1.95)
    node(g,"transactive",26,9.2,"Transactive memory","Differentiated/compilational knowledge\nConfigured directory: who is assigned what\nNot measured retrieval effectiveness","evidence",6.3,1.95)
    node(g,"coordination",19,12.3,"Interactive cognition + coordination","Situated interaction, not aggregated minds\nExposure and version-specific handoffs\nCooke et al.; no understanding inferred","evidence",6.3,1.95)
    node(g,"dynamics",26,12.3,"Teams as dynamical systems","Local–global / substrate / cross-level\nDistributed creative processes\nAttractors / synchrony / fractals not estimated","optional",6.3,1.95)
    node(g,"engine",15,15.5,"Configuration, tasks, monitoring and interventions","Standalone bounded engine; human-directed interventions, not automatic organizational improvement\nHuman-team constructs and effects require validation for AI teams; psychological states are not measured","code",28,1.65)
    edge(g,"user","non_system","bottom","top",via=((15,4.6),(7,4.6)))
    edge(g,"user","system","bottom","top",via=((15,4.6),(22.5,4.6)))
    for key,x in [("behavior",4),("models",10)]:edge(g,"non_system",key,"bottom","top",via=((7,7.5),(x,7.5)))
    for key,x in [("distributed",19),("transactive",26)]:edge(g,"system",key,"bottom","top",via=((22.5,7.5),(x,7.5)))
    edge(g,"system","coordination","left","left",via=((15.1,6),(15.1,12.3)))
    edge(g,"system","dynamics","right","right",via=((29.5,6),(29.5,12.3)))
    g["footer"]="Background: Research and Theory on Human Teams · 9 Nov 2026 · @Goran. Based on Labtune / Pioneertown B.V.; Teamknitt Noncommercial Licence 1.0."
    result.append(g)

    g=graph("16-teamknitt-intervention", "Configuration, tasks, monitoring and interventions", "Human-team research informs the design; user choice, operational records and independently reviewed outcomes remain distinct.",width=28,height=14)
    g.update(brand="TEAMKNITT", date="2026-11-09")
    for args in [
        ("configure",3.5,3.4,"01 / Configure","Members, roles, topology and sharing\nExplicit models, tools, delegation and bounds","artifact",5.8,1.8),
        ("tasks",10.5,3.4,"02 / Set tasks","Brief, sources and useful deliverable\nSuccess criteria and review boundary","artifact",5.8,1.8),
        ("follow",17.5,3.4,"03 / Follow work","Member reports + system organization\nProcesses are not psychological states","evidence",5.8,1.8),
        ("intervene",24.5,3.4,"04 / Intervene","Human selects intended scope\nPreview first; explicit CLI --apply","artifact",5.8,1.8),
        ("conditions",3.5,7.3,"Between runs / conditions","Reviewed role/task/procedure changes\nBackup + shared run lock; no auto redesign","code",5.8,1.8),
        ("planned",10.5,7.3,"Before run / planned gap","Actor, representation or directed link\nChosen wave + duration; not weight training","optional",5.8,1.8),
        ("control",17.5,7.3,"During run / safe boundary","Private feedback; pause / resume / stop\nCurrent-wave work may finish","code",5.8,1.8),
        ("review",24.5,7.3,"After / human outcome review","Partial or complete contributions\nInput/process change is not improved outcome","evidence",5.8,1.8),
        ("basis",7,11.1,"Research background","Research follow-up / conditions / shared knowledge / training\nDistinct mechanisms and levels; no inferred causal improvement","optional",12,1.8),
        ("bounds",21,11.1,"Limits and audit remain explicit","Pause keeps deadline and counters; stop is terminal\nQueued ≠ applied ≠ context assembled ≠ understood ≠ improved","code",12,1.8),
    ]:node(g,*args)
    for source,target in [("configure","tasks"),("tasks","follow"),("follow","intervene")]:edge(g,source,target)
    for source,target in [("configure","conditions"),("tasks","planned"),("follow","control"),("intervene","review")]:edge(g,source,target,"bottom","top")
    edge(g,"conditions","basis","bottom","top",via=((3.5,9.3),(7,9.3)))
    edge(g,"planned","basis","bottom","top",via=((10.5,9.3),(7,9.3)))
    edge(g,"control","bounds","bottom","top",via=((17.5,9.3),(21,9.3)))
    edge(g,"review","bounds","bottom","top",via=((24.5,9.3),(21,9.3)))
    g["footer"]="Browser: read-only metadata + command preparation. No model, permission, statistics or budget changes; no automatic recovery or team improvement."
    result.append(g)
    g=graph("17-teamknitt-multiple-teams", "Multiple teams and communication", "One shared task; explicit independent configurations, optional directed exchange and a finite all-team budget.",width=28,height=14)
    g.update(brand="TEAMKNITT", date="2026-11-09")
    node(g,"task",14,3,"Shared task and review criteria","One authoritative brief and immutable task snapshot; goal achievement is not inferred","artifact",24,1.5)
    for key,x,title in [("alpha",4,"Team alpha"),("beta",14,"Team beta"),("gamma",24,"Team gamma")]:
        node(g,key,x,6.5,title,"Own members, roles, topology and sharing\nOwn explicit model and local limits\nUser-authored context; URL references only","llm",7.6,2.0)
        edge(g,"task",key,"bottom","top",via=((14,4.6),(x,4.6)) if key!="beta" else ())
    edge(g,"alpha","beta",label="only if configured",at=(9,6.15),optional=True)
    node(g,"limits",7.5,10.5,"All-team limits and scoped controls","One shared request counter, wall deadline and concurrency cap\nPer-team limits also apply; pause/resume resets no allowance\nNo budget multiplication, model selection or automatic winner","code",13,2.2)
    node(g,"exchange",22,10.5,"Optional prior-wave exchange","Designated-member summaries or contributions only\nDirected links; bounded text; no raw private-artifact export\nDisconnected components have no exchange/barrier dependency","evidence",11,2.2)
    edge(g,"alpha","limits","bottom","top",via=((4,8.3),(7.5,8.3)))
    edge(g,"beta","exchange","bottom","top",via=((14,8.3),(22,8.3)),optional=True)
    edge(g,"gamma","limits","bottom","right",via=((24,8.8),(15,8.8),(15,10.5)))
    g["footer"]="External skills/prompts/configuration/code/CLIs are not imported. Default output is reviewable text/code proposals, not verified execution or merging."
    result.append(g)
    return result


# Canonical labels, captions and layout geometry for the runtime topology diagrams.
TEAM_TOPOLOGIES = {
    "fully_connected": {"label": "Fully connected", "description": "Every member can send permitted information to every other member."},
    "hub_and_spoke": {"label": "Hub and spoke", "description": "Member 1 is the two-way communication hub; spokes exchange through it."},
    "ring": {"label": "Ring · two-way", "description": "Each member connects to its two neighbors in a bidirectional ring."},
    "hierarchical": {"label": "Hierarchical routing", "description": "A bidirectional binary-tree communication layout; it does not grant decision authority."},
    "chain": {"label": "Chain · two-way", "description": "Adjacent member IDs exchange in both directions along a path, without a closing loop."},
    "directed_chain": {"label": "Chain · one-way", "description": "Information can flow from member 1 toward the last member, one adjacent hop at a time; no reverse links."},
    "directed_ring": {"label": "Ring · one-way", "description": "Each member sends to the next member, with the last sending to member 1; reverse links are not implied."},
    "wheel": {"label": "Wheel", "description": "Member 1 is a two-way hub; the remaining members also form a bidirectional outer ring."},
    "grid": {"label": "Grid", "description": "A row-major near-square grid with two-way horizontal and vertical neighbors, no diagonals or wraparound."},
    "clustered": {"label": "Clustered pods", "description": "Consecutive groups of up to three members are fully connected; each pod's first member links bidirectionally to the next pod's first member."},
    "bipartite": {"label": "Bipartite", "description": "The first ceil(N/2) members connect bidirectionally to all remaining members; no within-partition links."},
    "broadcast": {"label": "Broadcast · one-to-many", "description": "Member 1 can send to every other member; no replies or spoke-to-spoke routes are implied."},
    "gather": {"label": "Gather · many-to-one", "description": "Every other member can send to member 1; no return or spoke-to-spoke routes are implied."},
    "custom": {"label": "Custom directed links", "description": "Only the explicitly declared directed links exist; reverse links are not implied."},
}


def team_topology_layout(kind, count):
    """Normalized routing positions, not inferred influence or decision authority."""
    import math
    if type(count) is not int or not 1 <= count <= 16 or kind not in TEAM_TOPOLOGIES:
        raise ValueError("Unsupported topology layout")
    result = []
    for i in range(count):
        if count == 1:
            x, y = .5, .5
        elif kind in {"hub_and_spoke", "wheel", "broadcast", "gather"} and i == 0:
            x, y = .5, .5
        elif kind == "hierarchical":
            level = (i + 1).bit_length() - 1
            offset = i - (2**level - 1)
            levels = count.bit_length()
            x, y = (offset + 1) / (2**level + 1), .12 + .76 * level / max(1, levels - 1)
        elif kind in {"grid", "chain", "directed_chain"}:
            cols = math.ceil(math.sqrt(count)) if kind == "grid" else min(4, count)
            rows = math.ceil(count / cols)
            row, col = divmod(i, cols)
            if kind != "grid" and row % 2:
                col = cols - 1 - col
            x = .12 + .76 * col / (cols - 1) if cols > 1 else .5
            y = .14 + .70 * row / (rows - 1) if rows > 1 else .5
        elif kind == "bipartite":
            split = (count + 1) // 2
            left = i < split
            size, offset = (split, i) if left else (count - split, i - split)
            x = .25 if left else .75
            y = .12 + .76 * offset / (size - 1) if size > 1 else .5
        elif kind == "clustered" and count > 3:
            pods = math.ceil(count / 3)
            cols = min(3, pods)
            rows = math.ceil(pods / cols)
            pod, offset = divmod(i, 3)
            cx = .17 + .66 * (pod % cols) / (cols - 1) if cols > 1 else .5
            cy = .24 + .48 * (pod // cols) / (rows - 1) if rows > 1 else .5
            size = min(3, count - pod * 3)
            angle = 2 * math.pi * offset / size - math.pi / 2
            x, y = (cx, cy) if size == 1 else (cx + .09 * math.cos(angle), cy + .13 * math.sin(angle))
        else:
            hub = kind in {"hub_and_spoke", "wheel", "broadcast", "gather"}
            index, n = (i - 1, count - 1) if hub else (i, count)
            angle = 2 * math.pi * index / max(1, n) - math.pi / 2
            x, y = .5 + .36 * math.cos(angle), .5 + .36 * math.sin(angle)
        result.append({"id": f"member.{i+1}", "x": round(x, 6), "y": round(y, 6)})
    return result


# Inter-team export choices used by schema, CLI and collection UI; not organization rankings.
TEAM_EXCHANGE_PROFILES = {
    "none": {"label": "No inter-team communication", "description": "No exports or inter-team context; native internal sharing remains separate."},
    "summaries": {"label": "Designated-member summaries", "description": "Only a configured main member's validated summary from completed prior waves."},
    "contributions": {"label": "Designated-member contributions", "description": "Only a configured main member's validated candidate contribution from completed prior waves."},
}
