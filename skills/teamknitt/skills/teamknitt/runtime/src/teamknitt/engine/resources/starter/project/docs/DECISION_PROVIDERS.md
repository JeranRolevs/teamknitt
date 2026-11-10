# Optional decision endpoints

Every eligible agent can request a bounded decision and then resume its own generation context.
The user selects LLM-only, shadow or selected-active mode. A decision is a semantic judgment,
not empirical verification or permission to change the lab configuration.

## Account-free setup

```bash
teamknitt engine init ../my-lab --decision-backend chat_completions
```

Use --decision-backend typed for a typed JSON endpoint, or llm_only for the default same-model
route. Initialization only writes placeholder settings. Configure the selected endpoint before
an explicit live check or run; no key, service account or paid call is part of setup.

## Declare the selected endpoint

```yaml
decision_providers:
  specialist:
    adapter: chat_completions
    base_url: https://your-decision-provider.example/v1
    endpoint: /chat/completions
    model: your-decision-model-id
    api_key_env: TEAMKNITT_DECISION_API_KEY
    env_file: .env
    timeout_seconds: 90
    max_parallel_requests: 2
    max_output_tokens: 2048
base_overrides:
  decisions:
    mode: selected_active
    specialist: specialist
    allowed_specs: [semantic_choice.v1]
```

Declare every specialist by a lowercase path-safe ID. There are no built-in provider or model
aliases. The chat adapter supplies a bounded JSON instruction for noul, choice or score answers,
then checks the returned probabilities and labels. A model must reliably follow that contract.
max_output_field and request_options follow the generation adapter's rules.

For adapter: typed, choose your endpoint path and omit chat-only output/request options. Its
request contract is:

```json
{"model":"your-model-id","state":"permitted context","questions":{"q":{"type":"noul","instructions":"Does the context support the statement?"}}}
```

The response contains the resolved model, a matching answers mapping, and optional usage:

```json
{"model":"resolved-model-id","answers":{"q":{"noul":0.8}},"usage":{"input_tokens":20,"output_tokens":4}}
```

The local adapter validates answer types, labels, finite probabilities and their totals. A
service with another response schema needs a different adapter. Transport uses the same
HTTPS/loopback, authentication and no-redirect rules as generation.

## Modes and accounting

- LLM-only uses a bounded call to the generation model and needs no specialist credentials.
- Shadow retains a separate opinion in the private journal without returning it to the acting agent.
- Selected active returns a valid specialist answer to the same episode. Missing credentials,
  incompatible answers or an unavailable specialist can fall back to the generation model only
  within the existing budget. Uncertain requests are counted; they are not retried.

Generation and decisions share concurrency, time and request limits, including for children.
Decision receipts are grouped by decision/<configured-id>; total decision tokens are separate
from generation tokens. Allowed context references are checked before context resolution or HTTP.
Model-reported confidence is not a calibrated scientific probability.

Read [provider configuration](PROVIDERS.md), and set private credentials in the ignored .env
file. doctor --live --variant <id> probes only the specialist selected by that variant; an
LLM-only variant does not read or probe an unused specialist account.
