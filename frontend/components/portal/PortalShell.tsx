"use client";

import type { CSSProperties, ReactNode } from "react";
import { themeVars } from "@/lib/portalTheme";

export default function PortalShell({
  children,
  title,
  subtitle,
  right,
  theme = "ocean",
}: {
  children: ReactNode;
  title: string;
  subtitle?: string;
  right?: ReactNode;
  theme?: string;
}) {
  const vars = themeVars(theme) as CSSProperties;

  return (
    <div className="min-h-screen portal-shell" style={vars}>
      <header className="sticky top-0 z-30 border-b border-white/60 bg-white/80 backdrop-blur-md">
        <div className="max-w-lg mx-auto px-4 py-3.5 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p
              className="text-[11px] font-semibold tracking-wide uppercase"
              style={{ color: "var(--portal-accent-soft)" }}
            >
              RepetCRM · кабинет
            </p>
            <h1 className="text-xl font-bold truncate" style={{ color: "var(--portal-accent)" }}>
              {title}
            </h1>
            {subtitle && <p className="text-sm text-slate-500 mt-0.5 truncate">{subtitle}</p>}
          </div>
          {right}
        </div>
      </header>
      <main className="max-w-lg mx-auto px-4 pt-5 pb-28 space-y-5">{children}</main>
    </div>
  );
}

export function PortalCard({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-slate-200/80 bg-white shadow-sm shadow-slate-200/40 ${className}`}
    >
      {children}
    </section>
  );
}

export function PortalEmpty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="py-10 px-4 text-center">
      <div className="mx-auto w-12 h-12 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 mb-3">
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 12h6m-6 4h6M7 4h10a2 2 0 0 1 2 2v14l-7-3-7 3V6a2 2 0 0 1 2-2Z"
          />
        </svg>
      </div>
      <p className="font-medium text-slate-700">{title}</p>
      {hint && <p className="text-sm text-slate-500 mt-1">{hint}</p>}
    </div>
  );
}
