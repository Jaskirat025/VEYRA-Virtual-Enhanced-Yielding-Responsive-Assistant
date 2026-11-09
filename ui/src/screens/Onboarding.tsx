import { useState } from "react";
import { apiFetch } from "../lib/api";
import { useVeyra } from "../lib/useVeyra";
import { LANGUAGES, useI18n } from "../i18n";

interface CheckResponse {
  ollama: { ok: boolean; models: string[]; error?: string };
  speech: boolean;
  data_dir: string;
}

const TOTAL_STEPS = 5;

export function Onboarding() {
  const {
    backend,
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
  const [check, setCheck] = useState<CheckResponse | null>(null);
  const [checking, setChecking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runCheck = async () => {
    if (!backend) {
      setError(t("common.offlineHint"));
      return;
    }
    setChecking(true);
    setError(null);
    try {
      const response = await apiFetch<CheckResponse>(backend, "/api/onboarding/check");
      setCheck(response);
      if (!response.ollama.ok) setError(response.ollama.error ?? t("onboarding.missing"));
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setChecking(false);
    }
  };

  const finish = async () => {
    await completeOnboarding(name.trim() || "Veyra", language);
  };

  const next = () => setStep((current) => Math.min(current + 1, TOTAL_STEPS - 1));

  return (
    <div className="mx-auto flex h-full w-full max-w-2xl flex-col justify-center px-8 py-10">
      <div className="mb-6 flex items-center gap-3">
        {Array.from({ length: TOTAL_STEPS }).map((_, index) => (
          <span
            key={index}
            className="h-[2px] flex-1 transition-colors"
            style={{
              backgroundColor:
                index <= step ? "var(--vy-accent-500)" : "var(--vy-line-strong)",
            }}
          />
        ))}
      </div>

      <p className="vy-label mb-3">
        {t("onboarding.step")} {step + 1}/{TOTAL_STEPS}
      </p>

      {step === 0 && (
        <div>
          <h1 className="mb-3 font-display text-3xl tracking-wide text-silver-100">
            {t("onboarding.welcome")}
          </h1>
          <p className="mb-8 max-w-md text-sm leading-relaxed text-silver-400">
            {t("onboarding.intro")}
          </p>

          <label className="mb-4 block">
            <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
              {t("onboarding.name")}
            </span>
            <input
              className="vy-field"
              value={name}
              maxLength={32}
              onChange={(event) => setName(event.target.value)}
            />
          </label>

          <label className="block">
            <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
              {t("onboarding.language")}
            </span>
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
          <h1 className="mb-3 font-display text-2xl tracking-wide text-silver-100">
            {t("onboarding.ollama")}
          </h1>
          <p className="mb-5 text-sm text-silver-400">
            Veyra uses a local model through Ollama. Nothing is uploaded.
          </p>
          <button
            type="button"
            className="vy-btn vy-btn-primary"
            disabled={checking}
            onClick={() => void runCheck()}
          >
            {checking ? "…" : t("onboarding.check")}
          </button>
          {check?.ollama.ok && (
            <p className="mt-4 text-sm" style={{ color: "var(--vy-silver-300)" }}>
              {t("onboarding.ok")}: {check.ollama.models.join(", ") || "—"}
            </p>
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
            Voice input uses the local microphone through the backend. If no device is
            available, keep using the keyboard.
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
            onClick={() => speakTest("Ciao. Sono Veyra. La voce è pronta.")}
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
          <ul className="mb-6 space-y-1 font-mono text-[11px] text-silver-500">
            <li>NAME · {name || "Veyra"}</li>
            <li>LANGUAGE · {language}</li>
            <li>MODEL · {settings?.models.local_model ?? "qwen3:4b"}</li>
            <li>DATA · {check?.data_dir ?? "%APPDATA%\\Veyra"}</li>
          </ul>
          <button type="button" className="vy-btn vy-btn-primary" onClick={() => void finish()}>
            {t("onboarding.finish")}
          </button>
        </div>
      )}

      {error && (
        <p className="mt-5 border-l-2 border-accent px-3 py-1 text-xs text-silver-300">{error}</p>
      )}

      <div className="mt-10 flex items-center justify-between">
        <button type="button" className="vy-btn h-8 px-3 text-xs" onClick={skipOnboarding}>
          {t("onboarding.skip")}
        </button>
        {step < TOTAL_STEPS - 1 && (
          <button type="button" className="vy-btn" onClick={next}>
            {t("onboarding.next")}
          </button>
        )}
      </div>
    </div>
  );
}
