# Releasing VEYRA

The release is tag-driven and always starts as a GitHub draft. Do not publish the
draft until the Windows acceptance checks below pass.

## Version gate

All of these manifests must carry the same version:

- `package.json` and `package-lock.json`
- `ui/package.json` and `ui/package-lock.json`
- `src-tauri/Cargo.toml`, `src-tauri/Cargo.lock` and `src-tauri/tauri.conf.json`
- `backend/__init__.py`

Run the gate before committing a release change:

```bash
python scripts/check_versions.py
```

For a tag, the gate also checks the tag name:

```bash
python scripts/check_versions.py --tag v1.0.0
```

CI runs the same check on every pull request and push to `main`.

## Windows acceptance checklist

Run this on a clean Windows 10 21H2+ or Windows 11 x64 machine before tagging:

- [ ] Install per-user from the NSIS installer; no administrator prompt is required for the install itself.
- [ ] First launch starts the bundled Ollama runtime; no separate Ollama installation or setup card appears.
- [ ] Onboarding downloads `qwen3:4b`, the Whisper model and the Piper voice automatically; a local chat completes while offline.
- [ ] Restarting VEYRA does not download the same assets again; models are under `%APPDATA%\Veyra\ollama\models` and voices under `%APPDATA%\Veyra\voices`.
- [ ] Skipping onboarding is persisted after a restart.
- [ ] Microphone input, local transcription, spoken replies and timer reminders work.
- [ ] With a trained openWakeWord model selected in Settings → Audio, the wake phrase starts a listening turn; without one, the app stays in push-to-talk mode.
- [ ] A safe tool, a confirmation tool and a rejected confirmation behave as documented.
- [ ] Reading external content blocks a subsequent CONFIRM or DANGEROUS tool in the same turn without opening a prompt.
- [ ] “Delete my data” clears chat history, notes, tool logs, settings, downloaded models, voices and credentials after confirmation, and the app requires a restart.
- [ ] The mini widget can be enabled/disabled in Settings, stays on top and does not duplicate the backend.
- [ ] Autostart and close-to-tray can be toggled; a second launch does not start a second backend.
- [ ] The app stays in the tray when the window is closed, and Quit stops the backend and Ollama.
- [ ] The uninstaller removes the application and leaves user data intact unless the user chooses to remove it.
- [ ] The published SHA-256 matches the installer, and the installer size is below the release limit.

Record the Windows version, installer size and any failures in the release notes.

## Tag and draft

Only after the checklist passes:

```bash
git tag -a v1.0.0 -m "VEYRA 1.0.0"
git push origin v1.0.0
```

The release workflow verifies the tag against the version manifests, runs the
backend tests on Windows, builds the backend sidecar and installer, downloads
the pinned portable Ollama runtime, and writes `checksums.txt`. It creates a
draft GitHub release; review the assets and notes, then publish it manually.

A manual `workflow_dispatch` run builds and uploads the workflow artifacts but
does not create a GitHub release; only a `v*` tag triggers the draft release
step.

## Release constraints

- The bundled Ollama archive is about 1.5 GB. The installer and GitHub asset
  limits must be checked on the actual Windows runner.
- The sidecar bundles `piper-tts`, `piper-phonemize` and ONNX Runtime. Confirm
  the PyInstaller output starts and `PiperVoice.load()` succeeds on Windows.
- The Piper voice files are downloaded from the pinned `rhasspy/piper-voices`
  `v1.0.0` revision during onboarding, not shipped in the installer.
- Installers are unsigned until code signing is configured. SmartScreen may
  warn; publish the SHA-256 and never ask users to disable security checks.
- The default wake phrase needs a trained openWakeWord model; without one the
  feature stays disabled and the UI says so.
