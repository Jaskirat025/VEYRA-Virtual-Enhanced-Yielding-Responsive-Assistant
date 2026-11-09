import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ConfirmDialog } from "./components/ConfirmDialog";
import { Sidebar } from "./components/Sidebar";
import { StatusBar } from "./components/StatusBar";
import { TitleBar } from "./components/TitleBar";
import { useVeyra } from "./lib/useVeyra";
import type { View } from "./lib/types";
import { useI18n } from "./i18n";
import { ChatScreen } from "./screens/Chat";
import { HomeScreen } from "./screens/Home";
import { Onboarding } from "./screens/Onboarding";
import { SettingsScreen } from "./screens/Settings";
import { ToolLogScreen } from "./screens/ToolLog";

export default function App() {
  const { onboarded, error, notice, dismissError, dismissNotice } = useVeyra();
  const { t } = useI18n();
  const [view, setView] = useState<View>("home");

  return (
    <div className="vy-app-bg vy-grain relative flex h-screen flex-col overflow-hidden">
      <TitleBar />

      <div className="flex min-h-0 flex-1">
        <Sidebar view={view} onChange={setView} />

        <main className="vy-grid relative min-w-0 flex-1 overflow-y-auto">
          {onboarded === null ? (
            <div className="flex h-full items-center justify-center">
              <span className="vy-label animate-pulse">INITIALISING</span>
            </div>
          ) : !onboarded ? (
            <Onboarding />
          ) : (
            <AnimatePresence mode="wait">
              <motion.div
                key={view}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
                className="h-full"
              >
                {view === "home" && <HomeScreen />}
                {view === "chat" && <ChatScreen />}
                {view === "tools" && <ToolLogScreen />}
                {view === "settings" && <SettingsScreen />}
              </motion.div>
            </AnimatePresence>
          )}
        </main>
      </div>

      <StatusBar />
      <ConfirmDialog />

      <div className="pointer-events-none fixed bottom-12 right-4 z-40 flex w-[min(92vw,380px)] flex-col gap-2">
        {error && (
          <div className="vy-panel pointer-events-auto flex items-start gap-3 p-3">
            <span
              className="mt-1 inline-block h-2 w-2 shrink-0 rounded-full"
              style={{ backgroundColor: "var(--vy-accent-500)" }}
            />
            <p className="flex-1 text-xs leading-relaxed text-silver-300">{error}</p>
            <button
              type="button"
              className="text-xs text-silver-500 hover:text-silver-100"
              onClick={dismissError}
              aria-label={t("common.close")}
            >
              ×
            </button>
          </div>
        )}

        {notice && (
          <div className="vy-panel pointer-events-auto flex items-start gap-3 p-3">
            <span className="vy-label mt-0.5">{t("notice.timer")}</span>
            <p className="flex-1 text-xs text-silver-300">{notice}</p>
            <button
              type="button"
              className="text-xs text-silver-500 hover:text-silver-100"
              onClick={dismissNotice}
              aria-label={t("common.close")}
            >
              ×
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
