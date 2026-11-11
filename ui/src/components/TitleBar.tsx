import { useVeyra } from "../lib/useVeyra";
import { useI18n } from "../i18n";

async function windowAction(action: "minimize" | "maximize" | "close") {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    const window = getCurrentWindow();
    if (action === "minimize") await window.minimize();
    if (action === "maximize") await window.toggleMaximize();
    if (action === "close") await window.close();
  } catch {
    // Browser preview: window controls are decorative.
  }
}

export function TitleBar() {
  const { connected, settings } = useVeyra();
  const { t } = useI18n();

  return (
    <header
      data-tauri-drag-region
      className="flex h-11 shrink-0 items-center justify-between border-b border-white/5 bg-gunmetal-900/80 px-4 backdrop-blur"
    >
      <div className="flex items-center gap-3" data-tauri-drag-region>
        <span
          className="inline-block h-2 w-2 rounded-full"
          style={{
            backgroundColor: connected ? "var(--vy-accent-500)" : "var(--vy-silver-500)",
            boxShadow: connected ? "0 0 10px var(--vy-accent-500)" : "none",
          }}
        />
        <div className="flex items-baseline gap-3" data-tauri-drag-region>
          <span className="font-display text-[15px] font-semibold uppercase tracking-[0.22em] text-silver-100">
            {t("app.name")}
          </span>
          <span className="hidden text-[10px] uppercase tracking-[0.2em] text-silver-500 sm:inline">
            {settings?.assistant_name ?? t("app.tagline")}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          aria-label={t("app.minimise")}
          className="flex h-8 w-9 items-center justify-center text-silver-400 transition-colors hover:bg-white/5 hover:text-silver-100"
          onClick={() => void windowAction("minimize")}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M2 6h8" stroke="currentColor" strokeWidth="1.4" />
          </svg>
        </button>
        <button
          type="button"
          aria-label={t("app.maximise")}
          className="flex h-8 w-9 items-center justify-center text-silver-400 transition-colors hover:bg-white/5 hover:text-silver-100"
          onClick={() => void windowAction("maximize")}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <rect x="2.5" y="2.5" width="7" height="7" stroke="currentColor" strokeWidth="1.2" />
          </svg>
        </button>
        <button
          type="button"
          aria-label={t("app.close")}
          className="flex h-8 w-9 items-center justify-center text-silver-400 transition-colors hover:bg-accent/90 hover:text-accent-ink"
          onClick={() => void windowAction("close")}
        >
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
            <path d="M2.5 2.5l7 7M9.5 2.5l-7 7" stroke="currentColor" strokeWidth="1.4" />
          </svg>
        </button>
      </div>
    </header>
  );
}
