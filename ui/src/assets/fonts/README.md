# Fonts

The design system uses Rajdhani (HUD), Inter (body) and JetBrains Mono (logs). All three are licensed under the SIL Open Font License 1.1 and can be bundled with the application.

The interface currently falls back to the Windows system stack:

- display: `Rajdhani`, `Segoe UI`
- body: `Inter`, `Segoe UI`, `Microsoft YaHei UI`
- mono: `JetBrains Mono`, `Cascadia Mono`

To self-host the fonts, place the WOFF2 files here as:

```
Rajdhani-600.woff2
Rajdhani-700.woff2
Inter-400.woff2
Inter-500.woff2
Inter-600.woff2
JetBrainsMono-400.woff2
OFL.txt
```

and add the matching `@font-face` blocks to `src/index.css`. Keep `OFL.txt` next to the files and listed in `THIRD_PARTY_LICENSES.md`. The file weight stays small because only the used weights and Latin subsets are needed; CJK text uses the Windows system font to avoid a multi-megabyte download.
