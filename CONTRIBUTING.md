# Contributing to VEYRA

Thanks for taking the time to help. VEYRA is a Windows desktop assistant that has to stay small, private and predictable, so the rules below are stricter than in a typical hobby project.

## Ground rules

1. **English in the repository.** Code, identifiers (except the tool names defined by the product specification), comments, docstrings, log messages, commit messages, issues and documentation are written in English. User-facing strings are translated through i18n files only.
2. **No personal data.** No real names, e-mail addresses, account IDs, machine names, user directory paths or screenshots containing them. Example paths use `%APPDATA%` or relative paths.
3. **No secrets.** No API keys, access tokens, cookies or private keys — not in code, not in tests, not in fixtures, not in issue reports. Real values belong in Windows Credential Manager at runtime.
4. **Respect the memory budget.** Target is about 4 GB of RAM on an 8 GB machine. New dependencies must justify their memory and startup cost. Never keep two LLMs loaded.
5. **Permissive dependencies only.** Shipped runtime code must use MIT, Apache-2.0, BSD, ISC, PSF, OFL or public-domain components. Anything else needs a discussion and an entry in `THIRD_PARTY_LICENSES.md` first.
6. **No hidden network calls and no telemetry.** Anything that leaves the machine must be user-enabled and documented.
7. **Errors are data.** A failed tool, a missing model or a dropped connection must be reported to the user and the model; it must never crash the app.

## Commit and attribution policy

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `build:`, `ci:`, `chore:`.
- One logical change per commit; explain *why* in the body when it is not obvious.
- **Do not add tool or agent attribution.** No “Generated with …” lines, no co-author trailers for bots, assistants or code generators. A commit is attributed to the humans who wrote and reviewed it.
- Keep commit messages and branch names free of personal paths, tokens and machine names.
- Do not commit generated artefacts: models, databases, logs, build output, installers.

## Development setup

The toolchain is Windows-oriented. Build and run commands are in [docs/installation.md](docs/installation.md) and the repository README.

Prerequisites for the full application:

| Tool | Version | Used from |
| --- | --- | --- |
| Windows | 10 21H2+ / 11, 64-bit | all phases |
| Python | 3.11 | Phase 1 |
| Node.js | 20 LTS | Phase 4 |
| Rust + MSVC build tools | stable | Phase 4 |
| Ollama | current | Local development only; release builds bundle the portable runtime |
| WebView2 runtime | current | Phase 4 |

Run the repository hygiene gate before every commit:

```bash
python scripts/check_hygiene.py
```

It fails on tracked secrets, databases and model files, and on personal paths or e-mail addresses anywhere in the tree.

## Code style

**Python**

- `ruff` for lint and formatting; type hints on public functions.
- Docstrings in English, short and factual.
- `logging`, never `print`.
- No bare `except`; catch specific exceptions and return a user-safe message.
- Never trust model output: validate JSON, clamp numbers, check paths and tool names.
- No `shell=True`, no `eval`, no dynamic import of model-provided names.

**TypeScript / React**

- `strict` mode, no `any` without a comment explaining why.
- Function components and hooks; no class components.
- No inline colours, no arbitrary hex values: use the design tokens from `docs/design-system.md`.
- All user-visible text through i18n keys.

**Rust**

- `cargo fmt` and `cargo clippy -- -D warnings`.
- Minimal Tauri permissions; every new capability needs a justification in the pull request.

## Pull requests

A pull request is ready when:

- [ ] `python scripts/check_hygiene.py` passes.
- [ ] The relevant phase checks pass (`ruff`, `pytest`, `npm run build`, `cargo clippy` once they exist).
- [ ] New behaviour is documented, and `CHANGELOG.md` has an entry under `Unreleased`.
- [ ] No secrets, personal data, model files or build output are included.
- [ ] Tool changes follow [docs/adding-a-tool.md](docs/adding-a-tool.md) and declare a category and a risk level.
- [ ] New user-facing strings exist in every supported language file, or are marked as untranslated.

Keep pull requests focused. Unrelated refactors in the same change make review slow and are usually asked to be split.

## Adding a tool

Read [docs/adding-a-tool.md](docs/adding-a-tool.md). In short: decorate with `@tool(category=..., risk=...)`, write a short English docstring containing an example, return a string, raise `ToolError` for expected failures, and add a test that does not touch the real system.

## Translations

The interface ships in English, Italian and Simplified Chinese. See [docs/languages.md](docs/languages.md) for the file layout and the rule that the repository itself stays English.

## Reporting a security issue

Do not open a public issue. Follow [SECURITY.md](SECURITY.md).

## Code of conduct

Be civil and technical. This project adopts the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). Harassment, personal attacks and disclosure of another person's private information are not acceptable.
