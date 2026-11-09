# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **First-run downloads.** Ollama and Whisper downloads run in parallel during onboarding, report byte-level progress where available, skip assets that are already installed, and can be retried independently.
- **Local Gmail.** Gmail search, read and send over IMAP/SMTP with a Google App Password, with no OAuth client. Drafts and Calendar remain OAuth-only.
- **WhatsApp sharing.** `condividi_whatsapp` opens the official `wa.me` share page with a prefilled message; the user reviews and sends it manually. No personal-account automation.
- **Custom API tools.** User-defined REST endpoints (Exa, Claude, Gemini and others) can be added from Settings and used by the local model through `chiama_api`. Definitions are validated, keys are stored in Credential Manager, requests always require confirmation, and responses are treated as external data.

### Security

- Google app passwords and custom API keys are stored in Windows Credential Manager and are never returned by the API.
- Custom API definitions cannot contain credentials, authentication headers, non-http(s) URLs or traversal paths; only configured base URLs are reachable.

### Known limitations

- Local Gmail does not create drafts; Calendar still requires OAuth.
- The WhatsApp tool is a share link, not an inbox integration.
- Custom APIs are declarative REST integrations. Runtime self-modification is intentionally unsupported; a non-REST protocol needs a new built-in tool and tests.

## [0.1.0] — 2026-11-09

First complete development build. Windows-only paths still need a manual test pass on Windows 10/11.

### Added

- **Backend brain.** FastAPI application on loopback with a per-run session token, WebSocket event protocol, SQLite memory, dynamic tool selection, a six-step agentic loop, self-repair on invalid JSON, confirmation broker, escalation to the online model and automatic fallback to the local model.
- **Local and online models.** Ollama client with tool calling (`qwen3:4b` by default, Q4_K_M, 4096 context) and an OpenAI-compatible online client configured by the user. Mercury and Gemini can be used through compatible endpoints; direct Claude can be exposed as a custom API tool.
- **Tool registry.** `@tool(category, risk)` decorator that builds JSON schemas from type hints and docstrings, with `SAFE`/`CONFIRM`/`DANGEROUS` gating and a SQLite audit log.
- **Tools.** System control (apps, volume, brightness, screenshot, clipboard, PC status, windows), UI automation, file search and read/move/Recycle-Bin delete, exact math and unit conversion, equation solving, charts, sandboxed Python, GitHub, Gmail and Calendar, notes, timers and alarms, clarification.
- **Voice pipeline.** openWakeWord hook, energy VAD, faster-whisper speech-to-text with lazy loading, Piper text-to-speech with a pyttsx3 fallback.
- **Desktop shell.** Tauri 2 frameless window, tray icon with show/quit, close-to-tray, Python sidecar handshake, minimal capability set and restrictive CSP.
- **Interface.** React + TypeScript + Tailwind HUD: animated orb with five states, waveform, home, chat, tool log, settings, onboarding in five steps, confirmation dialog, status bar, low-power mode, and English/Italian/Chinese translation files.
- **Localisation.** One installer with a language choice, interface language switchable at runtime.
- **Build and release.** NSIS configuration, PyInstaller sidecar build, Windows release workflow with checksums, CI for backend, interface, desktop shell and repository hygiene.
- **Documentation.** Installation, languages, design system, tool authoring, Google credentials, security policy and third-party licences.
- **Repository hygiene gate.** Fails on tracked secrets, databases, model files, personal paths and e-mail addresses.

### Security

- API keys and OAuth tokens stored in Windows Credential Manager, never in configuration files.
- Prompt-injection wrapping for external content and a confirmation lockout for risky tools after external reads.
- Sandbox with no network access, a stripped environment, a timeout and a blocked import list.
- No telemetry and no network calls the user did not enable.

### Known limitations

- The Tauri shell, audio devices, Windows automation tools and the NSIS installer are not executed in the Linux development container used to assemble this release. They require a Windows test pass.
- The default wake phrase needs a trained openWakeWord model; without one, wake-word detection stays disabled and the UI says so.
- Fonts fall back to the Windows system stack until the OFL WOFF2 files are added to `ui/src/assets/fonts/`.

## [0.0.0] — not released

Initial commit: project name and one-line description.
