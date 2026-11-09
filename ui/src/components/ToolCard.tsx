import type { Risk, ToolEvent } from "../lib/types";
import { useI18n } from "../i18n";

const riskKey: Record<Risk, string> = {
  safe: "risk.safe",
  confirm: "risk.confirm",
  dangerous: "risk.dangerous",
};

export function ToolCard({ event }: { event: ToolEvent }) {
  const { t } = useI18n();
  const accent = event.risk === "safe" ? "var(--vy-silver-400)" : "var(--vy-accent-500)";

  return (
    <details className="vy-panel-flat group px-3 py-2 text-xs">
      <summary className="flex cursor-pointer list-none items-center gap-3">
        <span className="font-mono text-silver-100">{event.tool}</span>
        <span
          className="font-display text-[10px] uppercase tracking-[0.14em]"
          style={{ color: accent }}
        >
          {t(riskKey[event.risk])}
        </span>
        <span className="ml-auto font-mono text-[10px] text-silver-500">
          {event.status}
          {typeof event.duration_ms === "number" ? ` · ${event.duration_ms} ms` : ""}
        </span>
      </summary>
      <pre className="mt-2 overflow-auto rounded bg-gunmetal-900 p-2 font-mono text-[11px] text-silver-400">
        {JSON.stringify(event.args, null, 2)}
      </pre>
      {event.output && (
        <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-gunmetal-900 p-2 font-mono text-[11px] text-silver-300">
          {event.output}
        </pre>
      )}
    </details>
  );
}
