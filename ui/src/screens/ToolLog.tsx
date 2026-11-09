import { useEffect } from "react";
import { useVeyra } from "../lib/useVeyra";
import { useI18n } from "../i18n";
import type { Risk } from "../lib/types";

const riskKey: Record<Risk, string> = {
  safe: "risk.safe",
  confirm: "risk.confirm",
  dangerous: "risk.dangerous",
};

function riskOf(value: string): Risk {
  return value === "confirm" || value === "dangerous" ? value : "safe";
}

export function ToolLogScreen() {
  const { toolLog, loadToolLog } = useVeyra();
  const { t } = useI18n();

  useEffect(() => {
    void loadToolLog();
  }, [loadToolLog]);

  return (
    <div className="mx-auto flex h-full w-full max-w-content flex-col px-6 py-6">
      <div className="mb-4 flex items-center justify-between">
        <h1 className="font-display text-2xl tracking-wide text-silver-100">{t("tools.title")}</h1>
        <button type="button" className="vy-btn h-8 px-3 text-xs" onClick={() => void loadToolLog()}>
          {t("tools.refresh")}
        </button>
      </div>

      {toolLog.length === 0 ? (
        <p className="mt-16 text-center text-sm text-silver-500">{t("tools.empty")}</p>
      ) : (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <table className="w-full border-collapse text-left text-xs">
            <thead className="sticky top-0 bg-gunmetal-700">
              <tr className="vy-label">
                <th className="border-b border-white/10 py-2 pr-3">{t("tools.tool")}</th>
                <th className="border-b border-white/10 py-2 pr-3">{t("tools.risk")}</th>
                <th className="border-b border-white/10 py-2 pr-3">{t("tools.status")}</th>
                <th className="border-b border-white/10 py-2 pr-3">{t("tools.duration")}</th>
                <th className="border-b border-white/10 py-2">{t("tools.args")}</th>
              </tr>
            </thead>
            <tbody>
              {toolLog.map((entry) => (
                <tr key={entry.id} className="align-top">
                  <td className="border-b border-white/5 py-3 pr-3 font-mono text-silver-100">
                    {entry.tool}
                    <div className="text-[10px] text-silver-500">{entry.category}</div>
                  </td>
                  <td
                    className="border-b border-white/5 py-3 pr-3 font-display text-[10px] uppercase tracking-[0.12em]"
                    style={{
                      color:
                        entry.risk === "safe" ? "var(--vy-silver-400)" : "var(--vy-accent-500)",
                    }}
                  >
                    {t(riskKey[riskOf(entry.risk)])}
                  </td>
                  <td className="border-b border-white/5 py-3 pr-3 font-mono">
                    <span
                      className="px-1.5 py-0.5"
                      style={{
                        color:
                          entry.status === "ok"
                            ? "var(--vy-silver-100)"
                            : "var(--vy-accent-500)",
                        backgroundColor: "rgba(22, 28, 31, 0.6)",
                      }}
                    >
                      {entry.status}
                    </span>
                    {entry.error && (
                      <div className="mt-1 max-w-[220px] text-[10px] text-silver-500">
                        {entry.error}
                      </div>
                    )}
                  </td>
                  <td className="border-b border-white/5 py-3 pr-3 font-mono text-silver-400">
                    {entry.duration_ms} ms
                  </td>
                  <td className="max-w-[280px] border-b border-white/5 py-3 font-mono text-[11px] text-silver-400">
                    <details>
                      <summary className="cursor-pointer text-silver-500">
                        {Object.keys(entry.args_redacted).length} keys
                      </summary>
                      <pre className="mt-1 overflow-x-auto whitespace-pre-wrap">
                        {JSON.stringify(entry.args_redacted, null, 2)}
                      </pre>
                    </details>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
