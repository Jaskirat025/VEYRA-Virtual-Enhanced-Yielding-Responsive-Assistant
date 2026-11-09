# Adding a tool

> **Status:** implemented in `backend/tools/registry.py` and the `backend/tools/builtin/` modules. This document defines the contract every tool must follow so the registry, the agent loop, the UI and the security model stay consistent.

A tool is a small, typed Python function with a declared category and risk level. The model never sees the whole tool set: a pre-classifier selects 3–6 relevant tools per request.

## The contract

```python
from backend.tools.registry import Category, Risk, ToolError, tool


@tool(category=Category.SYSTEM, risk=Risk.CONFIRM)
def chiudi_app(nome: str) -> str:
    """Close a running application by window or process name.

    Use when the user explicitly asks to close a program. Closing an
    application can lose unsaved work, so the CONFIRM risk level makes the
    UI ask the user before this runs.

    Example:
        chiudi_app("notepad")
    """
    if not nome.strip():
        raise ToolError("Application name is empty.")
    ...
    return f"Closed {matched_process}."
```

Rules:

- **The docstring is the tool prompt.** One sentence on what it does, one on when to use it, one example call. English only, under 60 words.
- **The schema comes from type hints.** `str`, `int`, `float`, `bool`, `Literal[...]` and `list[str]` are supported; everything else needs an explicit `Annotated` description. No `**kwargs`, no untyped parameters.
- **Tool names follow the product specification** and are part of the model contract, so they are not translated.
- **Return a string.** The executor truncates it to 2000 characters before it reaches the model. Return a short factual result, not a formatted document.
- **Raise `ToolError`** for expected failures (not found, permission denied, empty input). The message goes back to the model as text and to the tool log. Never raise bare exceptions on purpose; unexpected ones are caught and reported the same way.
- **Never return raw bytes, file contents over the limit, HTML or ANSI escapes.**
- **No hidden side effects** beyond the declared purpose. Local tools make no network calls; network-backed tools must use the external-data wrapper, a confirmation risk and a timeout.

## Risk levels

| Level | Behaviour | Examples |
| --- | --- | --- |
| `SAFE` | Executes immediately, logged, no prompt | `stato_pc`, `calcola`, `cerca_file`, `leggi_file`, `cerca_mail` |
| `CONFIRM` | Requires user confirmation (voice or UI) before execution | `chiudi_app`, `invia_mail`, `crea_issue`, `sposta_file`, `clicca` |
| `DANGEROUS` | Requires confirmation plus a written summary of the consequences | `elimina_file`, `esegui_python` |

Additional rules:

- Choose the **highest** level that could apply. `chiudi_app` is `CONFIRM` even though most closes are harmless.
- `DANGEROUS` tools must show the resolved target, not the raw model arguments: the absolute path, the exact code, the recipient address.
- File deletion prefers the Recycle Bin. Permanent deletion needs a second, explicit choice.
- Write access to Google and GitHub is disabled by default and enabled per integration in Settings.

## Confirmation flow

1. The agent loop emits a `tool_confirm_request` event with tool name, risk, a human summary and the validated arguments (with secrets redacted).
2. The UI shows a bordered dialog with the summary, the argument preview and Cancel focused by default.
3. Voice confirmation is accepted only for `CONFIRM`, never for `DANGEROUS`, and only when the microphone input came from the same turn.
4. On approval the backend executes with the **validated** arguments, not by re-parsing model text.
5. Denial returns “The user declined this action.” to the model and is logged as `denied`.
6. Confirmation expires after 120 seconds.

Prompt-injection lockout: once a turn has read external content (mail, issue body, web page, file), `CONFIRM` and `DANGEROUS` tools are blocked until the user confirms through the UI. The model cannot lift this lockout.

## Validation and execution

Before execution the executor:

1. checks that the tool exists and is enabled in Settings;
2. validates JSON against the generated schema (types, enums, bounds, string lengths);
3. rejects unknown parameters instead of ignoring them;
4. resolves and validates paths (no traversal outside allowed roots, no system directories);
5. enforces the risk gate and the injection lockout;
6. runs the tool with a timeout (default 20 s, 60 s for sandboxed Python);
7. truncates output to 2000 characters and strips control characters;
8. writes an audit record and returns the result to the model.

If the model produces invalid JSON, the executor returns the validation error once and allows a single retry. A second failure ends the tool call and is reported in the answer, not silently ignored.

## Categories

The pre-classifier maps an utterance to one or more categories and only those tools are exposed:

