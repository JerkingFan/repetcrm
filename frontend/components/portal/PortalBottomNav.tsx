"use client";

import type { ReactNode } from "react";
import type { PortalTab } from "@/lib/portalUi";

const TABS: { id: PortalTab; label: string; icon: ReactNode }[] = [
  {
    id: "home",
    label: "Главная",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5Z"
        />
      </svg>
    ),
  },
  {
    id: "homework",
    label: "ДЗ",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2m-6 9 2 2 4-4"
        />
      </svg>
    ),
  },
  {
    id: "schedule",
    label: "Уроки",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M8 7V3m8 4V3M4 11h16M5 5h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"
        />
      </svg>
    ),
  },
  {
    id: "progress",
    label: "Прогресс",
    icon: (
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 17l6-6 4 4 8-8M14 7h7v7" />
      </svg>
    ),
  },
];

export default function PortalBottomNav({
  tab,
  onChange,
  homeworkBadge = 0,
}: {
  tab: PortalTab;
  onChange: (t: PortalTab) => void;
  homeworkBadge?: number;
}) {
  return (
    <nav className="fixed bottom-0 inset-x-0 z-40 portal-bottom-nav safe-area-pb">
      <div className="max-w-lg mx-auto grid grid-cols-4 px-1">
        {TABS.map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onChange(t.id)}
              className={`relative flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-semibold transition-all ${
                active ? "text-[var(--portal-accent)]" : "text-slate-400 hover:text-slate-600"
              }`}
            >
              <span
                className={`relative flex items-center justify-center w-10 h-8 rounded-xl transition-all ${
                  active ? "bg-[var(--portal-accent)]/10 scale-105" : ""
                }`}
              >
                {t.icon}
                {t.id === "homework" && homeworkBadge > 0 && (
                  <span className="absolute -top-1 -right-1 min-w-[16px] h-4 px-1 rounded-md bg-rose-500 text-white text-[10px] leading-4 text-center font-bold">
                    {homeworkBadge > 9 ? "9+" : homeworkBadge}
                  </span>
                )}
              </span>
              {t.label}
            </button>
          );
        })}
      </div>
    </nav>
  );
}
