# Security Policy

VEYRA is a desktop assistant with access to the user's applications, files, e-mail and calendar. Its security model is intentionally conservative: local by default, explicit confirmation for anything risky, and no telemetry.

## Supported versions

| Version | Supported |
| --- | --- |
| 0.1.x | Development only — no public release yet |
| Older | Not applicable |

There is no published build at this stage. This table will be updated with the first release.

## Reporting a vulnerability

Use GitHub's **private vulnerability reporting** on this repository:

1. Open the **Security** tab.
2. Choose **Report a vulnerability**.
3. Describe the issue in the private advisory form.

Please do not open a public issue for a security problem, and do not include live API keys, OAuth tokens, chat transcripts, private e-mail content or personal paths in any report. Redact them; a description of the shape of the problem is enough.

A useful report contains:

- the affected component or phase (backend, tool layer, Tauri shell, installer, UI);
- Windows version and VEYRA version or commit;
- reproduction steps, expected and actual behaviour;
- the impact you believe it has;
- an optional suggested fix.

No e-mail address is required.

## What to expect

This is a volunteer project, so these are best-effort targets rather than a contractual SLA:

| Stage | Target |
| --- | --- |
| Acknowledgement | 7 days |
| Initial assessment | 14 days |
| Fix for confirmed high-severity issues | 30 days |

Reporters are credited in the advisory unless they ask to stay anonymous.

## Security controls in the design

| Area | Control |
| --- | --- |
| Transport | Backend binds to `127.0.0.1` only, on a random free port chosen at startup |
| Authentication | Per-run session token, required on every HTTP request and WebSocket message; regenerated on each start |
| Secrets at rest | API keys and OAuth tokens in Windows Credential Manager through `keyring`; never in `config.json`, never logged |
| Tool risk | Every tool declares `SAFE`, `CONFIRM` or `DANGEROUS`; confirmation is required in the UI and, for high risk, summarized before execution |
| Prompt injection | External content (mail, web, files) is wrapped in `<dati_esterni fonte="...">` blocks and marked as data; after such content is read in a turn, `CONFIRM`/`DANGEROUS` tools stay blocked until the user confirms |
| Code execution | `esegui_python` runs in a separate process with a timeout, no network, and no access to user document folders |
| Desktop shell | Minimal Tauri allowlist, restrictive CSP, no remote origins in the webview, no `eval` of untrusted content |
| Network | No telemetry, no analytics, no background polling; online providers are opt-in per integration |
| Logs | Redacted: keys, tokens, message bodies and file contents are never written to disk |

## Threat model

In scope:

- a malicious or compromised online model provider returning hostile content;
- prompt injection through e-mail, issue text, web pages or files;
- a compromised dependency in the supply chain;
- another local process on the same machine trying to reach the backend;
- accidental disclosure of secrets through logs, crash reports or the repository.

Out of scope:

- an attacker with administrator rights or physical access to an unlocked machine;
- malware already running in the user's session;
- a tampered Ollama binary or a malicious model file installed by the user;
- how third-party providers (online model API, Google, GitHub) handle data they receive;
- denial of service caused by the user's own machine being out of memory.

## Secrets for contributors

- Local development may use a `.env` file with invented values. `.env` is git-ignored; `.env.example` contains placeholders only.
- Never paste a real key into an issue, pull request, test fixture, screenshot or commit.
- If a secret is committed by accident, revoke and rotate it first, then ask for history cleanup. Removing the file in a later commit is not enough.
- Run `python scripts/check_hygiene.py` before pushing; CI runs the same check.

## Dependency policy

Only permissive licenses are shipped (MIT, Apache-2.0, BSD, ISC, PSF, OFL, public domain). Additions are recorded in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md). Optional proprietary components — such as a user-supplied Porcupine access key or a commercial online model API — are never bundled and never required.
