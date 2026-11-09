"""Human-team research as design rationale, not validation of AI-team constructs.

Background supplied by Goran, 9 November 2026; research lineage also includes his
2022/2023 thesis research on distributed teams and creative processes.
The implementation separates explanatory locus, forms of emergence and process/state/outcome records rather than treating them as
one binary taxonomy or an automatic improvement recipe.
"""
from copy import deepcopy

AUTHOR_RESEARCH = {
    "author": "Goran Mitevski", "research_period": "2022/2023", "relation": "research_follow_up",
    "connection": "Teamknitt follows up Goran Mitevski’s 2022/2023 thesis research on distributed teams and their creative processes. It continues that work through configurable AI-agent teams, different ways to follow their work, and human-directed intervention.",
    "focus": ["distributed teamwork", "creative processes", "AI-agent participation"],
    "boundary": "This research background does not establish AI-team performance or intervention effects. Configuration and interventions remain user-directed.",
}

ADDITIONAL_SOURCES = {
    "mcgrath_1964": {"citation": "McGrath, J. E. (1964). Social Psychology: A Brief Introduction. Holt, Rinehart & Winston.", "tradition": "Input–process–output frameworks"},
    "hackman_1987": {"citation": "Hackman, J. R. (1987). The design of work teams. In J. W. Lorsch (Ed.), Handbook of Organizational Behavior. Prentice-Hall.", "tradition": "Team design and inputs"},
    "hackman_2002": {"citation": "Hackman, J. R. (2002). Leading Teams: Setting the Stage for Great Performances. Harvard Business School Press.", "tradition": "Enabling conditions and leadership"},
    "ilgen_2005": {"citation": "Ilgen, D. R., Hollenbeck, J. R., Johnson, M., & Jundt, D. (2005). Teams in organizations: From input-process-output models to IMOI models. Annual Review of Psychology, 56, 517–543.", "tradition": "Input–mediator–outcome–input cycles"},
    "marks_2001": {"citation": "Marks, M. A., Mathieu, J. E., & Zaccaro, S. J. (2001). A temporally based framework and taxonomy of team processes. Academy of Management Review, 26(3), 356–376.", "tradition": "Transition/action phases, interpersonal processes and emergent states"},
    "kozlowski_klein_2000": {"citation": "Kozlowski, S. W. J., & Klein, K. J. (2000). A multilevel approach to theory and research in organizations: Contextual, temporal, and emergent processes. In K. J. Klein & S. W. J. Kozlowski (Eds.), Multilevel Theory, Research, and Methods in Organizations. Jossey-Bass.", "tradition": "Compositional and compilational emergence"},
    "beal_2003": {"citation": "Beal, D. J., Cohen, R. R., Burke, M. J., & McLendon, C. L. (2003). Cohesion and performance in groups: A meta-analytic clarification of construct relations. Journal of Applied Psychology, 88(6), 989–1004.", "tradition": "Cohesion and performance research"},
    "edmondson_1999": {"citation": "Edmondson, A. (1999). Psychological safety and learning behavior in work teams. Administrative Science Quarterly, 44(2), 350–383.", "tradition": "Psychological safety and team learning"},
    "mathieu_2000": {"citation": "Mathieu, J. E., Heffner, T. S., Goodwin, G. F., Salas, E., & Cannon-Bowers, J. A. (2000). The influence of shared mental models on team process and performance. Journal of Applied Psychology, 85(2), 273–283.", "tradition": "Shared mental-model similarity and accuracy"},
    "lewis_2003": {"citation": "Lewis, K. (2003). Measuring transactive memory systems in the field. Journal of Applied Psychology, 88(4), 587–604.", "tradition": "Differentiated knowledge and transactive memory"},
    "dechurch_2010": {"citation": "DeChurch, L. A., & Mesmer-Magnus, J. R. (2010). The cognitive underpinnings of effective teamwork: A meta-analysis. Journal of Applied Psychology, 95(1), 32–53.", "tradition": "Cognitive emergent states and measurement"},
    "cooke_2013": {"citation": "Cooke, N. J., Gorman, J. C., Myers, C. W., & Duran, J. L. (2013). Interactive team cognition. Cognitive Science, 37(2), 255–285.", "tradition": "Team cognition as situated interaction activity"},
    "kelso_1995": {"citation": "Kelso, J. A. S. (1995). Dynamic Patterns: The Self-Organization of Brain and Behavior. MIT Press.", "tradition": "Coordination dynamics"},
    "schmidt_richardson_2008": {"citation": "Schmidt, R. C., & Richardson, M. J. (2008). Dynamics of interpersonal coordination. In A. Fuchs & V. K. Jirsa (Eds.), Coordination: Neural, Behavioral and Social Dynamics. Springer.", "tradition": "Interpersonal coupling and coordination"},
    "gorman_2010": {"citation": "Gorman, J. C., Cooke, N. J., & Amazeen, P. G. (2010). Training adaptive teams. Human Factors, 52(2), 295–307.", "tradition": "Perturbation and adaptive training in human teams"},
    "salas_2008": {"citation": "Salas, E., DiazGranados, D., Klein, C., Burke, C. S., Stagl, K. C., Goodwin, G. F., & Halpin, S. M. (2008). Does team training improve team performance? A meta-analysis. Human Factors, 50(6), 903–933.", "tradition": "Human-team training and intervention research"},
}

