import { useEffect, useState, type ReactNode } from "react";
import { apiFetch } from "../lib/api";
import type { Settings } from "../lib/types";
import { useVeyra } from "../lib/useVeyra";
import { LANGUAGES, useI18n } from "../i18n";

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="vy-panel p-5">
      <h2 className="vy-label mb-4" style={{ color: "var(--vy-silver-300)" }}>
        {title}
      </h2>
      <div className="space-y-4">{children}</div>
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-[11px] uppercase tracking-[0.12em] text-silver-500">
        {label}
      </span>
      {children}
    </label>
  );
}

export function SettingsScreen() {
  const { settings, tools, saveSettings, refreshTools, backend, setLanguage } = useVeyra();
  const { t } = useI18n();
  const [draft, setDraft] = useState<Settings | null>(settings);
  const [saved, setSaved] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [secret, setSecret] = useState("");
  const [secretKind, setSecretKind] = useState<"online_api_key" | "github_token">(
    "online_api_key",
  );
  const [googleClient, setGoogleClient] = useState("");
  const [googleWrite, setGoogleWrite] = useState(false);
  const [gmailPassword, setGmailPassword] = useState("");

  useEffect(() => setDraft(settings), [settings]);

  if (!draft) {
    return <p className="p-8 text-sm text-silver-500">{t("settings.loading")}</p>;
  }

  const patchGroup = (
    group: "models" | "voice" | "audio" | "integrations" | "interface",
    key: string,
    value: unknown,
  ) => {
    setDraft((current) => {
      if (!current) return current;
      return {
        ...current,
        [group]: { ...(current[group] as unknown as Record<string, unknown>), [key]: value },
      } as Settings;
    });
  };

  const save = async () => {
    setMessage(null);
    try {
      await saveSettings({
        assistant_name: draft.assistant_name,
        wake_word: draft.wake_word,
        system_prompt: draft.system_prompt,
        models: draft.models,
        voice: draft.voice,
        audio: draft.audio,
        integrations: draft.integrations,
        interface: draft.interface,
        ram_floor_mb: draft.ram_floor_mb,
      });
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2000);
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const saveSecret = async () => {
    if (!backend || !secret.trim()) return;
    try {
      await apiFetch(backend, "/api/secrets", {
        method: "POST",
        body: JSON.stringify({ name: secretKind, value: secret.trim() }),
      });
      setSecret("");
      setMessage(t("settings.saved"));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const saveGmail = async () => {
    if (!backend) return;
    setMessage(null);
    try {
      await saveSettings({
        integrations: {
          ...draft.integrations,
          gmail_address: draft.integrations.gmail_address.trim(),
        },
      });
      if (gmailPassword.trim()) {
        await apiFetch(backend, "/api/secrets", {
          method: "POST",
          body: JSON.stringify({ name: "gmail_app_password", value: gmailPassword.trim() }),
        });
        setGmailPassword("");
      }
      setMessage(t("settings.gmailSaved"));
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const toggleTool = async (name: string, enabled: boolean) => {
    try {
      await saveSettings({
        tool_permissions: { ...(settings?.tool_permissions ?? {}), [name]: enabled },
      });
      await refreshTools();
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  const connectGoogle = async () => {
    if (!backend) return;
    try {
      if (googleClient.trim()) {
        const parsed = JSON.parse(googleClient) as Record<string, unknown>;
        await apiFetch(backend, "/api/google/client", {
          method: "POST",
          body: JSON.stringify(parsed),
        });
      }
      await apiFetch(backend, `/api/google/connect?allow_write=${googleWrite}`, {
        method: "POST",
      });
      setMessage("Google account connected.");
    } catch (error) {
      setMessage((error as Error).message);
    }
  };

  return (
    <div className="mx-auto w-full max-w-content px-6 py-6">
      <div className="mb-5 flex items-end justify-between">
        <h1 className="font-display text-2xl tracking-wide text-silver-100">
          {t("settings.title")}
        </h1>
        <div className="flex items-center gap-3">
          {saved && <span className="text-xs text-accent">{t("settings.saved")}</span>}
          <button type="button" className="vy-btn vy-btn-primary" onClick={() => void save()}>
            {t("settings.save")}
          </button>
        </div>
      </div>

      {message && (
        <p className="mb-4 border-l-2 border-accent px-3 py-1 text-xs text-silver-300">
          {message}
        </p>
      )}

      <div className="grid grid-cols-1 gap-5 pb-10 lg:grid-cols-2">
        <Section title={t("settings.identity")}>
          <Field label={t("settings.name")}>
            <input
              className="vy-field"
              value={draft.assistant_name}
              maxLength={32}
              onChange={(event) =>
                setDraft({ ...draft, assistant_name: event.target.value })
              }
            />
          </Field>
          <Field label={t("settings.wakeWord")}>
            <input
              className="vy-field"
              value={draft.wake_word}
              onChange={(event) => setDraft({ ...draft, wake_word: event.target.value })}
            />
          </Field>
          <Field label={t("settings.systemPrompt")}>
            <textarea
              className="vy-field min-h-[110px] resize-y"
              value={draft.system_prompt}
              placeholder="Sei Veyra…"
              onChange={(event) => setDraft({ ...draft, system_prompt: event.target.value })}
            />
          </Field>
        </Section>

        <Section title={t("settings.models")}>
          <Field label={t("settings.localModel")}>
            <input
              className="vy-field"
              value={draft.models.local_model}
              onChange={(event) => patchGroup("models", "local_model", event.target.value)}
            />
          </Field>
          <label className="flex items-center gap-3 text-sm text-silver-300">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--vy-accent-500)]"
              checked={draft.models.online_enabled}
              onChange={(event) =>
                patchGroup("models", "online_enabled", event.target.checked)
              }
            />
            {t("settings.onlineEnabled")}
          </label>
          <Field label={t("settings.baseUrl")}>
            <input
              className="vy-field"
              value={draft.models.online_base_url}
              placeholder="https://api.example.invalid/v1"
              onChange={(event) => patchGroup("models", "online_base_url", event.target.value)}
            />
          </Field>
          <Field label={t("settings.onlineModel")}>
            <input
              className="vy-field"
              value={draft.models.online_model}
              onChange={(event) => patchGroup("models", "online_model", event.target.value)}
            />
          </Field>
          <Field label={t("settings.apiKey")}>
            <div className="flex gap-2">
              <select
                className="vy-field w-36"
                value={secretKind}
                onChange={(event) =>
                  setSecretKind(event.target.value as "online_api_key" | "github_token")
                }
              >
                <option value="online_api_key">Online model</option>
                <option value="github_token">GitHub</option>
              </select>
              <input
                type="password"
                autoComplete="off"
                className="vy-field flex-1"
                value={secret}
                onChange={(event) => setSecret(event.target.value)}
                placeholder="••••••••"
              />
              <button type="button" className="vy-btn px-3" onClick={() => void saveSecret()}>
                {t("settings.saveKey")}
              </button>
            </div>
          </Field>
        </Section>

        <Section title={t("settings.voice")}>
          <Field label={t("settings.engine")}>
            <select
              className="vy-field"
              value={draft.voice.engine}
              onChange={(event) => patchGroup("voice", "engine", event.target.value)}
            >
              <option value="piper">Piper</option>
              <option value="pyttsx3">System voice</option>
            </select>
          </Field>
          <Field label={t("settings.voiceModel")}>
            <input
              className="vy-field"
              value={draft.voice.piper_voice}
              onChange={(event) => patchGroup("voice", "piper_voice", event.target.value)}
            />
          </Field>
          <label className="flex items-center gap-3 text-sm text-silver-300">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--vy-accent-500)]"
              checked={draft.voice.speak_replies}
              onChange={(event) =>
                patchGroup("voice", "speak_replies", event.target.checked)
              }
            />
            {t("settings.speakReplies")}
          </label>
        </Section>

        <Section title={t("settings.audio")}>
          <Field label={t("settings.sttModel")}>
            <select
              className="vy-field"
              value={draft.audio.stt_model}
              onChange={(event) => patchGroup("audio", "stt_model", event.target.value)}
            >
              <option value="base">base</option>
              <option value="small">small</option>
            </select>
          </Field>
          <Field label={t("settings.inputDevice")}>
            <input
              className="vy-field"
              type="number"
              value={draft.audio.input_device ?? ""}
              placeholder="auto"
              onChange={(event) =>
                patchGroup(
                  "audio",
                  "input_device",
                  event.target.value === "" ? null : Number(event.target.value),
                )
              }
            />
          </Field>
        </Section>

        <Section title={t("settings.accounts")}>
          <Field label={t("settings.githubToken")}>
            <input
              type="password"
              autoComplete="off"
              className="vy-field"
              value={secretKind === "github_token" ? secret : ""}
              placeholder="ghp_… (stored in Credential Manager)"
              onChange={(event) => {
                setSecretKind("github_token");
                setSecret(event.target.value);
              }}
            />
          </Field>
          <label className="flex items-center gap-3 text-sm text-silver-300">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--vy-accent-500)]"
              checked={draft.integrations.github_read_only}
              onChange={(event) =>
                patchGroup("integrations", "github_read_only", event.target.checked)
              }
            />
            {t("settings.githubReadOnly")}
          </label>
          <label className="flex items-center gap-3 text-sm text-silver-300">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--vy-accent-500)]"
              checked={draft.integrations.google_read_only}
              onChange={(event) =>
                patchGroup("integrations", "google_read_only", event.target.checked)
              }
            />
            {t("settings.googleReadOnly")}
          </label>
          <Field label={t("settings.gmailAddress")}>
            <input
              type="email"
              autoComplete="off"
              className="vy-field"
              value={draft.integrations.gmail_address}
              placeholder="Gmail address"
              onChange={(event) =>
                patchGroup("integrations", "gmail_address", event.target.value)
              }
            />
          </Field>
          <Field label={t("settings.gmailPassword")}>
            <input
              type="password"
              autoComplete="off"
              className="vy-field"
              value={gmailPassword}
              onChange={(event) => setGmailPassword(event.target.value)}
              placeholder="•••• •••• •••• ••••"
            />
          </Field>
          <p className="text-[11px] leading-relaxed text-silver-500">
            {t("settings.gmailLocalHint")}{" "}
            <a
              className="text-accent underline"
              href="https://myaccount.google.com/apppasswords"
              target="_blank"
              rel="noreferrer"
            >
              {t("settings.gmailAppPasswords")}
            </a>
          </p>
          <button type="button" className="vy-btn" onClick={() => void saveGmail()}>
            {t("settings.saveGmail")}
          </button>
          <div className="vy-hairline" />
          <Field label="Google OAuth client JSON (Calendar / drafts)">
            <textarea
              className="vy-field min-h-[76px] resize-y font-mono text-[11px]"
              value={googleClient}
              placeholder={'"installed": { "client_id": "…" }'}
              onChange={(event) => setGoogleClient(event.target.value)}
            />
          </Field>
          <label className="flex items-center gap-3 text-sm text-silver-300">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--vy-accent-500)]"
              checked={googleWrite}
              onChange={(event) => setGoogleWrite(event.target.checked)}
            />
            Request write scopes
          </label>
          <button type="button" className="vy-btn" onClick={() => void connectGoogle()}>
            {t("settings.connectGoogle")}
          </button>
        </Section>

        <Section title={t("settings.interface")}>
          <Field label={t("settings.language")}>
            <select
              className="vy-field"
              value={draft.interface.language}
              onChange={(event) => {
                patchGroup("interface", "language", event.target.value);
                void setLanguage(event.target.value);
              }}
            >
              {LANGUAGES.map((language) => (
                <option key={language.code} value={language.code}>
                  {language.label}
                </option>
              ))}
            </select>
          </Field>
          <label className="flex items-center gap-3 text-sm text-silver-300">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--vy-accent-500)]"
              checked={draft.interface.low_power}
              onChange={(event) =>
                patchGroup("interface", "low_power", event.target.checked)
              }
            />
            {t("settings.lowPower")}
          </label>
        </Section>

        <Section title={t("settings.permissions")}>
          <div className="max-h-[340px] space-y-1 overflow-y-auto pr-1">
            {tools.map((tool) => (
              <label
                key={tool.name}
                className="flex items-center justify-between gap-3 border-b border-white/5 py-1.5 text-xs"
              >
                <span className="flex items-center gap-2">
                  <span className="font-mono text-silver-200">{tool.name}</span>
                  {tool.risk !== "safe" && (
                    <span
                      className="font-display text-[9px] uppercase tracking-[0.12em]"
                      style={{ color: "var(--vy-accent-500)" }}
                    >
                      {tool.risk}
                    </span>
                  )}
                </span>
                <input
                  type="checkbox"
                  className="h-4 w-4 accent-[var(--vy-accent-500)]"
                  checked={tool.enabled}
                  onChange={(event) => void toggleTool(tool.name, event.target.checked)}
                />
              </label>
            ))}
          </div>
        </Section>
      </div>
    </div>
  );
}
