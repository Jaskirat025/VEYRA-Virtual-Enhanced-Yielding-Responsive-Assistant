import { motion } from "framer-motion";
import { useEffect, useRef } from "react";
import { useVeyra } from "../lib/useVeyra";
import { useI18n } from "../i18n";

export function ConfirmDialog() {
  const { confirm, respondConfirm } = useVeyra();
  const { t } = useI18n();
  const cancelRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (confirm) cancelRef.current?.focus();
  }, [confirm]);

  useEffect(() => {
    if (!confirm) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") respondConfirm(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [confirm, respondConfirm]);

  if (!confirm) return null;

  const dangerous = confirm.risk === "dangerous";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
    >
      <motion.div
        initial={{ opacity: 0, y: 10, scale: 0.99 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
        className="vy-panel w-full max-w-lg p-6"
        style={{
          boxShadow:
            "inset 0 0 0 1px var(--vy-accent-500), 0 24px 60px rgba(0, 0, 0, 0.6)",
        }}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 id="confirm-title" className="font-display text-lg tracking-wide text-silver-100">
            {t("confirm.title")}
          </h2>
          <span
            className="px-2 py-1 font-display text-[10px] uppercase tracking-[0.16em]"
            style={{
              color: "var(--vy-accent-ink)",
              backgroundColor: "var(--vy-accent-500)",
            }}
          >
            {dangerous ? t("risk.dangerous") : t("risk.confirm")}
          </span>
        </div>

        <p className="mb-1 font-mono text-xs text-silver-400">
          {confirm.tool} · {confirm.category}
        </p>
        <p className="mb-4 text-sm text-silver-100">{confirm.summary}</p>

        {confirm.external_content_read && (
          <p
            className="mb-4 border-l-2 px-3 py-2 text-xs text-silver-300"
            style={{ borderColor: "var(--vy-accent-500)" }}
          >
            {t("confirm.external")}
          </p>
        )}

        <p className="vy-label mb-1">{t("confirm.arguments")}</p>
        <pre className="mb-6 max-h-40 overflow-auto rounded-md bg-gunmetal-900 p-3 font-mono text-[11px] leading-relaxed text-silver-400">
          {JSON.stringify(confirm.arguments, null, 2)}
        </pre>

        <div className="flex justify-end gap-3">
          <button ref={cancelRef} type="button" className="vy-btn" onClick={() => respondConfirm(false)}>
            {t("confirm.cancel")}
          </button>
          <button
            type="button"
            className="vy-btn vy-btn-primary"
            onClick={() => respondConfirm(true)}
          >
            {t("confirm.approve")}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