AXES = {
    "explanatory_locus": {
        "question": "Where is the team phenomenon located?",
        "options": {"non_system": "Members' attributes, knowledge, skills or aggregates of individual measures.",
                    "system": "Situated interaction and organization across members and non-human resources."},
        "sources": ["gorman_2017", "cooke_2013"],
        "boundary": "These are explanatory orientations, not a claim that every conventional model is linear or never studies interaction.",
    },
    "form_of_emergence": {
        "question": "How is a team-level construct formed?",
        "options": {"compositional": "An isomorphic team-level counterpart, often aggregated from comparable member measures.",
                    "compilational": "A differentiated configuration or pattern across members, not an individual construct's simple aggregate."},
        "sources": ["kozlowski_klein_2000", "dechurch_2010"],
        "boundary": "This axis is related to, but not identical to, explanatory locus. Configured patterns and report comparisons do not demonstrate emergence.",
    },
    "kind_of_record": {
        "question": "Is this a process, a state, or an outcome?",
        "options": {"process": "What members do together through time.", "state": "A condition of the team, theorized as dynamic, not the behavior itself.",
                    "outcome": "An independently assessed consequence, not merely workflow completion."},
        "sources": ["marks_2001", "ilgen_2005"],
        "boundary": "Trust and psychological safety are distinct; neither is inferred from AI text. Agent agreement is not a human emergent-state measure.",
    },
}

CONSTRUCTS = [
    {"id": "task_cohesion", "label": "Task cohesion", "status": "not_measured", "sources": ["beal_2003"], "support": "A declared common task is not evidence of cohesion."},
    {"id": "social_cohesion", "label": "Social cohesion", "status": "not_measured", "sources": ["beal_2003"], "support": "Friendly wording does not establish attraction or belonging."},
    {"id": "trust", "label": "Trust", "status": "not_measured", "sources": ["marks_2001", "ilgen_2005"], "support": "Reliance, acknowledgement and agreement do not measure trust."},
    {"id": "psychological_safety", "label": "Psychological safety", "status": "not_measured", "sources": ["edmondson_1999"], "support": "A channel for raising blockers is a configured opportunity, not a shared belief about interpersonal risk."},
    {"id": "collective_efficacy", "label": "Collective efficacy", "status": "not_measured", "sources": ["marks_2001", "ilgen_2005"], "support": "Confidence expressed by agents does not validate a shared capability belief."},
    {"id": "team_potency", "label": "Team potency", "status": "not_measured", "sources": ["marks_2001", "ilgen_2005"], "support": "No general team-capability belief or trait is inferred."},
    {"id": "shared_mental_models", "label": "Shared mental models", "status": "proxy_records_only", "sources": ["cannon_bowers_1993", "mathieu_2000"], "support": "Explicit plan reports can be compared, but do not measure latent knowledge structures or their correctness."},
    {"id": "transactive_memory", "label": "Transactive memory", "status": "configuration_only", "sources": ["wegner_1987", "lewis_2003"], "support": "Differentiated expertise directories and input grants are configured scaffolds, not a validated encoding/storage/retrieval system."},
]

PHASE_TYPES = {"independent_proposals": "transition", "task_adoption": "transition",
               "parallel_episodes": "action", "evidence_review": "transition"}

