# Third-party licenses

VEYRA ships only components whose licenses allow redistribution in an MIT-licensed application. This file records the planned inventory and the policy for adding to it.

> **Status:** current inventory for 0.2.0. Dependency versions are pinned in `backend/requirements*.txt`, `ui/package-lock.json`, `package-lock.json` and `src-tauri/Cargo.toml`. Before the first public release this file is regenerated from a machine-readable audit (`pip-licenses`, `cargo-license`, `license-checker`) and reviewed by hand.

## Policy

Allowed for shipped runtime code:

- MIT, ISC, BSD-2-Clause, BSD-3-Clause, Apache-2.0, PSF-2.0, Zlib, public domain;
- MPL-2.0 libraries, unmodified, with their source available upstream;
- SIL OFL 1.1 for bundled fonts;
- build-only tools under GPL with an explicit exception that permits distributing the resulting application (PyInstaller).

Not allowed in shipped runtime code without an explicit decision recorded here: GPL, AGPL, LGPL, SSPL, Commons Clause, non-commercial, "source available" or unclear custom licenses.

Optional proprietary components are never bundled and never required: the user supplies their own key or account, and the component remains under its own terms.

---

## Application shell

| Component | Role | License | Notes |
| --- | --- | --- | --- |
| Tauri 2 | Desktop shell | MIT OR Apache-2.0 | Rust; uses the system WebView2 |
| Wry / Tao | WebView and window glue (Tauri) | MIT OR Apache-2.0 | transitive |
| Microsoft Edge WebView2 Runtime | Rendering engine | Microsoft proprietary redistributable | Required system component; the installer checks for it instead of bundling Chromium |
| Rust standard library and crates | Shell runtime | MIT OR Apache-2.0 | audited per release |

## Interface

| Component | Role | License | Notes |
| --- | --- | --- | --- |
| React, React DOM | UI runtime | MIT | |
| TypeScript | Language toolchain | Apache-2.0 | build time |
| Vite | Dev server and bundler | MIT | build time |
| Tailwind CSS | Styling | MIT | |
| Framer Motion | Micro-animations | MIT | disabled in low-power mode |
| Rajdhani | Display / HUD typeface | SIL OFL 1.1 | bundled, license text included |
| Inter | Interface text typeface | SIL OFL 1.1 | bundled, license text included |
| JetBrains Mono | Logs and code typeface | SIL OFL 1.1 | bundled, license text included |

No icon font is planned; icons are inline SVG drawn in-house to keep the bundle small.

## Backend and speech

| Component | Role | License | Notes |
| --- | --- | --- | --- |
| Python 3.11 | Runtime | PSF-2.0 | |
| FastAPI | HTTP and WebSocket API | MIT | |
| Uvicorn | ASGI server | BSD-3-Clause | |
| Pydantic | Schema validation | MIT | |
| websockets | WebSocket transport | BSD-3-Clause | |
| HTTPX | HTTP client for providers | BSD-3-Clause | replaces PyGithub to avoid LGPL |
| python-dotenv | Developer `.env` loading | BSD-3-Clause | end users never need it |
| keyring | Windows Credential Manager access | MIT | |
| Ollama | Local model runtime | MIT | installed separately by the user, not bundled |
| Qwen3-4B (Q4_K_M) | Default local model | Apache-2.0 | downloaded by the user through Ollama |
| faster-whisper | Speech-to-text | MIT | lazy loaded |
| CTranslate2 | Inference engine for Whisper | MIT | |
| Whisper `base` weights | STT model | MIT | downloaded on demand |
| openWakeWord | Default wake-word engine | Apache-2.0 | no key required |
| ONNX Runtime | Inference for openWakeWord | MIT | |
| Silero VAD | Voice activity detection | MIT | preferred VAD |
| webrtcvad | Alternative lightweight VAD | MIT | fallback |
| sounddevice | Audio capture | MIT | PortAudio binding |
| PortAudio | Audio I/O | MIT | |
| Piper | Text-to-speech | MIT | |
| Piper voice models | Voices | varies per voice | **not bundled**: downloaded on demand, only voices whose license permits redistribution/use are offered |
| pyttsx3 | TTS fallback | MPL-2.0 | unmodified, used only when Piper is unavailable |
| NumPy | Numerics | BSD-3-Clause | |
| SciPy | Numerics for sandbox | BSD-3-Clause | |
| SymPy | Exact math and equations | BSD-3-Clause | |
| numexpr | Fast expression evaluation | MIT | |
| Matplotlib | Charts from tools | PSF-compatible BSD-style (Matplotlib license) | |
| Pillow | Image handling | MIT-CMU (HPND) | |
| PyInstaller | Sidecar packaging | GPL-2.0-or-later **with bootloader exception** | build tool; the exception permits distributing the bundled application |

## Windows integration

| Component | Role | License | Notes |
| --- | --- | --- | --- |
| psutil | System status | BSD-3-Clause | |
| pyperclip | Clipboard | BSD-3-Clause | |
| pycaw | Audio endpoints | MIT | |
| comtypes | COM bindings for pycaw | MIT | |
| pywin32 | Windows APIs | PSF-2.0 | |
| pyautogui | Keyboard and mouse control | BSD-3-Clause | |
| pywinauto | Window management | BSD-3-Clause | |
| mss | Screenshots | MIT | |
| SQLite (via `sqlite3`) | Local memory | Public domain | stdlib module |

## Integrations (optional, user-configured)

| Component | Role | License | Notes |
| --- | --- | --- | --- |
| GitHub REST API | Repository, issue and commit tools | API terms of service | called with the user's personal token; no client library shipped |
| google-api-python-client | Gmail and Calendar tools | Apache-2.0 | |
| google-auth, google-auth-oauthlib | Google OAuth flow | Apache-2.0 | each user creates their own OAuth client |
| Mercury 3 (Inception Labs) | Optional online model | Commercial API | not redistributed; used only with the user's own key and explicit opt-in |

## Installer and build tooling

| Component | Role | License |
| --- | --- | --- |
| NSIS | Windows installer | Zlib/libpng |
| GitHub Actions runners | CI and release builds | GitHub terms |
| Ruff | Python lint and format | MIT |
| pytest | Python tests | MIT |
| ESLint | TypeScript lint | MIT |

## Fonts

The three typefaces are distributed under the SIL Open Font License 1.1. Their `OFL.txt` files are placed next to the font files in `ui/src/assets/fonts/` and are not modified. The fonts may be bundled with the application but not sold on their own.

## Voice and model assets

Speech models are **downloaded by the user at runtime**, not committed and not shipped in the installer. This keeps the repository small, avoids redistributing weights with unclear provenance, and lets the license of each voice be checked individually. The download screen in onboarding shows the license and source of every asset before it is fetched.

## Attribution in the application

The About panel in Settings lists VEYRA's MIT license and links to this file. Third-party notices required by Apache-2.0 and OFL are included in the installed application's `licenses/` folder.

## Reporting a licensing problem

If you believe a component is listed incorrectly or a shipped asset is not covered, open an issue (without pasting proprietary material) or use the private advisory form described in [SECURITY.md](SECURITY.md).
