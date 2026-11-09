# Documentation

Specifications and guides for VEYRA. Everything here is written in English; user-facing text in the application is translated separately.

| Document | Contents | Needed from |
| --- | --- | --- |
| [installation.md](installation.md) | Requirements, install flow, data locations, RAM budget, Windows troubleshooting | Phase 1 (dev), Phase 12 (users) |
| [languages.md](languages.md) | One installer, three languages; i18n layout; what stays English | Implemented |
| [design-system.md](design-system.md) | Colour tokens, contrast, typography, surfaces, orb states, motion, low-power mode | Phase 4 |
| [adding-a-tool.md](adding-a-tool.md) | Tool contract, risk levels, schemas, audit log, tests | Phase 2 |
| [custom-apis.md](custom-apis.md) | Custom REST tools, OpenAI-compatible providers, key storage and safety boundaries | Implemented |
| [google-oauth.md](google-oauth.md) | Creating your own Google credentials for Gmail and Calendar | Phase 9 |

## Status

The application is implemented in this repository. The Python backend and the React interface run their automated checks on every push; Windows-only components (Tauri shell, audio devices, desktop automation, NSIS installer) need a manual test pass on Windows before a public release.

Commands marked *planned* in these documents describe the intended end-user flow rather than something the development container could execute.

## Conventions used in these documents

- Paths are relative or derived from the system (`%APPDATA%`, `%LOCALAPPDATA%`). Absolute user directories never appear in the repository.
- “Must” describes a requirement, “should” a strong recommendation, “planned” an item scheduled for a later phase.
- Example values are invented. Placeholder keys are not valid credentials.
