import { useVeyra } from "../lib/useVeyra";
import { useI18n } from "../i18n";

export function StatusBar() {
  const { connected, health, settings, orbState } = useVeyra();
  const { t } = useI18n();
  const ram = health?.ram_mb ? (health.ram_mb / 1024).toFixed(1) : "—";

  return (
    <footer className="flex h-8 shrink-0 items-center gap-4 border-t border-white/10 bg-gunmetal-900/85 px-4 font-mono text-[10px] uppercase tracking-[0.12em] text-silver-500">
      <span className="flex items-center gap-2">
        <span
          className="inline-block h-1.5 w-1.5 rounded-full"
          style={{
            backgroundColor: connected ? "var(--vy-accent-500)" : "var(--vy-silver-500)",
          }}
        />
        {connected ? t("status.connected") : t("status.offline")}
      </span>
      <span aria-hidden="true" className="h-3 w-px bg-white/10" />
      <span className="truncate">
        {t("status.model")}: {health?.model?.toUpperCase() ?? "—"}
      </span>
      <span aria-hidden="true" className="hidden h-3 w-px bg-white/10 sm:inline-block" />
      <span className="hidden sm:inline">
        {t("status.ram")}: {ram} GB
      </span>
      <span aria-hidden="true" className="hidden h-3 w-px bg-white/10 md:inline-block" />
      <span className="hidden md:inline">
        {health?.online_enabled ? "LOCAL + ONLINE" : t("status.local")}
      </span>
      <span className="ml-auto flex items-center gap-3">
        {settings?.interface.low_power && (
          <span style={{ color: "var(--vy-accent-500)" }}>{t("status.lowPower")}</span>
        )}
        <span aria-live="polite" className="text-silver-400">
          {orbState.toUpperCase()}
        </span>
      </span>
    </footer>
  );
}
