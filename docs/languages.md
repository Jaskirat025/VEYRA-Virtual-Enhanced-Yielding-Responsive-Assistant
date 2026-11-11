# Languages

## The decision

VEYRA ships **one installer** with a language choice, not one build per language.

| Layer | Behaviour |
| --- | --- |
| Installer | NSIS asks for English, Italiano or 简体中文 at the start of setup |
| Application UI | English / Italiano / 中文, changeable in Settings → Language |
| Spoken answers | VEYRA answers in the language the user speaks |
| Code, comments, docstrings, logs, commits, docs | English only |

Why one build:

- One artefact to build, sign, checksum and test instead of three 100+ MB downloads.
- No risk of three builds drifting apart in behaviour.
- The user can change language after installation without reinstalling.
- Maintenance cost stays with translations, not with release engineering.

A per-language download page would duplicate binaries without adding capability, so it is explicitly not planned.

## What is translated

- All interface strings: navigation, labels, tooltips, empty states, buttons.
- Onboarding steps and permission explanations.
- User-visible error messages and confirmation dialogs.
- Tool display names and descriptions shown in the tool log and settings.
- Installer pages.

## What stays English

- Source code, identifiers, comments and docstrings.
- Log messages (they are diagnostic, not product copy).
- Tool schemas and model-facing descriptions: these are prompts, and mixed-language prompts measurably hurt small-model tool calling.
- Repository documentation, commit messages, issue templates and changelog.
- The wake word phrase is configurable, not translated. The default “Ehi Veyra” is a phrase, not UI copy.

## Planned file layout

```
ui/src/i18n/
├── index.ts        # typed dictionary loader, t() helper, locale detection
├── en.json         # source of truth
├── it.json
└── zh.json
```

Rules:

- Flat, namespaced keys: `home.orb.idle`, `settings.apiKeys.save`, `tools.closeApp.risk.confirm`.
- No string concatenation in components; placeholders use `{name}` and are substituted by `t()`.
- No runtime i18n framework. A typed dictionary plus `t()` costs a few kilobytes and no extra parse time, which matters on an 8 GB machine. It also makes missing keys a TypeScript error.
- A key that exists in `en.json` but not in another locale falls back to English and is reported in development mode.
- A CI check (Phase 10) verifies that all locale files have the same key set.

## Chinese typography

Rajdhani and Inter do not cover CJK glyphs. Instead of bundling a multi-megabyte CJK font, the interface uses the Windows system stack for Chinese: `"Microsoft YaHei UI", "Microsoft YaHei", "Noto Sans SC", sans-serif`. This keeps the installer small and rendering native. The HUD typeface remains Rajdhani for Latin labels and numerals.

## Adding a language

1. Copy `en.json` to `<locale>.json` and translate the values, not the keys.
2. Add the locale to the dictionary registry and to the Settings language list.
3. Add the NSIS language entry so setup can offer it.
4. Check that no string overflows its container; German and Chinese lengths differ substantially from English.
5. Run the key-parity check and the hygiene check.
6. Add the language to the table above and to `CHANGELOG.md`.

Right-to-left languages are not supported yet; they would require layout mirroring that is out of scope for the first release.

## Model and voice languages

- The local model is multilingual; answers follow the system prompt rule “reply in the user's language”.
- Whisper handles multiple languages, with the language hint configurable (auto-detect by default).
- Piper needs one voice per language. The language-matched voice is downloaded during onboarding from the pinned `rhasspy/piper-voices` revision; the source and voice licence are documented in [THIRD_PARTY_LICENSES.md](../THIRD_PARTY_LICENSES.md).