INTERVENTION_RATIONALES = [
    {"id": "inputs_conditions", "label": "Inputs and enabling conditions", "supports": ["Roles and responsibilities", "Task framing and success criteria", "Routing, source grants and work design"], "sources": ["hackman_1987", "hackman_2002", "salas_2008"], "boundary": "Reconfiguration is explicit and between runs; better inputs are not assumed to cause better coordination."},
    {"id": "shared_knowledge", "label": "Shared-knowledge interventions", "supports": ["Explicit role clarification", "Reviewed context or feedback", "User-directed cross-training task design"], "sources": ["cannon_bowers_1993", "mathieu_2000"], "boundary": "Providing the same prompt is not human cross-training or proof of a shared mental model."},
    {"id": "coordination_dynamics", "label": "Coordination and adaptive practice", "supports": ["Planned bounded disturbances", "Operator feedback", "Trace and outcome review"], "sources": ["gorman_2010", "cooke_2013", "gorman_2017"], "boundary": "Disturbance scenarios are not model-weight training or validated AI-team adaptation. No general rule that more variability is better is assumed."},
    {"id": "execution_control", "label": "Operator control", "supports": ["Pause before the next wave", "Resume within the same limits", "Stop after the current wave"], "sources": [], "boundary": "Execution control is a software safeguard, not a psychological intervention or improvement measure."},
]


def catalogue(sources):
    return {"title": "Background: Research and Theory on Human Teams", "background_credit": "Goran · 9 November 2026",
            "design_basis": "Human-team research informs configuration, task framing, observation and human-led intervention; transfer to AI-agent teams requires independent validation.",
            "author_research": deepcopy(AUTHOR_RESEARCH), "axes": deepcopy(AXES), "constructs": deepcopy(CONSTRUCTS), "interventions": deepcopy(INTERVENTION_RATIONALES),
            "representative_sources": deepcopy(sources), "automatic_improvement": False, "api_calls": 0}


def project(report):
    c = report["cognition"]
    rows = []
    for wave in report["waves"]:
        phases = sorted({node.split(":")[1] for node in wave["nodes"] if ":" in node})
        kinds = {PHASE_TYPES.get(phase, "unclassified") for phase in phases}
        rows.append({"wave": wave["wave"], "phases": phases,
                     "phase_type": next(iter(kinds)) if len(kinds) == 1 else "mixed" if kinds else "operational",
                     "annotation": "Conventional annotation of known task phases, not a new scheduler or measured interpersonal process."})
    return {"background_credit": "Goran · 9 November 2026", "author_research": deepcopy(AUTHOR_RESEARCH), "axes": deepcopy(AXES), "constructs": deepcopy(CONSTRUCTS),
            "episode_cycle": {
                "model": "IPO / IMOI: inputs, process and state mediators, outcomes, feedback",
                "inputs": {"configured_members": len(c["roles"]), "representations": len(c["representations"]), "topology": report["topology"]["kind"]},
                "process_records": {"publications": None if report["mode"] == "configuration" else sum(e["kind"] == "representation_published" for e in report["events"]),
                                    "exposures": None if report["mode"] == "configuration" else sum(e["kind"] == "representation_exposed" for e in report["events"]),
                                    "acknowledgements": None if report["mode"] == "configuration" else sum(e["kind"] == "handoff_acknowledged" for e in report["events"])},
                "outcomes": {"execution_status": report["status"], "task_review": report["task_review"], "goal_achieved": report["goal_achieved"]},
                "feedback": "Operator feedback and explicit future configuration/task changes; no automatic episode restart or budget reset.",
                "sources": ["mcgrath_1964", "hackman_1987", "ilgen_2005", "marks_2001"],
                "phases": rows, "interpersonal_processes": "Cross-cutting in the human framework; not automatically measured here.",
            },
            "patterns": {"expertise_directory": deepcopy(c["expertise_directory"]), "work_dependencies": [{"id": w["id"], "actors": w["actors"], "depends_on": w["depends_on"]} for w in c["work"]],
                         "status": "configured_patterns_not_estimated_emergence"},
            "intervention_rationales": deepcopy(INTERVENTION_RATIONALES),
            "transfer_status": "design_hypotheses_not_validated_for_ai_teams"}
