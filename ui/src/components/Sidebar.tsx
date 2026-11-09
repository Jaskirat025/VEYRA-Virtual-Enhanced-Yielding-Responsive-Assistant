import type { View } from "../lib/types";
import { useI18n } from "../i18n";

interface SidebarProps {
  view: View;
  onChange: (view: View) => void;
}

const items: { view: View; key: string; path: string }[] = [
  { view: "home", key: "nav.home", path: "M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" },
  { view: "chat", key: "nav.chat", path: "M4 4h16v12H8l-4 4z" },
  {
    view: "tools",
    key: "nav.tools",
    path: "M4 6h16M4 12h16M4 18h10",
  },
  {
    view: "settings",
    key: "nav.settings",
    path: "M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7z M19 12l1.5 1.2-1.4 2.4-1.8-.6a7 7 0 0 1-1.7 1l-.3 1.9h-2.8l-.3-1.9a7 7 0 0 1-1.7-1l-1.8.6-1.4-2.4L5 12l-1.5-1.2 1.4-2.4 1.8.6a7 7 0 0 1 1.7-1l.3-1.9h2.8l.3 1.9a7 7 0 0 1 1.7 1l1.8-.6 1.4 2.4z",
  },
];

export function Sidebar({ view, onChange }: SidebarProps) {
  const { t } = useI18n();

  return (
    <nav
      aria-label="Primary"
      className="flex w-16 shrink-0 flex-col gap-1 border-r border-white/10 bg-gunmetal-900/55 py-4 xl:w-52"
    >
      {items.map((item) => {
        const active = view === item.view;
        return (
          <button
            key={item.view}
            type="button"
            onClick={() => onChange(item.view)}
            aria-current={active ? "page" : undefined}
            className={`group relative mx-2 flex items-center gap-3 rounded-md px-3 py-2.5 text-left transition-colors duration-150 ${
              active
                ? "bg-white/[0.055] text-silver-100"
                : "text-silver-500 hover:bg-white/[0.035] hover:text-silver-100"
            }`}
          >
            {active && (
              <span
                aria-hidden="true"
                className="absolute left-0 top-1/2 h-6 w-[2px] -translate-y-1/2"
                style={{ backgroundColor: "var(--vy-accent-500)" }}
              />
            )}
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
              className="shrink-0"
            >
              <path d={item.path} />
            </svg>
            <span className="hidden text-[12px] uppercase tracking-[0.14em] xl:inline">
              {t(item.key)}
            </span>
          </button>
        );
      })}

      <div className="mt-auto hidden px-5 xl:block">
        <div className="vy-hairline mb-3" />
        <p className="vy-label leading-relaxed opacity-70">VEYRA 0.1</p>
      </div>
    </nav>
  );
}
