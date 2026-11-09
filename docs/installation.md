# Installation

> **Status:** the application and the installer pipeline are implemented. This document covers the developer setup that works today and the end-user flow produced by the Windows release workflow. Windows-only steps still need a manual test pass.

## End-user requirements

| Item | Requirement |
| --- | --- |
| Windows | 10 21H2 or newer, or Windows 11; 64-bit |
| RAM | 8 GB total; VEYRA targets about 4 GB |
| Free disk | ≈ 5 GB (application plus downloaded models) |
| WebView2 | Preinstalled on Windows 11, distributed by Microsoft to Windows 10; the installer verifies it |
| Ollama | Required for the local model; installed separately |
| Microphone | Optional; the app is fully usable with the keyboard |
| Internet | Optional; only for online features you enable |

## Install flow

1. Download the single release asset for Windows x64, `Veyra_<version>_x64-setup.exe`.
2. Run it and choose the setup language: **English**, **Italiano** or **简体中文**. This is one installer with a language selector, not three separate builds.
3. Choose the install directory (default per-user, no administrator rights needed).
4. Finish setup; VEYRA starts and shows the onboarding wizard.

Windows SmartScreen may warn about an unsigned build. Until releases are code-signed, verify the SHA-256 checksum published with the release before running the installer.

## First-run onboarding

1. **Ollama check** — detect the local service and its version, with a link to the official installer if missing.
2. **Model download** — pull the default local model with visible progress and size, or pick another installed model.
3. **Microphone test** — permission check, level meter, device selection.
4. **Voice test** — short spoken sample, volume and voice selection.
5. **Language and wake word** — interface language, assistant name, wake word.
6. **Privacy summary** — what runs locally, what would leave the machine, and what stays off until enabled.

Everything in onboarding can be skipped and revisited in Settings.

## Developer prerequisites

| Tool | Version | Needed from |
| --- | --- | --- |
| Python | 3.11 | Backend and tools |
| Ollama | current | Local model |
| Node.js | 20 LTS | Interface build |
| Rust toolchain + MSVC build tools | stable | Desktop shell |
| WebView2 runtime | current | Desktop shell |

From the repository root:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\pip install -r backend\requirements-windows.txt
npm --prefix ui install
npm install
npm run dev
```

Or, to run the two halves separately during development:

```powershell
.venv\Scripts\python -m backend.main --port 8765 --token dev-token
npm --prefix ui run dev
```

Repository checks:

```bash
python scripts/check_hygiene.py
ruff check backend && pytest -q backend/tests
npm --prefix ui run build
```

## Where data is stored

| Location | Contents | Removed by uninstall |
| --- | --- | --- |
| `%APPDATA%\Veyra\config.json` | settings, no secrets | kept by default |
| `%APPDATA%\Veyra\veyra.db` | notes, chat history, timers, tool log | kept by default |
| `%APPDATA%\Veyra\logs\` | rotating redacted logs | kept by default |
| `%APPDATA%\Veyra\models\` | downloaded speech models | kept by default |
| Windows Credential Manager | keys and OAuth tokens | removed when the user deletes them in Settings |

Nothing is written into the installation directory. Settings → Privacy → “Delete my data” removes the Veyra folder and its credential entries after an explicit confirmation.

## RAM budget

These are design targets to be measured in the phase that introduces each component:

| Component | Target resident memory |
| --- | --- |
| Tauri shell + WebView2 UI | 200–300 MB |
| Local LLM (Qwen3-4B Q4_K_M, 4096 context) | 2.5–3.0 GB while loaded |
| faster-whisper `base` int8 | 200–300 MB while loaded |
| Piper voice | 100–200 MB while speaking |
| Backend, SQLite, misc | 150–250 MB |
| **Total, worst case** | **≈ 3.5–4.0 GB** |

Rules that keep it there:

- Only one LLM is ever loaded.
- STT and TTS load lazily and unload when idle, or when free RAM drops below `VEYRA_RAM_FLOOR_MB`.
- Context is capped at 4096 tokens.
- Low-power mode disables WebGL, grain, and continuous animation.
- No local vision model exists in the product.

## Windows troubleshooting (planning notes)

| Symptom | Likely cause | Check |
| --- | --- | --- |
| Window opens blank | WebView2 missing or outdated | install the Evergreen WebView2 Runtime |
| “Local model unavailable” | Ollama not running | `ollama list`, start the Ollama service |
| Model download stalls | network or disk space | free space on the drive holding the Ollama models |
| No audio input | microphone privacy setting | Settings → Privacy → Microphone |
| TTS silent | voice not downloaded | download the voice in Settings → Voice |
| Installer blocked | unsigned build | verify checksum; do not disable SmartScreen permanently |
| High memory use | model too large or two models loaded | switch to the 4B model, enable low-power mode |
| Port error | another process holds the port | restart VEYRA; the port is chosen at random each start |

## Removing VEYRA

The planned uninstaller removes the application and the autostart entry, and keeps `%APPDATA%\Veyra` so settings and notes survive a reinstall. To remove everything, delete that folder and the VEYRA entries in Windows Credential Manager, or use “Delete my data” in Settings before uninstalling.
