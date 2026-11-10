# Custom APIs

> **Status:** implemented. VEYRA can call user-defined REST APIs as tools and can use any OpenAI-compatible chat endpoint as its online model. API keys are stored in Windows Credential Manager.

There are two extension points:

1. **The online chat model.** VEYRA's router sends hard requests to an OpenAI-compatible `/chat/completions` endpoint. Mercury and Gemini offer compatible endpoints; for Claude, point VEYRA at an OpenAI-compatible gateway, or expose Claude as a custom tool with the second option.
2. **Custom tools.** Any REST API can be defined in Settings and exposed to the local model as `chiama_api`. This is the path for Exa, direct Anthropic Messages calls, direct Gemini `generateContent` calls, internal services and webhooks.

The local model does not need new source code for either path. It receives the configured API names and descriptions, chooses one, and the call is executed only after confirmation.

## Add a custom API

1. Open **Settings → Custom APIs**.
2. Paste a JSON array of definitions into **API definitions**. Start with `[]` and add one object per API.
3. Save settings. The definitions are validated before they reach the model.
4. The configured APIs appear with a key field. Paste each key and choose **Save key**. Keys go to Credential Manager, never to the JSON or `config.json`.
5. Ask for a task that names the API, for example “use Exa to find recent sources about this topic”. The UI shows the request and asks for confirmation before sending it.

The **API definitions** field must contain valid JSON. A definition has these fields:

| Field | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Lowercase slug, 2–32 characters, used by the model and for the key name. |
| `name` | yes | Human-readable label. |
| `description` | no | What the API is for and what payload it expects. Kept under 300 characters. |
| `base_url` | yes | `http://` or `https://` origin and optional base path. No credentials, query or fragment. |
| `path` | no | Relative path. No `..`, query, fragment or spaces. |
| `method` | no | `GET`, `POST`, `PUT`, `PATCH` or `DELETE`; default `POST`. |
| `auth_header` | no | Header that receives the key; default `Authorization`. |
| `auth_prefix` | no | Prefix before the key; default `Bearer `, use `""` for `x-api-key`. |
| `headers` | no | Static non-secret headers, at most 20. Authentication headers belong in the key field. |
| `enabled` | no | Default `true`. Disabled APIs are not offered to the model. |

Limits: 20 APIs per installation, 20 static headers per API, 4000 characters per model payload, 30-second timeout, no redirects, and at most 200,000 characters from a response. Only configured base URLs are reachable; the model cannot invent an arbitrary URL.

## Exa search

Exa is a search API, not a chat model. Define it as a tool:

```json
[
  {
    "id": "exa",
    "name": "Exa search",
    "description": "Search the web. Payload: {\"query\": \"...\", \"numResults\": 5}.",
    "base_url": "https://api.exa.ai",
    "path": "/search",
    "method": "POST",
    "auth_header": "x-api-key",
    "auth_prefix": "",
    "headers": {"content-type": "application/json"},
    "enabled": true
  }
]
```

Save the Exa key in the `exa` key field. A model call such as `{"query":"latest local-first AI news","numResults":5}` becomes a POST to `https://api.exa.ai/search`.

## Claude Messages

Direct Claude access uses Anthropic's `x-api-key` header and its own message format:

```json
[
  {
    "id": "claude",
    "name": "Claude Messages",
    "description": "Ask Claude for a second opinion. Payload: model, max_tokens, messages.",
    "base_url": "https://api.anthropic.com",
    "path": "/v1/messages",
    "method": "POST",
    "auth_header": "x-api-key",
    "auth_prefix": "",
    "headers": {
      "anthropic-version": "2023-06-01",
      "content-type": "application/json"
    },
    "enabled": true
  }
]
```

The model builds a JSON object with `model`, `max_tokens` and `messages`. The response is wrapped as external data. If you want Claude to be the **chat brain** instead of a tool, use an OpenAI-compatible gateway in **Settings → Models**; VEYRA's router protocol is OpenAI chat completions.

## Mercury and other OpenAI-compatible providers

Mercury and many other providers expose OpenAI-compatible chat completions. Configure **Settings → Models**:

- enable the online model;
- set its base URL to the provider's OpenAI-compatible URL;
- set the model id;
- save the provider key as **Online model**.

That provider becomes the escalation model for hard requests. The local model remains the default and the fallback.

## What the local model sees

The system prompt contains only the API `id`, `name` and sanitized `description`. It never contains keys or full URLs. Every call:

- must name a configured `id`;
- is `CONFIRM`, so the user sees the arguments and approves or declines it;
- sends a JSON object; GET APIs receive those fields as query parameters;
- has a 30-second timeout and does not follow redirects;
- returns a response wrapped in `<dati_esterni fonte="custom_api:...">`, which the model must treat as data, not instructions;
- is written to the tool log with normal secret redaction.

## Why the model does not rewrite its own code

Runtime self-modification is deliberately not enabled. A model that can write and import its own Python can bypass the risk gates, read credentials, and change behaviour after an update. Declarative API definitions give the same practical result for REST services without that attack surface.

If an integration needs a protocol that is not REST, add a typed built-in tool with tests instead of generating and loading code at runtime. The contributor flow is in [adding-a-tool.md](adding-a-tool.md). The existing `esegui_python` tool remains sandboxed and separate from VEYRA's source tree.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| “No custom APIs configured” | definitions were not saved | save the JSON, then reload Settings |
| JSON validation error | malformed array or field | compare against the examples; fields are case-sensitive |
| 401/403 from the API | missing or wrong key | save the key for that exact `id` |
| 404 | wrong base URL or path | check the provider's endpoint and path |
| “disabled in Settings” | `enabled` is false | set it to `true` and save |
| Response truncated | large payload | request fewer fields or a smaller limit |
| Model does not choose the API | task did not mention it | name the API id or description in the request |
