import { useState } from "react";
import { Orb } from "../components/Orb";
import { useVeyra } from "../lib/useVeyra";
import { useI18n } from "../i18n";

async function hideMini() {
  try {
    const { getCurrentWindow } = await import("@tauri-apps/api/window");
    await getCurrentWindow().hide();
  } catch {
    // Browser preview: there is no desktop window to hide.
  }
}

export function MiniWidget() {
  const {
    orbState,
    messages,
    settings,
    connected,
    send,
    listen,
    cancel,
  } = useVeyra();
  const { t } = useI18n();
  const [text, setText] = useState("");
  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");
  const busy = orbState === "thinking" || orbState === "listening" || orbState === "speaking";

  const submit = () => {
    if (!text.trim() || !connected) return;
    send(text);
    setText("");
  };

  return (
    <div className="vy-app-bg vy-grain flex h-screen flex-col overflow-hidden border border-white/10">
      <header
        data-tauri-drag-region
        className="flex h-9 shrink-0 items-center justify-between border-b border-white/10 px-3"
      >
        <span className="vy-label" data-tauri-drag-region>
          {settings?.assistant_name ?? t("app.name")}
        </span>
        <div className="flex items-center gap-1">
          <span
            aria-hidden="true"
            className="h-1.5 w-1.5 rounded-full"
            style={{
              backgroundColor: connected ? "var(--vy-accent-500)" : "var(--vy-silver-500)",
            }}
          />
          <button
            type="button"
            className="flex h-7 w-7 items-center justify-center text-silver-500 hover:text-silver-100"
            aria-label={t("mini.close")}
            onClick={() => void hideMini()}
          >
            ×
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-2 px-4 py-3">
        <Orb
          state={orbState}
          level={0}
          lowPower={settings?.interface.low_power ?? false}
          size={76}
        />
        <p className="vy-label" aria-live="polite">
          {t(`state.${orbState}`)}
        </p>
        <p className="line-clamp-3 min-h-[42px] text-center text-xs leading-relaxed text-silver-300">
          {lastAssistant?.text ?? t("mini.hint")}
        </p>
      </div>

      <form
        className="flex shrink-0 items-center gap-1 border-t border-white/10 p-2"
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        <button
          type="button"
          className="flex h-8 w-8 shrink-0 items-center justify-center text-silver-400 hover:text-silver-100 disabled:opacity-40"
          aria-label={busy ? t("home.stop") : t("mini.listen")}
          disabled={!connected}
          onClick={() => (busy ? cancel() : listen())}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <rect x="9" y="3" width="6" height="11" rx="3" stroke="currentColor" strokeWidth="1.5" />
            <path d="M5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
        </button>
        <input
          className="min-w-0 flex-1 bg-transparent px-1 text-xs text-silver-100 outline-none placeholder:text-silver-500"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={connected ? t("mini.placeholder") : t("common.offlineTitle")}
          aria-label={t("mini.placeholder")}
          disabled={!connected}
        />
        <button
          type="submit"
          className="vy-btn vy-btn-primary h-8 px-3 text-xs"
          disabled={!text.trim() || !connected}
        >
          {t("home.send")}
        </button>
      </form>
    </div>
  );
}
