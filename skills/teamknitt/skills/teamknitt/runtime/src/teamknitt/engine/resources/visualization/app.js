(() => {
  "use strict";
  const boot = JSON.parse(document.getElementById("teamknitt-bootstrap").textContent);
  let state = boot.state, paused = false, disconnected = false;
  let map = "workflow", selected = null, zoom = 1, fit = "auto";
  let selection = state.requested_selection || "latest", requestVersion = 0;
  const signatures = new Map();
  const $ = id => document.getElementById(id);
  const pretty = value => String(value ?? "").replaceAll("_", " ");
  const titleCase = value => { const result = pretty(value); return result.charAt(0).toUpperCase() + result.slice(1); };
  const numeric = value => Number.isFinite(value) ? value : 0;
  const quantity = value => new Intl.NumberFormat(undefined, {maximumFractionDigits: 0}).format(numeric(value));
  const frozen = () => paused || disconnected || !boot.api_url;
  const live = () => !frozen() && state.runtime.status === "running";
  const statusOf = value => value === "running" && frozen() ? "last_observed" : value || "unknown";
  const states = {
    planned: ["□", "PLANNED"], ready: ["□", "READY"], running: ["▶", "ACTIVE"],
    completed: ["✓", "DONE"], waiting: ["Ⅱ", "WAITING"], idle: ["□", "IDLE"],
    skipped: ["–", "BYPASSED"], deferred: ["–", "DEFERRED"], unknown: ["?", "UNKNOWN"],
    failed: ["!", "FAILED"], interrupted: ["!", "INTERRUPTED"], cancelled: ["–", "CANCELLED"],
    last_observed: ["~", "RECORDED ACTIVE"], budget_exhausted: ["|", "LIMIT REACHED"]
  };
  const stateInfo = value => states[value] || ["?", pretty(value).toUpperCase()];

  function element(tag, content, className) {
    const result = document.createElement(tag);
    if (content !== undefined) result.textContent = content;
    if (className) result.className = className;
    return result;
  }
  function svgElement(tag, attributes, content) {
    const result = document.createElementNS("http://www.w3.org/2000/svg", tag);
    for (const [key, value] of Object.entries(attributes)) result.setAttribute(key, String(value));
    if (content !== undefined) result.textContent = content;
    return result;
  }
  function setText(id, value) {
    const target = $(id), content = String(value ?? "—");
    if (target.textContent !== content) target.textContent = content;
  }
  function changed(key, value) {
    const signature = JSON.stringify(value);
    if (signatures.get(key) === signature) return false;
    signatures.set(key, signature);
    return true;
  }
  function stamp(value, date = true) {
    const parsed = new Date(value);
    if (!value || !Number.isFinite(parsed.getTime())) return "—";
    const iso = parsed.toISOString();
    return date ? iso.slice(0, 19).replace("T", " ") : iso.slice(11, 19);
  }

  function renderDetails() {
    const setup = state.setup, runtime = state.runtime;
    const node = setup.nodes.find(item => item.id === selected);
    const actor = setup.actors.find(item => item.id === selected) || runtime.actors.find(item => item.id === selected);
    let heading = "Lab configuration", description = "Select a process step or team member for details.", rows;
    if (node) {
      heading = titleCase(node.label);
      description = node.kind === "confirmation"
        ? "Reserved confirmation occurs after acting episodes. Its results do not return to those agents."
        : "Workflow dependency step. Completion records execution; evidence status is separate.";
      rows = [["State", stateInfo(statusOf(runtime.node_states[node.id]))[1]], ["Step ID", node.id],
        ["Work type", titleCase(node.kind)], ["Actors", node.actors.join(", ")],
        ["Dependencies", node.depends_on.join(", ") || "Mission / qualification inputs"], ["Sharing", titleCase(setup.communication)]];
    } else if (actor) {
      const observed = runtime.actors.find(item => item.id === actor.id);
      heading = titleCase(actor.name || actor.id);
      description = titleCase(actor.approach) || "Observed child agent; inherited team permissions and limits apply.";
      rows = [["Actor ID", actor.id], ["Role", titleCase(actor.role || "child")],
        ["State", stateInfo(statusOf(observed?.status || "planned"))[1]], ["Step", observed?.node || "—"],
        ["Model", setup.model.name], ["Sharing", titleCase(setup.communication)]];
    } else {
      rows = [["Model", setup.model.name], ["Sharing", titleCase(setup.communication)], ["Statistics", titleCase(setup.statistics)],
        ["Decisions", pretty(setup.decision_mode) + (setup.specialist ? " / " + setup.specialist : "")],
        ["Agent limit", setup.resources.max_active_agents], ["Child depth", setup.delegation.max_depth],
        ["Children / agent", setup.delegation.max_children_per_agent]];
      if (setup.execution?.kind === "single_scientist") rows.push(
        ["Persistence", titleCase(setup.execution.persistence)], ["Effort mode", pretty(setup.execution.effort_mode)],
        ["Sequences", setup.execution.sequences], ["Passes / sequence", setup.execution.passes_per_sequence ?? "Until allowance"],
        ["Context", pretty(setup.execution.context_policy)]);
      if (setup.execution?.kind === "multi_lab") rows.push(
        ["Labs", setup.execution.lab_count], ["Active lab limit", setup.resources.max_active_labs], ["Sequences", setup.execution.sequences],
        ["Meeting", pretty(setup.execution.meeting)], ["Context", pretty(setup.execution.context_policy)],
        ...setup.labs.map(lab => [lab.id, `${lab.design} · ${lab.sharing}`]));
    }
    setText("detail-title", heading);
    setText("detail-description", description);
    if (!changed("details", rows)) return;
    $("details").replaceChildren(...rows.map(([name, value]) => {
      const row = element("div"); row.append(element("dt", name), element("dd", String(value ?? "—"))); return row;
    }));
  }

  function graphNodes() {
    if (map === "workflow") return state.setup.nodes.map(node => ({...node, state: statusOf(state.runtime.node_states[node.id])}));
    const actors = new Map(state.setup.actors.map(actor => [actor.id, {...actor, rank: actor.role === "coordinator" ? 0 : 1, depends_on: []}]));
    for (const actor of state.runtime.actors) {
      if (actor.id.startsWith("system:") || actors.has(actor.id)) continue;
      const parent = actor.id.includes(".child") ? actor.id.slice(0, actor.id.lastIndexOf(".child")) : null;
      actors.set(actor.id, {...actor, role: "child", name: actor.id,
        rank: 1 + (actor.id.match(/\.child/g) || []).length,
        depends_on: parent && actors.has(parent) ? [parent] : []});
    }
    return [...actors.values()].map(actor => ({...actor, label: actor.name || actor.id, kind: actor.role,
      actors: [actor.id], state: statusOf(state.runtime.actors.find(row => row.id === actor.id)?.status || "planned")}));
  }
  function wrapWords(value, width = 23) {
    const lines = [""];
    for (const word of titleCase(value).split(/\s+/)) {
      if (lines[lines.length - 1].length + word.length + 1 > width && lines[lines.length - 1]) lines.push("");
      lines[lines.length - 1] += (lines[lines.length - 1] ? " " : "") + word;
    }
    return lines.slice(0, 2).map(line => line.length > width ? line.slice(0, width - 1) + "…" : line);
  }
  function renderGraph() {
    const setup = state.setup, labView = map === "workflow" && setup.execution?.kind === "multi_lab";
    const svg = $("graph"), nodes = graphNodes(), positions = new Map();
    const actorIds = labView ? setup.labs.map(lab => lab.id) : map === "workflow" ? setup.actors.map(actor => actor.id) : nodes.map(node => node.id);
    const shared = nodes.some(node => labView ? !actorIds.includes(node.lab) : node.actors.length !== 1 || !actorIds.includes(node.actors[0]));
    const lanes = [...actorIds, ...(shared ? ["system:shared"] : [])];
    const ranks = [...new Set(nodes.map(node => node.rank))].sort((a, b) => a - b);
    const rankBase = Math.min(...ranks), cell = 204, boxWidth = 180, boxHeight = 86, gutter = 174;
    const width = Math.max(500, gutter + (Math.max(...ranks) - rankBase + 1) * cell + 16);
    const height = Math.max(250, 50 + lanes.length * 102);
    if (fit) {
      const available = Math.min(1, ($("graph-scroll").clientWidth - 2) / width);
      // Preserve legibility by default; an explicit Fit requests the full overview.
      zoom = Math.max(fit === "all" ? .2 : .8, available);
    }
    const signature = {nodes, lanes, map, selected, zoom, width};
    if (!changed("graph", signature)) return;
    const focusId = svg.contains(document.activeElement) ? document.activeElement.getAttribute("data-node-id") : null;
    let focusTarget;
    svg.replaceChildren();
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg.setAttribute("width", width * zoom); svg.setAttribute("height", height * zoom);
    const defs = svgElement("defs", {}), marker = svgElement("marker", {id: "arrow", viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 5, markerHeight: 5, orient: "auto-start-reverse"});
    marker.append(svgElement("path", {d: "M 0 0 L 10 5 L 0 10 z", fill: "#8c816e"})); defs.append(marker); svg.append(defs);
    for (let index = 0; index < lanes.length; index++) {
      const id = lanes[index], y = 44 + index * 102;
      svg.append(svgElement("line", {x1: 12, x2: width - 12, y1: y, y2: y, class: "lane-rule"}));
      const actor = state.setup.actors.find(item => item.id === id);
      const name = id === "system:shared" ? "System / shared work" : pretty(id);
      const parts = wrapWords(name, 22);
      parts.forEach((part, line) => svg.append(svgElement("text", {x: 12, y: y + 30 + line * 16, class: "lane-label"}, part)));
      if (id !== "system:shared") svg.append(svgElement("text", {x: 12, y: y + 70, class: "lane-role"}, labView ? "LAB / " + setup.labs.find(lab => lab.id === id).variant : titleCase(actor?.role || "child")));
    }
    for (const rank of ranks) {
      const step = nodes.find(node => node.rank === rank && node.sequence);
      const heading = map === "workflow" ? step ? setup.execution?.kind === "multi_lab" ? `SEQ ${step.sequence} / ${pretty(step.kind).toUpperCase()}` : `SEQ ${step.sequence} / ${step.pass ? "PASS " + step.pass : "BUDGET"}`
        : `STAGE ${String(rank + 1).padStart(2, "0")}` : rank === 0 ? "COORDINATION" : rank === 1 ? "PRIME AGENTS" : `CHILD LEVEL ${rank - 1}`;
      svg.append(svgElement("text", {x: gutter + (rank - rankBase) * cell, y: 26, class: "rank-label"}, heading));
    }
    for (const node of nodes) {
      const lane = labView && actorIds.includes(node.lab) ? node.lab : !labView && node.actors.length === 1 && actorIds.includes(node.actors[0]) ? node.actors[0] : "system:shared";
      positions.set(node.id, {x: gutter + (node.rank - rankBase) * cell, y: 52 + lanes.indexOf(lane) * 102});
    }
    for (const node of nodes) for (const dependency of node.depends_on) {
      const from = positions.get(dependency), to = positions.get(node.id);
      if (!from || !to) continue;
      const startX = from.x + boxWidth, startY = from.y + boxHeight / 2;
      const endX = to.x - 5, endY = to.y + boxHeight / 2, bus = (startX + endX) / 2;
      svg.append(svgElement("path", {d: `M ${startX} ${startY} H ${bus} V ${endY} H ${endX}`,
        class: "graph-edge" + (node.state === "running" ? " active" : ""), "marker-end": "url(#arrow)"}));
    }
    for (const node of nodes) {
      const position = positions.get(node.id), [symbol, stateLabel] = stateInfo(node.state);
      const group = svgElement("g", {class: `node ${node.state}${selected === node.id ? " selected" : ""}`,
        transform: `translate(${position.x} ${position.y})`, tabindex: 0, role: "button", "data-node-id": node.id,
        "aria-label": `${titleCase(node.label)}; ${node.actors.join(", ")}; ${stateLabel}`});
      group.append(svgElement("title", {}, `${titleCase(node.label)}\n${node.actors.join(", ")}\n${stateLabel}`));
      group.append(svgElement("path", {d: `M 5 0 H ${boxWidth - 5} L ${boxWidth} 5 V ${boxHeight - 5} L ${boxWidth - 5} ${boxHeight} H 5 L 0 ${boxHeight - 5} V 5 Z`, class: "node-frame"}));
      group.append(svgElement("path", {d: `M 8 4 H ${boxWidth - 8} M 8 ${boxHeight - 4} H ${boxWidth - 8}`, class: "node-inset", "aria-hidden": "true"}));
      group.append(svgElement("text", {x: 10, y: 17, class: "node-kind"}, pretty(node.kind).toUpperCase()));
      wrapWords(node.label).forEach((line, index) => group.append(svgElement("text", {x: 10, y: 37 + index * 15, class: "node-title"}, line)));
      group.append(svgElement("text", {x: 10, y: 73, class: "state-symbol"}, symbol));
      group.append(svgElement("text", {x: 30, y: 73, class: "node-state"}, stateLabel));
      if (selected === node.id) group.append(svgElement("rect", {x: -4, y: -4, width: boxWidth + 8, height: boxHeight + 8, class: "selection-frame"}));
      const select = () => {selected = node.id; renderGraph(); renderDetails();};
      group.addEventListener("click", select);
      group.addEventListener("keydown", event => {if (event.key === "Enter" || event.key === " ") {event.preventDefault(); select();}});
      svg.append(group); if (node.id === focusId) focusTarget = group;
    }
    if (focusTarget) focusTarget.focus({preventScroll: true});
    setText("graph-count", `${nodes.length} ${map === "workflow" ? "steps" : "actors"}`);
    setText("process-title", map === "workflow" ? "Process overview" : "Team status");
    setText("map-note", map === "workflow"
      ? "Arrows indicate readiness dependencies, not permission to read peer data. Done refers to execution; deferred verification is separate from reserved confirmation."
      : "Rows retain actor identity. Arrows indicate observed child delegation; reporting relationships are not inferred.");
    setText("zoom-value", `${Math.round(zoom * 100)}%`);
  }

  function renderOperations() {
    const operations = [...state.runtime.active].sort((a, b) => `${a.actor?.id || ""}:${a.category}`.localeCompare(`${b.actor?.id || ""}:${b.category}`));
    setText("active-count", operations.length);
    const values = operations.map(operation => ({...operation, displayStatus: statusOf(operation.status),
      elapsed: statusOf(operation.status) === "running" && operation.elapsed_seconds !== null ? Math.floor(operation.elapsed_seconds) : null}));
    if (!changed("operations", values)) return;
    const body = $("activities"); body.replaceChildren();
    if (!values.length) {
      const row = element("tr", undefined, "empty-row"), cell = element("td",
        state.runtime.status === "plan_only" ? "No run observed. Start a run separately to observe its operations." : "No open operation is present in the observed record.");
      cell.colSpan = 4; row.append(cell); body.append(row); return;
    }
    for (const operation of values) {
      const row = element("tr", undefined, operation.displayStatus), location = element("td");
      location.append(element("strong", pretty(operation.actor?.id || "system")), element("small", operation.node || "No workflow step recorded"));
      const kind = operation.kind === "provider_request" ? "Model request" : titleCase(operation.category);
      const action = element("td"); action.append(element("strong", kind), element("small", operation.model || operation.provider || "Local runtime"));
      row.append(location, action, element("td", operation.elapsed === null ? "—" : `${operation.elapsed}s`, "elapsed"),
        element("td", operation.category === "delegation" && operation.displayStatus === "running" ? "WAITING ON CHILD" : stateInfo(operation.displayStatus)[1]));
      body.append(row);
    }
  }

  const eventNames = {provider_request: "Request sent", provider_response: "Response received", provider_error: "Request failed",
    phase_started: "Step started", phase_completed: "Step ended", episode_started: "Episode started", episode_finished: "Episode ended",
    trial_started: "Run started", trial_finished: "Run ended", domain_step_pending: "Domain step deferred",
    operational_coordination: "Operational coordination", sharing_read: "Permitted sharing read"};
  function renderEvents() {
    const events = state.runtime.recent_events.slice(-20).reverse();
    if (!changed("events", events)) return;
    const body = $("events"), scroll = body.closest(".table-scroll"), previousScroll = scroll.scrollTop;
    body.replaceChildren();
    if (!events.length) {
      const row = element("tr", undefined, "empty-row"), cell = element("td", "No runtime events recorded."); cell.colSpan = 2; row.append(cell); body.append(row);
    }
    for (const event of events) {
      const fault = event.kind === "provider_error" || event.status === "failed";
      const row = element("tr", undefined, fault ? "fault" : undefined), time = element("td"), when = element("time", stamp(event.time, false));
      when.dateTime = event.time; when.title = stamp(event.time) + " UTC"; time.append(when);
      let name = eventNames[event.kind] || titleCase(event.kind);
      if (event.kind === "activity_started" || event.kind === "activity_finished") name = `${titleCase(event.category)} ${event.kind === "activity_started" ? "started" : "ended"}`;
      const detail = element("td"); detail.append(element("strong", name), element("small", pretty(event.actor?.id || event.node || "Runtime")));
      row.append(time, detail); body.append(row);
    }
    scroll.scrollTop = previousScroll;
  }

  function renderConditions() {
    const runtime = state.runtime, notes = [];
    if (disconnected) notes.push(["warning", "? VIEW DISCONNECTED", "Check that the local visualization command is running. Last received data is retained."]);
    else if (paused) notes.push(["info", "Ⅱ VIEW PAUSED", "Resume updates to follow the run. Values are frozen at the last received record."]);
    else if (!boot.api_url) notes.push(["info", "RECORDED VIEW", "Values describe the saved record. Current activity is not measured."]);
    if (runtime.status === "stale") notes.push(["warning", "? HEARTBEAT STALE", "Check the runner process. Activity cannot be confirmed from the last heartbeat."]);
    if (runtime.status === "activity_unknown") notes.push(["warning", "? TELEMETRY UNKNOWN", "No usable current activity signal is available. Inspect the local run log."]);
    if (runtime.status === "catching_up") notes.push(["info", "READING RECORD", "The observer is reading an event backlog. Current activity is not yet established."]);
    if (runtime.status === "failed") notes.push(runtime.recorded_status === "cancelled"
      ? ["info", "RUN CANCELLED", "Execution was cancelled. Review the journal for unfinished operations."]
      : ["fault", "! EXECUTION FAILED", "The run ended with unfinished work. Inspect the event journal and local run summary."]);
    if (numeric(runtime.skipped_events)) notes.push(["warning", "? INCOMPLETE JOURNAL", `${quantity(runtime.skipped_events)} entries could not be read. Totals may be incomplete.`]);
    if (numeric(runtime.metrics.errors) && runtime.status !== "failed") notes.push(["info", "ERROR HISTORY", `${quantity(runtime.metrics.errors)} error events recorded, including recovered errors. Review the journal.`]);
    if (live() && runtime.metrics.requests >= state.setup.budget.max_llm_calls) notes.push(["warning", "REQUEST LIMIT REACHED", "New model requests may be denied by the configured budget."]);
    if (!notes.length) notes.push(["info", "RUNTIME RECORD", "No runtime fault is reported in the observed record. Evidence status is shown separately."]);
    if (!changed("conditions", notes)) return;
    $("conditions").replaceChildren(...notes.map(([severity, heading, description]) => {
      const row = element("li", undefined, severity); row.append(element("strong", heading), element("span", description)); return row;
    }));
  }

  function renderStatus() {
    const runtime = state.runtime, setup = state.setup;
    const executionLabels = {plan_only: "NOT STARTED", running: frozen() ? "RECORDED RUNNING" : "RUNNING",
      completed: "ENDED", failed: runtime.recorded_status === "cancelled" ? "CANCELLED" : "FAILED",
      stale: "STATE UNKNOWN", activity_unknown: "STATE UNKNOWN", catching_up: "READING RECORD"};
    const fault = runtime.status === "failed" && runtime.recorded_status !== "cancelled";
    const uncertain = ["stale", "activity_unknown", "catching_up"].includes(runtime.status);
    const activeRequests = runtime.active.filter(operation => operation.kind === "provider_request").length;
    setText("run-state", live() && activeRequests ? "EXECUTING" : executionLabels[runtime.status] || "STATE UNKNOWN");
    $("run-state").className = "state-label" + (fault ? " fault" : uncertain ? " warning" : live() && activeRequests ? " running" : "");
    setText("execution-note", runtime.recorded_status ? pretty(runtime.recorded_status) : "No run observed.");
    if (setup.execution?.kind === "single_scientist" && runtime.sequence_progress?.current_sequence) {
      const progress = runtime.sequence_progress;
      setText("execution-note", `Sequence ${progress.current_sequence} / ${setup.execution.sequences} · Pass ${progress.current_pass}` +
        (setup.execution.passes_per_sequence ? ` / ${setup.execution.passes_per_sequence}` : " · budget mode"));
    }
    if (setup.execution?.kind === "multi_lab" && runtime.sequence_progress?.current_sequence) {
      setText("execution-note", `Sequence ${runtime.sequence_progress.current_sequence} / ${setup.execution.sequences} · ${setup.execution.lab_count} labs · ${pretty(setup.execution.meeting)}`);
    }
    setText("source-state", disconnected ? "DISCONNECTED" : paused ? "PAUSED" : !boot.api_url ? "SNAPSHOT" : "LOCAL JOURNAL");
    setText("source-note", !boot.api_url ? "Saved observation; live updates disabled" : paused ? "Last received values retained" : "Filtered activity records from the selected run");
    setText("connection", disconnected ? "DISCONNECTED" : paused ? "PAUSED" : boot.api_url ? "CONNECTED" : "OFFLINE FILE");
    const at = ["completed", "failed"].includes(runtime.status) ? runtime.last_event_at : runtime.heartbeat_at || runtime.last_event_at;
    setText("telemetry-time", stamp(at));
    setText("telemetry-note", ["completed", "failed"].includes(runtime.status) ? "Final event time" : at ? "Heartbeat / latest event" : "No telemetry timestamp available");
    const evidence = {not_run: ["NOT RUN", "No execution record selected"], not_evaluated: ["NOT EVALUATED", "Execution end does not establish correctness"],
      no_valid_confirmation: ["NO VALID CONFIRMATION", "No valid confirmation result recorded"],
      confirmation_evaluated_exploratory: ["EVALUATED · EXPLORATORY", "Confirmation evaluated; conclusions remain scoped"]};
    const evidenceState = evidence[runtime.verification_status] || ["STATUS UNAVAILABLE", "No recognized evidence status recorded"];
    setText("evidence-state", evidenceState[0]); setText("evidence-note", evidenceState[1]);
    const terminal = ["completed", "failed"].includes(runtime.status);
    const knownInactive = terminal && !runtime.active.length;
    setText("metric-active", live() ? quantity(activeRequests) : knownInactive ? "0" : "—");
    setText("request-cap", "/ " + quantity(setup.resources.max_llm_requests));
    setText("active-note", live() ? "Observed requests / concurrency limit" : knownInactive ? "No open request in the final record" : "Current request count unavailable");
    setText("metric-requests", quantity(runtime.metrics.requests)); setText("budget-cap", "/ " + quantity(setup.budget.max_llm_calls));
    setText("metric-tokens", quantity(runtime.metrics.input_tokens + runtime.metrics.output_tokens));
    setText("token-note", `${quantity(runtime.metrics.input_tokens)} input / ${quantity(runtime.metrics.output_tokens)} output`);
    setText("metric-evaluations", quantity(runtime.metrics.evaluations)); setText("metric-errors", quantity(runtime.metrics.errors));
    setText("setup-agent-state", "READY");
    setText("observer-state", disconnected ? "DISCONNECTED" : paused ? "PAUSED" : runtime.status === "plan_only" ? "WAITING FOR RUN" : !boot.api_url || terminal ? "RECORD VIEW" : "OBSERVING");
    setText("last-updated", stamp(runtime.last_event_at, false));
  }

  function renderSelector() {
    const setup = state.setup, runtime = state.runtime;
    setText("design-scope", setup.execution?.kind === "multi_lab" ? "Lab collection" : "Lab design");
    setText("design-letter", setup.execution?.kind === "multi_lab" ? "" : setup.design_letter); setText("design-title", setup.design.name);
    setText("governance", titleCase(setup.design.governance)); setText("snapshot-id", setup.snapshot_id);
    setText("run-hint", runtime.trial_id || (state.trials.length ? "Latest follows runs with this exact configuration snapshot." : "No matching run recorded."));
    if (changed("trial-options", [state.trials, state.selection])) {
      const choices = [new Option("Latest matching run", "latest"), new Option("Setup only", "setup")];
      for (const run of state.trials) choices.push(new Option(`${run.id} / ${pretty(run.status)}`, run.id));
      if (!choices.some(option => option.value === selection) && state.selection !== "setup") choices.push(new Option(state.selection, state.selection));
      $("trial-select").replaceChildren(...choices);
    }
    $("trial-select").value = selection; $("trial-select").disabled = !boot.api_url;
    $("pause").disabled = !boot.api_url; setText("pause", paused ? "Resume updates" : "Pause updates");
    setText("view-time", stamp(state.generated_at) + " UTC");
    $("view-time").dateTime = state.generated_at;
  }
  function render() {renderSelector(); renderStatus(); renderConditions(); renderGraph(); renderDetails(); renderOperations(); renderEvents();}

  async function refresh() {
    if (!boot.api_url || paused) return;
    const version = ++requestVersion, requested = selection;
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const url = new URL(boot.api_url, location.href); url.searchParams.set("trial", requested);
      const response = await fetch(url, {cache: "no-store", signal: controller.signal});
      if (!response.ok) throw new Error("View unavailable");
      const next = await response.json();
      if (version !== requestVersion || requested !== selection || paused) return;
      state = next; disconnected = false; render();
    } catch (error) {if (version === requestVersion && !paused) {disconnected = true; render();}}
    finally {clearTimeout(timeout);}
  }
  async function poll() {await refresh(); if (boot.api_url) setTimeout(poll, 1200);}
  $("trial-select").addEventListener("change", () => {selection = $("trial-select").value; selected = null; refresh();});
  $("pause").addEventListener("click", () => {paused = !paused; render(); if (!paused) refresh();});
  $("clear-selection").addEventListener("click", () => {selected = null; renderGraph(); renderDetails();});
  for (const view of ["workflow", "team"]) $(view + "-tab").addEventListener("click", () => {
    map = view; selected = null; $("workflow-tab").setAttribute("aria-pressed", String(view === "workflow"));
    $("team-tab").setAttribute("aria-pressed", String(view === "team")); renderGraph(); renderDetails();
  });
  $("zoom-in").addEventListener("click", () => {fit = false; zoom = Math.min(1.8, zoom + .15); renderGraph();});
  $("zoom-out").addEventListener("click", () => {fit = false; zoom = Math.max(.5, zoom - .15); renderGraph();});
  $("zoom-reset").addEventListener("click", () => {fit = "all"; renderGraph();});
  new ResizeObserver(() => {if (fit) renderGraph();}).observe($("graph-scroll"));
  $("download").addEventListener("click", () => {
    const copy = document.documentElement.cloneNode(true);
    copy.querySelector("#teamknitt-bootstrap").textContent = JSON.stringify({state, api_url: null}).replaceAll("<", "\\u003c");
    const url = URL.createObjectURL(new Blob(["<!doctype html>\n" + copy.outerHTML], {type: "text/html"}));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "teamknitt-process-record.html"; anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  render(); poll();
})();
