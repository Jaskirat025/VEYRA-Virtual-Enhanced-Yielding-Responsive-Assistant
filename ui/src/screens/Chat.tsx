import { useEffect, useRef } from "react";
import { ToolCard } from "../components/ToolCard";
import { useVeyra } from "../lib/useVeyra";
import { useI18n } from "../i18n";

export function ChatScreen() {
  const { messages, toolEvents } = useVeyra();
  const { t } = useI18n();
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, toolEvents.length]);

  return (
    <div className="mx-auto flex h-full w-full max-w-content flex-col px-6 py-6">
      <div className="mb-4 flex items-baseline justify-between">
        <h1 className="font-display text-2xl tracking-wide text-silver-100">{t("chat.title")}</h1>
        <span className="vy-label">{t("chat.messages", { count: messages.length })}</span>
      </div>

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-2">
        {messages.length === 0 && (
          <p className="mt-16 text-center text-sm text-silver-500">{t("chat.empty")}</p>
        )}

        {messages.map((message, index) => {
          const isUser = message.role === "user";
          return (
            <article
              key={`${message.role}-${index}`}
              className={`max-w-[85%] ${isUser ? "ml-auto text-right" : "mr-auto"}`}
            >
              <p className="vy-label mb-1">
                {isUser ? t("chat.you") : t("chat.veyra")}
                {message.used_online ? " · ONLINE" : ""}
              </p>
              <div
                className={`vy-panel-flat px-4 py-3 text-sm leading-relaxed ${
                  isUser ? "text-silver-300" : "text-silver-100"
                }`}
                style={
                  isUser
                    ? undefined
                    : { boxShadow: "inset 0 0 0 1px var(--vy-line), inset 2px 0 0 var(--vy-accent-500)" }
                }
              >
                {message.text}
              </div>
            </article>
          );
        })}

        {toolEvents.length > 0 && (
          <div className="space-y-2 pt-2">
            <p className="vy-label">{t("tools.title")}</p>
            {toolEvents.map((event) => (
              <ToolCard key={event.id} event={event} />
            ))}
          </div>
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}
