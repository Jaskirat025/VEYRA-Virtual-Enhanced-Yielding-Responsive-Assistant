import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "../lib/api";
import type { BootstrapJob, BootstrapStatus } from "../lib/types";
import { useVeyra } from "../lib/useVeyra";
import { LANGUAGES, useI18n } from "../i18n";

const TOTAL_STEPS = 5;

const JOB_LABEL_KEYS: Record<string, string> = {
  local_model: "onboarding.job.localModel",
  speech_model: "onboarding.job.speechModel",
  voice_model: "onboarding.job.voiceModel",
};

const STATUS_KEYS: Record<BootstrapJob["status"], string> = {
  pending: "downloads.pending",
  running: "downloads.running",
  done: "downloads.done",
  skipped: "downloads.skipped",
  error: "downloads.error",
};

function formatBytes(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return "0 MB";
  const units = ["B", "KB", "MB", "GB"];
  let size = value;
  let unit = 0;
  while (size >= 1024 && unit < units.length - 1) {
    size /= 1024;
    unit += 1;
  }
  return `${size.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}

function DownloadRow({ job }: { job: BootstrapJob }) {
  const { t } = useI18n();
  const labelKey = JOB_LABEL_KEYS[job.id];
  const label = labelKey ? t(labelKey) : job.label;
  const percent = job.progress === null ? null : Math.round(job.progress * 100);
  const complete = job.status === "done" || job.status === "skipped";
  const failed = job.status === "error";
  const indeterminate = percent === null && job.status === "running";
  const width =
    percent !== null
      ? `${Math.max(complete ? 100 : 3, percent)}%`
      : failed
        ? "100%"
        : job.status === "pending"
          ? "4%"
          : undefined;
  const fill = complete
    ? "var(--vy-silver-400)"
    : "linear-gradient(90deg, var(--vy-accent-600), var(--vy-accent-500))";

  return (
    <div className="vy-panel-flat p-3.5">
      <div className="flex items-baseline justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm text-silver-100">{label}</p>
          <p
            className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.12em]"
            style={{ color: failed ? "var(--vy-accent-500)" : "var(--vy-silver-500)" }}
          >
            {t(STATUS_KEYS[job.status])}
          </p>
        </div>
        <div className="shrink-0 text-right font-mono text-[10px] text-silver-500">
          {job.total > 0 ? (
            <span>
              {formatBytes(job.downloaded)} / {formatBytes(job.total)}
            </span>
          ) : percent !== null ? (
            <span>{percent}%</span>
          ) : null}
        </div>
      </div>

      <div
        className="vy-progress mt-2.5"
        data-indeterminate={indeterminate ? "true" : "false"}
        role="progressbar"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={percent ?? undefined}
      >
        <span style={{ width, background: fill }} />
      </div>

      {job.detail && (
        <p
          className={`mt-2 text-[11px] leading-relaxed ${
            failed ? "text-silver-300" : "text-silver-500"
          }`}
        >
          {failed ? job.error || job.detail : job.detail}
        </p>
      )}
    </div>
  );
}

export function Onboarding() {
  const {
    backend,
    health,
    settings,
    completeOnboarding,
    skipOnboarding,
    speakTest,
    setLanguage,
  } = useVeyra();
  const { t } = useI18n();
  const [step, setStep] = useState(0);
  const [name, setName] = useState(settings?.assistant_name ?? "Veyra");
  const [language, setLanguageLocal] = useState(settings?.interface.language ?? "en");
  const [downloads, setDownloads] = useState<BootstrapStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const startedRef = useRef(false);

  const refreshDownloads = useCallback(async () => {
    if (!backend) return;
    try {
      const status = await apiFetch<BootstrapStatus>(backend, "/api/bootstrap/status");
      setDownloads(status);
      setDownloadError(null);
    } catch (cause) {
      setDownloadError((cause as Error).message);
    }
  }, [backend]);

  const startDownloads = useCallback(async () => {
    if (!backend) {
      setDownloadError(t("common.offlineHint"));
      return;
    }
    setStarting(true);
    setDownloadError(null);
    try {
      const status = await apiFetch<BootstrapStatus>(backend, "/api/bootstrap/start", {
        method: "POST",
      });
      setDownloads(status);
    } catch (cause) {
      setDownloadError((cause as Error).message);
    } finally {
      setStarting(false);
    }
  }, [backend, t]);

  useEffect(() => {
    if (!backend || startedRef.current) return;
    startedRef.current = true;
    void startDownloads();
  }, [backend, startDownloads]);

  useEffect(() => {
    if (!downloads?.running) return;
    const timer = window.setInterval(() => {
      void refreshDownloads();
    }, 1000);
    return () => window.clearInterval(timer);
  }, [downloads?.running, refreshDownloads]);

  const finish = async () => {
    await completeOnboarding(name.trim() || "Veyra", language);
  };

  const next = () => setStep((current) => Math.min(current + 1, TOTAL_STEPS - 1));

  return (
    <div className="vy-grain relative mx-auto flex min-h-full w-full max-w-2xl flex-col justify-center px-8 py-8">
      <div className="mb-7">
        <div className="flex items-center justify-between">
          <span className="vy-label">
            {t("onboarding.step")} {String(step + 1).padStart(2, "0")}
          </span>
          <span className="font-mono text-[10px] tracking-[0.14em] text-silver-500">
            {String(step + 1).padStart(2, "0")} / {String(TOTAL_STEPS).padStart(2, "0")}
          </span>
        </div>
        <div className="mt-3 flex gap-1.5" aria-hidden="true">
          {Array.from({ length: TOTAL_STEPS }).map((_, index) => (
            <span
              key={index}
              className="h-[2px] flex-1 transition-colors"
              style={{
                backgroundColor:
                  index === step
                    ? "var(--vy-accent-500)"
                    : index < step
                      ? "var(--vy-silver-400)"
                      : "var(--vy-line-strong)",
              }}
            />
          ))}
        </div>
      </div>

      {step === 0 && (
        <div>
          <h1 className="mb-3 font-display text-3xl tracking-wide text-silver-100">
            {t("onboarding.welcome")}
          </h1>
          <p className="mb-8 max-w-md text-sm leading-relaxed text-silver-400">
            {t("onboarding.intro")}
          </p>

          <label className="mb-4 block">
            <span className="vy-label mb-1 block">{t("onboarding.name")}</span>
            <input
              className="vy-field"
              value={name}
              maxLength={32}
              onChange={(event) => setName(event.target.value)}
            />
          </label>

          <label className="block">
            <span className="vy-label mb-1 block">{t("onboarding.language")}</span>
            <select
              className="vy-field"
              value={language}
              onChange={(event) => {
                setLanguageLocal(event.target.value);
                void setLanguage(event.target.value);
              }}
            >
              {LANGUAGES.map((item) => (
                <option key={item.code} value={item.code}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {step === 1 && (
        <div>
          <h1 className="mb-2 font-display text-2xl tracking-wide text-silver-100">
            {t("onboarding.downloads")}
          </h1>
          <p className="mb-5 max-w-lg text-sm leading-relaxed text-silver-400">
            {t("onboarding.downloadsHint")}
          </p>

          <div className="space-y-3" aria-live="polite">
            {downloads?.jobs.map((job) => <DownloadRow key={job.id} job={job} />)}
            {!downloads && !downloadError && (
              <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-silver-500">
                {t("onboarding.downloadsStarting")}
              </p>
            )}
          </div>

          {downloads?.complete && (
            <p className="mt-4 text-sm" style={{ color: "var(--vy-silver-300)" }}>
              {t("onboarding.downloadsDone")}
            </p>
          )}
          {downloads?.running && (
            <p className="mt-4 text-xs text-silver-500">{t("onboarding.downloadsBackground")}</p>
          )}

          {downloadError && (
            <div className="mt-4 border-l-2 border-accent px-3 py-2 text-xs text-silver-300">
              <p>{downloadError}</p>
              <button
                type="button"
                className="vy-btn mt-2 h-8 px-3 text-xs"
                disabled={starting}
                onClick={() => void startDownloads()}
              >
                {t("common.retry")}
              </button>
            </div>
          )}

          {downloads?.failed && !downloadError && (
            <button
              type="button"
              className="vy-btn mt-4"
              disabled={starting}
              onClick={() => void startDownloads()}
            >
              {t("onboarding.downloadsRetry")}
            </button>
          )}
        </div>
      )}

      {step === 2 && (
        <div>
          <h1 className="mb-3 font-display text-2xl tracking-wide text-silver-100">
            {t("onboarding.mic")}
          </h1>
          <p className="mb-5 text-sm leading-relaxed text-silver-400">{t("onboarding.micHint")}</p>
          <p className="border-l-2 border-accent px-3 py-2 text-xs text-silver-400">
            {t("onboarding.micNote")}
          </p>
        </div>
      )}

      {step === 3 && (
        <div>
          <h1 className="mb-3 font-display text-2xl tracking-wide text-silver-100">
            {t("onboarding.voice")}
          </h1>
          <p className="mb-5 text-sm leading-relaxed text-silver-400">
            {t("onboarding.voiceHint")}
          </p>
          <button
            type="button"
            className="vy-btn"
            onClick={() => speakTest(t("onboarding.voiceTest"))}
          >
            {t("onboarding.testVoice")}
          </button>
        </div>
      )}

      {step === 4 && (
        <div>
          <h1 className="mb-3 font-display text-2xl tracking-wide text-silver-100">
            {t("onboarding.finish")}
          </h1>
          <p className="mb-5 text-sm leading-relaxed text-silver-400">
            {t("onboarding.intro")}
          </p>
          <div className="vy-panel-flat mb-6 space-y-1 p-4 font-mono text-[11px] text-silver-500">
            <p>NAME · {name || "Veyra"}</p>
            <p>LANGUAGE · {language}</p>
            <p>MODEL · {settings?.models.local_model ?? "qwen3:4b"}</p>
            <p>DATA · {health?.data_dir ?? "%APPDATA%\\Veyra"}</p>
          </div>
          <button type="button" className="vy-btn vy-btn-primary" onClick={() => void finish()}>
            {t("onboarding.finish")}
          </button>
        </div>
      )}

      <div className="mt-10 flex items-center justify-between border-t border-white/10 pt-4">
        <button
          type="button"
          className="vy-btn h-8 px-3 text-xs"
          disabled={!backend}
          onClick={() => void skipOnboarding()}
        >
          {t("onboarding.skip")}
        </button>
        {step < TOTAL_STEPS - 1 && (
          <button type="button" className="vy-btn vy-btn-primary" onClick={next}>
            {t("onboarding.next")}
          </button>
        )}
      </div>
    </div>
  );
}
