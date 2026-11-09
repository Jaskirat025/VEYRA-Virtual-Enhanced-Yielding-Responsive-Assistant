import { useState } from "react";
import { Orb } from "../components/Orb";
import { Waveform } from "../components/Waveform";
import { useVeyra } from "../lib/useVeyra";
import { useI18n } from "../i18n";

function Readout({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
}) {
  return (
    <div className="min-w-0 border-l border-white/10 px-4 py-2.5 first:border-l-0">
      <p className="vy-label text-[9px]">{label}</p>
      <p className="mt-1 flex min-w-0 items-center gap-2 font-display text-[13px] tracking-wide text-silver-100">
        {accent && (
          <span
            aria-hidden="true"
            className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
            style={{ backgroundColor: "var(--vy-accent-500)" }}
          />
        )}
        <span className="truncate">{value}</span>
      </p>
    </div>
  );
}

export function HomeScreen() {
  const {
    orbState,
    level,
    settings,
    messages,
    send,
    listen,
    cancel,
    connected,
    error,
    health,
  } = useVeyra();
  const { t } = useI18n();
  const [text, setText] = useState("");

  const busy = orbState === "thinking" || orbState === "listening" || orbState === "speaking";
  const active = orbState === "listening" || orbState === "speaking";
  const lastUser = [...messages].reverse().find((message) => message.role === "user");
  const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");

  const submit = () => {
    if (!text.trim() || !connected) return;
    send(text);
    setText("");
  };

  return (
    <div className="flex h-full flex-col items-center justify-between gap-6 px-6 py-6">
      <div className="flex w-full max-w-content flex-1 flex-col items-center justify-center gap-4">
        <div className="grid w-full max-w-2xl grid-cols-3 border-y border-white/10 bg-black/10">
          <Readout
            label={t("status.link")}
            value={connected ? t("status.online") : t("status.offline")}
            accent={connected}
          />
          <Readout
            label={t("status.model")}
            value={health?.model ?? settings?.models.local_model ?? "qwen3:4b"}
          />
          <Readout
            label={t("status.mode")}
            value={health?.online_enabled ? "LOCAL + ONLINE" : t("status.local")}
          />
        </div>

        <span className="vy-label" role="status" aria-live="polite">
          {t(`state.${orbState}`)}
        </span>

        <div className="relative flex items-center justify-center">
          <Orb
            state={orbState}
            level={level}
            lowPower={settings?.interface.low_power ?? false}
            size={264}
          />
        </div>

        <Waveform level={level} active={active} />

        <div className="mt-1 min-h-[92px] w-full max-w-xl text-center">
          {lastUser && (
            <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.14em] text-silver-500">
              {t("chat.you")}
            </p>
          )}
          {lastUser && (
            <p className="mb-3 line-clamp-2 text-sm text-silver-400">{lastUser.text}</p>
          )}
          {lastAssistant ? (
            <p className="text-base leading-relaxed text-silver-100">{lastAssistant.text}</p>
          ) : (
            !lastUser && (
              <p className="mx-auto max-w-md text-sm leading-relaxed text-silver-400">
                {t("home.hint")}
              </p>
            )
          )}
        </div>

        {error && (
          <p
            className="max-w-lg border-l-2 px-3 py-1 text-center text-xs text-silver-300"
            style={{ borderColor: "var(--vy-accent-500)" }}
          >
            {error}
          </p>
        )}
      </div>

      <div className="w-full max-w-2xl">
        <div className="mb-3 flex flex-wrap justify-center gap-2">
          {["home.chip.calc", "home.chip.open", "home.chip.note"].map((key) => (
            <button
              key={key}
              type="button"
              className="vy-chip"
              onClick={() => setText(t(key))}
            >
              {t(key)}
            </button>
          ))}
        </div>

        <form
          className="vy-panel flex items-end gap-2 p-2"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <button
            type="button"
            aria-label={t("home.listen")}
            title={t("home.listen")}
            disabled={!connected || busy}
            onClick={() => (busy ? cancel() : listen())}
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md transition-colors disabled:opacity-40"
            style={{
              color: busy ? "var(--vy-accent-500)" : "var(--vy-silver-300)",
              boxShadow: busy ? "inset 0 0 0 1px var(--vy-accent-500)" : "none",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <rect x="9" y="3" width="6" height="11" rx="3" stroke="currentColor" strokeWidth="1.4" />
              <path d="M5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
          </button>

          <input
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder={connected ? t("home.placeholder") : t("common.offlineHint")}
            aria-label={t("home.placeholder")}
            disabled={!connected}
            className="min-h-10 flex-1 bg-transparent px-2 text-sm text-silver-100 outline-none placeholder:text-silver-500 disabled:opacity-60"
          />

          <button
            type="submit"
            disabled={!text.trim() || !connected}
            className="vy-btn vy-btn-primary h-10 shrink-0 px-5"
          >
            {t("home.send")}
          </button>
        </form>
      </div>
    </div>
  );
}
