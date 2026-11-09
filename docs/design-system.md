# Design system

> **Status:** implemented in `ui/src/index.css` and `ui/tailwind.config.ts`. This document is the single source of truth for colour, type, surfaces and motion; the interface must not introduce values outside these tokens.

## Intent

A clean science-fiction HUD: calm, precise, engineered. Metal and glass, thin lines, wide-tracked labels. Never cartoonish, never saturated neon, never decorative noise that costs frames.

## Colour: the 60 / 30 / 10 rule

| Role | Token | Hex | Share | Used for |
| --- | --- | --- | --- | --- |
| Structure | `--vy-gunmetal-700` | `#2A3439` | 60% | window background, main panels |
| Depth | `--vy-gunmetal-800` | `#1E262A` | | raised panels, cards, inputs |
| Depth | `--vy-gunmetal-900` | `#161C1F` | | wells, log surface, app frame |
| Structure | `--vy-silver-300` | `#C5CBD0` | 30% | borders, icons, secondary surfaces, separators |
| Text | `--vy-silver-100` | `#E4E8EB` | | primary text |
| Text | `--vy-silver-400` | `#9AA3AA` | | secondary text on gunmetal (derived, AA-safe) |
| Text | `--vy-silver-500` | `#8B949B` | | secondary text on the darkest surface only |
| Accent | `--vy-accent-500` | `#FF5A1F` | 10% | active orb, primary button, wake-word hit, listening indicator, focus ring, confirmation borders |
| Accent | `--vy-accent-600` | `#E64A12` | | pressed state of accent fills (derived) |
| Accent | `--vy-ink-on-accent` | `#161C1F` | | label inside accent fills |

`--vy-silver-400` is a derived value, not a new brand colour: `#8B949B` reaches only ≈4.1:1 on `#2A3439`, which fails WCAG AA for normal text. The slightly lighter neutral keeps the same visual role and passes.

Orange never covers a large surface. It appears as a fill on small controls, a 1 px line, an icon, an orb state, or a focus ring.

## Contrast (WCAG 2.1, computed with the relative-luminance formula)

| Foreground | Background | Ratio | Verdict |
| --- | --- | --- | --- |
| `#E4E8EB` | `#2A3439` | ≈ 10.3 : 1 | AAA |
| `#E4E8EB` | `#161C1F` | ≈ 14.0 : 1 | AAA |
| `#9AA3AA` | `#2A3439` | ≈ 5.0 : 1 | AA normal text |
| `#8B949B` | `#161C1F` | ≈ 5.6 : 1 | AA normal text |
| `#8B949B` | `#2A3439` | ≈ 4.1 : 1 | large text and non-essential only |
| `#FF5A1F` | `#2A3439` | ≈ 4.1 : 1 | not body text; large text (≥ 18.7 px bold / 24 px) and UI edges only |
| `#161C1F` | `#FF5A1F` | ≈ 5.5 : 1 | label text on accent fills |

Rules that follow from this table:

- Body text uses `--vy-silver-100`; secondary text uses `--vy-silver-400` on gunmetal and may use `--vy-silver-500` only on `--vy-gunmetal-900`.
- Primary buttons are accent fills with near-black labels, never white labels.
- Status is never conveyed by colour alone: every state also has a label or an icon.

## CSS tokens

Planned location: `ui/src/theme/tokens.css`, imported once and exposed to Tailwind through `theme.extend`.

```css
:root {
  /* Surfaces — 60% */
  --vy-gunmetal-700: #2a3439;
  --vy-gunmetal-800: #1e262a;
  --vy-gunmetal-900: #161c1f;

  /* Silver — 30% */
  --vy-silver-100: #e4e8eb;
  --vy-silver-300: #c5cbd0;
  --vy-silver-400: #9aa3aa;
  --vy-silver-500: #8b949b;

  /* Accent — 10% */
  --vy-accent-500: #ff5a1f;
  --vy-accent-600: #e64a12;
  --vy-accent-soft: rgba(255, 90, 31, 0.12);
  --vy-ink-on-accent: #161c1f;

  /* Lines and glows, always alpha-based so surfaces stay readable */
  --vy-line: rgba(197, 203, 208, 0.14);
  --vy-line-strong: rgba(197, 203, 208, 0.28);
  --vy-glow-accent: 0 0 24px rgba(255, 90, 31, 0.35);

  /* Type */
  --vy-font-display: "Rajdhani", "Segoe UI", sans-serif;
  --vy-font-body: "Inter", "Segoe UI", "Microsoft YaHei UI", sans-serif;
  --vy-font-mono: "JetBrains Mono", "Cascadia Mono", monospace;

  /* Geometry */
  --vy-space-1: 4px;
  --vy-space-2: 8px;
  --vy-space-3: 12px;
  --vy-space-4: 16px;
  --vy-space-6: 24px;
  --vy-space-8: 32px;
  --vy-radius-sm: 4px;
  --vy-radius-md: 8px;
  --vy-radius-panel: 10px;
  --vy-cut: 14px; /* clipped corner size */
  --vy-line-width: 1px;

  /* Motion */
  --vy-dur-fast: 150ms;
  --vy-dur-base: 220ms;
  --vy-dur-slow: 300ms;
  --vy-ease: cubic-bezier(0.2, 0.8, 0.2, 1);
  --vy-ease-out: cubic-bezier(0.16, 1, 0.3, 1);

  /* Elevation: metal, not drop shadow */
  --vy-inset-top: inset 0 1px 0 rgba(228, 232, 235, 0.06);
  --vy-shadow-panel: 0 12px 32px rgba(0, 0, 0, 0.35);
}
```

## Typography

