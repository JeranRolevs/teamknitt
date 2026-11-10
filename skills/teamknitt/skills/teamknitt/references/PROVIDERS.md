# Configure a provider

teamknitt connects to services by a declared JSON protocol. It includes a chat-completions
adapter for generation and chat-completions or typed-JSON adapters for optional decisions.
The user chooses the service, account, model and request options; there are no bundled accounts,
service defaults or automatic model choices. Other protocols require a registered adapter.

## Generation

Edit the provider section of study.yaml:

```yaml
provider:
  adapter: chat_completions
  base_url: https://your-provider.example/v1
  endpoint: /chat/completions
  models_endpoint: null
  model: your-model-id
  api_key_env: TEAMKNITT_API_KEY
  env_file: .env
  timeout_seconds: 90
  max_output_tokens: 8192
  max_parallel_requests: 2
  request_options: {}
```

Replace the URL and model with values from your service's own documentation. Starter URLs
under .invalid and YOUR_MODEL_ID are intentional placeholders: prepare and visualization work,
but run and doctor --live reject them before dispatch. A JSON endpoint is compatible only if
it accepts model, messages, a bounded output-token field and stream: false, and returns a
choices array containing message.content. Usage receipts may contain prompt_tokens /
completion_tokens or input_tokens / output_tokens; missing receipts remain visibly missing.

base_url is the API prefix. endpoint is appended to it and must be an absolute API path,
without query parameters or traversal. Use HTTPS for remote hosts. HTTP is allowed only for
explicit loopback URLs such as http://127.0.0.1:8000/v1. Redirects are not followed with credentials.

Set the named environment variable or put it in the workspace's ignored .env file:

```text
TEAMKNITT_API_KEY=replace-with-your-private-key
```

Never put raw keys in study.yaml. For an endpoint that explicitly needs no authentication,
set api_key_env: null; no Authorization header will be sent. This is an explicit user choice.
Use max_output_field: max_completion_tokens if your compatible endpoint requires that spelling.
The default is max_tokens. Request options cannot override the model, messages, streaming or
output bound. Finite JSON options such as temperature and nested generation settings are
sent only when explicitly supplied; support for them depends on the selected service.

Model listing is optional. If your service exposes a compatible data / id listing, set
models_endpoint, for example /models, to have an explicit live check use it. Otherwise the
live check directly probes the chosen generation model without assuming a listing API exists.

## Prepare, check and run

python3 engine.py prepare validates settings and compiles variants without reading a key or
calling a provider. python3 engine.py doctor reads local credential presence only.
python3 engine.py doctor --live explicitly makes metered probes of the chosen generation and
selected decision models. python3 engine.py run --variant single explicitly starts a workflow
once you have supplied the mission. No setup, test, diagram or package build makes these calls.

All dispatched requests, including failed requests with uncertain billing, decisions, fallbacks
and output corrections, use the same study request/time budget. Transport failures are not
retried automatically. Provider identity, endpoint/model settings and actual usage enter the
saved configuration and journal. Key values remain private and known keys are redacted.

See [decision endpoints](DECISION_PROVIDERS.md) for separate judging models. Generation and
decision endpoints may use different accounts and credentials.