| Category | Tools |
| --- | --- |
| `system` | `apri_app`, `chiudi_app`, `volume`, `luminosita`, `screenshot`, `stato_pc`, `appunti`, `finestre` |
| `ui` | `clicca`, `scrivi`, `scorciatoia` |
| `files` | `cerca_file`, `leggi_file`, `sposta_file`, `elimina_file` |
| `calc` | `calcola`, `converti_unita`, `risolvi_equazione`, `grafico` |
| `code` | `esegui_python` |
| `github` | `lista_repo`, `leggi_issue`, `ultimi_commit`, `crea_issue` |
| `google` | `cerca_mail`, `leggi_mail`, `bozza_mail`, `invia_mail`, `eventi_oggi`, `eventi_range`, `crea_evento` |
| `memory` | `salva_nota`, `cerca_note`, `timer`, `sveglia` |
| `communication` | `condividi_whatsapp` |
| `custom` | `chiama_api` (definition supplied by the user) |
| `meta` | `chiedi_chiarimento` |

Keyword matching is the default selector; optional lightweight embeddings (`all-MiniLM`, lazy loaded, unloaded after use) improve ambiguous cases. If selection is uncertain, include `chiedi_chiarimento` plus the two most likely categories rather than dumping every tool.

## Custom APIs without code

A REST integration does not need a new Python tool. Add a definition in **Settings → Custom APIs**; the registry exposes the single `chiama_api` tool, and the system prompt lists the configured ids and descriptions. Keys are stored in Credential Manager, every call is `CONFIRM`, and responses are wrapped by `wrap_external`.

Runtime code generation is intentionally not part of this flow. A new protocol that cannot be expressed as a REST definition belongs in a typed built-in tool with tests, not in model-written code loaded at runtime. See [custom-apis.md](custom-apis.md).

## Agent loop

- `MAX_STEPS = 6`. Each step is one model turn that may contain tool calls.
- Tool results return as structured text, never as images or raw output.
- The spoken answer is 1–2 sentences; details stay in the chat transcript.
- Two failed calls of the same tool, or more than three steps, can trigger escalation to the online model when it is enabled.
- The model must call `calcola` for arithmetic; it must not compute in its head. The system prompt states this and the loop rejects plausible-looking numeric answers without a tool call when the user asked for a calculation.

## Settings and permissions

- Every tool has an on/off switch in Settings → Permissions, grouped by category.
- Integrations (GitHub, Google) are off until configured; read-only is the default. Gmail can use a local Google app password; Calendar and Gmail drafts still use OAuth.
- Custom APIs are user-defined JSON, limited to 20 entries, and remain disabled from the model's tool list until the definition is saved and enabled.
- Disabled tools are removed from the model's tool list, and calling one is an error, never an execution.
- Per-tool last-used time and error count are visible in the tool log.

## Audit record

Every call writes one row to SQLite:

| Field | Content |
| --- | --- |
| `id`, `created_at` | identifier and timestamp |
| `conversation_id`, `step` | turn linkage |
| `tool` | tool name |
| `category`, `risk` | declared metadata |
| `args_redacted` | arguments with secrets, tokens and long text removed |
| `status` | `ok`, `error`, `denied`, `timeout`, `blocked` |
| `duration_ms` | execution time |
| `error` | user-safe message, no stack trace |
| `output_preview` | first 200 characters |

The tool log screen reads this table; it never re-executes anything.

## Tests

Every tool needs unit tests that do not touch the real machine:

- happy path with a fake adapter or temporary directory;
- validation errors: missing, wrong type, out of range, extra field;
- `ToolError` path produces a readable message and status `error`;
- risk gate: `CONFIRM` and `DANGEROUS` do not execute without approval;
- injection lockout: after an external-content read, a `CONFIRM` tool is blocked;
- truncation: a 10 KB return value is cut to 2000 characters;
- no network access in `SAFE` local tools (monkeypatched socket must not be called).

## Checklist for a new tool

- [ ] Decorator with category and risk.
- [ ] English docstring with an example call.
- [ ] Typed, validated parameters; no `**kwargs`.
- [ ] String result under 1000 characters; errors as `ToolError`.
- [ ] Enabled/disabled switch wired to Settings.
- [ ] Audit fields populated; secrets redacted.
- [ ] Unit tests above, including the risk gate.
- [ ] Entry in the category table and in the tool log labels.
- [ ] `THIRD_PARTY_LICENSES.md` updated if a dependency was added.