| Role | Family | Size / weight | Notes |
| --- | --- | --- | --- |
| Window title | Rajdhani | 15 px / 600 | uppercase, tracking 0.14em |
| Screen title | Rajdhani | 24 px / 600 | |
| HUD label | Rajdhani | 11 px / 600 | uppercase, tracking 0.16em, `--vy-silver-400` |
| Numeric readout | Rajdhani | 13–18 px / 600 | tabular figures |
| Body | Inter | 14 px / 400, line-height 1.5 | primary text 16 px in chat |
| Secondary | Inter | 12.5 px / 400 | `--vy-silver-400` |
| Log, code, tool args | JetBrains Mono | 12.5 px / 400, line-height 1.6 | `--vy-gunmetal-900` surface |

Fonts are self-hosted in `ui/src/assets/fonts/` as WOFF2 with their `OFL.txt`. Fallback stacks include the Windows system fonts and a CJK family so Chinese never renders as boxes. See [languages.md](languages.md).

## Surfaces and language

- **Panels:** one-pixel `--vy-line` border, a faint top highlight, slightly darker fill, and one or two clipped corners. The clipped corners are the recurring signature of the interface.
- **Hairline technique:** a clipped element loses its own border on the cut edge. Draw the outline on a wrapper filled with the line colour and place the clipped surface 1 px inside it. Do not fake it with a shadow.
- **Background:** `--vy-gunmetal-700` with a technical grid at 2–3% opacity, 32 px cells, plus a static grain tile at 3–4% opacity. The grain is a 64×64 px PNG repeated, not an animated shader.
- **Glass:** at most one blurred layer per screen (`backdrop-filter: blur(12px)`), used for overlays. Never on scrolling lists.
- **Glow:** accent glow only on the active orb and the focused primary control.
- **Iconography:** 1.5 px stroke inline SVG, currentColor, 16 px and 20 px grids, no filled decorative icons.

## The orb

The orb is the identity of the product and the only element allowed to animate continuously. It is Canvas 2D by default, with a WebGL variant only if measured cheaper; both read the same state store.

| State | Colour | Motion | Duration |
| --- | --- | --- | --- |
| Idle | silver core, silver edges | slow breathing, scale 0.98 → 1.02 | 6 s loop |
| Listening | accent ring, accent waveform | 2–3 expanding rings, 40 ms audio-driven jitter | continuous while active |
| Thinking | silver core, accent segments | segments rotate at different speeds, subtle pulse | 1.8 s loop |
| Speaking | accent core | sphere deforms to the output waveform envelope | audio-reactive |
| Error | accent flash, then silver | 2 quick flashes, no shake | 400 ms total |
| Offline model unavailable | silver, desaturated | static, with a text label | none |

Rules:

- Idle animation is CSS transform only; no `requestAnimationFrame` loop when nothing is happening.
- Frames are capped at 30 fps; the loop pauses on `visibilitychange` and when the window is minimized.
- In low-power mode the orb becomes a static SVG with a 2-state transition (idle/listening) and no glow.
- The orb is `aria-hidden`; state is also announced through a visible status label and `aria-live` text.

## Waveform

- Input meter: 32–48 bars, peak-normalized, 30 fps, drawn to a single canvas.
- Output meter: same component, accent colour, fed by the TTS envelope rather than a microphone.
- No historical scrolling graph on the home screen; that belongs to the tool log.
- Reduced-motion mode replaces bars with a 3-level activity indicator.

## Motion

| Interaction | Duration | Easing |
| --- | --- | --- |
| Hover, focus, small fades | 150 ms | `--vy-ease` |
| Panel enter, tab change, message appear | 220 ms | `--vy-ease-out` |
| Confirmation dialog enter | 300 ms | `--vy-ease-out` |
| Orb state cross-fade | 300 ms | linear |

Rules: nothing longer than 300 ms; no bounce; no parallax; no spinner where a progress value exists; respect `prefers-reduced-motion`; every animation must be skippable without losing information.

## Low-power mode

Enabled in Settings or automatically on battery. It disables:

- WebGL and canvas shaders, falling back to the static SVG orb;
- grain, grid glow and backdrop blur;
- waveform animation (3-level indicator instead);
- continuous sampling of system stats beyond one update every 5 seconds.

Tool log, chat and settings stay fully functional.

## Layout

- Minimum window 960×640; default 1280×800; the layout is fluid above 960 px and stacks below 1100 px.
- Left rail 64 px collapsed / 200 px expanded, with icon plus label.
- Content max-width 1080 px, 24 px gutters.
- Status bar 32 px tall at the bottom: connection, active model, RAM, low-power toggle.
- Mini widget (future scope, not in 0.1.0): 180×72 px, always-on-top, orb plus one status line, draggable, no title bar.

## Accessibility checklist

- [ ] All text meets the contrast table above.
- [ ] Focus is visible: 2 px accent ring with 2 px offset; never removed.
- [ ] Full keyboard operation, including the confirmation dialog (Enter confirms only when the primary action is focused).
- [ ] Interactive targets at least 32×32 px.
- [ ] State is conveyed by text or icon as well as colour.
- [ ] `prefers-reduced-motion` and low-power mode both honoured.
- [ ] Screen-reader labels on icon-only buttons; orb state announced via `aria-live`.
- [ ] Window is resizable down to the minimum size without clipping controls.

## Implementation notes (Phase 4)

- Tailwind receives the tokens as named colours (`vy-gunmetal-700`, `vy-silver-100`, `vy-accent-500`, …); arbitrary hex values are rejected in review and by a lint rule.
- `tokens.css` is the only place where literal colours appear.
- One `useOrbState` hook maps backend state messages to the states above; components never inspect raw WebSocket payloads.
- Every animation is disabled by a single `lowPower` flag at the root, not by ad-hoc checks in components.
