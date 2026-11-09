# ui/ — React + TypeScript interface

> **Status: implemented.** React + TypeScript + Vite + Tailwind interface with the orb, waveform, chat, tool log, settings, onboarding and the IT/EN/ZH dictionaries.

Layout:

```
ui/
├── src/
│   ├── components/      # Orb, Waveform, Chat, ToolLog, ConfirmDialog, Settings...
│   ├── screens/         # Home, Chat, ToolLog, Settings, Onboarding
│   ├── state/           # WebSocket client, orb state store, settings store
│   ├── theme/           # tokens.css (single source of literal colours)
│   ├── i18n/            # en.json, it.json, zh.json, typed t() helper
│   └── assets/          # fonts (WOFF2 + OFL.txt), static SVG icons
├── index.html
├── package.json
├── tailwind.config.ts
└── vite.config.ts
```

Non-negotiable rules:

- All colours come from the tokens in [../docs/design-system.md](../docs/design-system.md); no literal hex values in components.
- All user-visible strings come from i18n files, not JSX literals.
- No Electron and no heavy UI framework: React, Vite, Tailwind and Framer Motion only.
- Canvas animation stops when the window is hidden or low-power mode is on.
- The UI never talks to the network directly; it talks to the local backend over the authenticated WebSocket.
