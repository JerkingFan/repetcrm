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
      <div className="portal-atmosphere" aria-hidden>
        <span className="portal-orb portal-orb-a" />
        <span className="portal-orb portal-orb-b" />
        <span className="portal-grain" />
      </div>

      <header className="sticky top-0 z-30 portal-header">
        <div className="max-w-lg mx-auto px-4 py-3.5 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="portal-kicker">RepetCRM · кабинет</p>
            <h1 className="portal-title truncate">{title}</h1>
            {subtitle && <p className="portal-subtitle truncate">{subtitle}</p>}
          </div>
          {right}
        </div>
      </header>
      <main className="relative z-10 max-w-lg mx-auto px-4 pt-5 pb-28 space-y-4">{children}</main>
    </div>
  );
}

export function PortalCard({
  children,
  className = "",
  style,
}: {
  children: ReactNode;
  className?: string;
  style?: CSSProperties;
}) {
  return (
    <section className={`portal-card ${className}`} style={style}>
      {children}
    </section>
  );
}

export function PortalEmpty({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="py-12 px-4 text-center">
      <div className="mx-auto w-14 h-14 rounded-2xl bg-[var(--portal-accent)]/8 flex items-center justify-center text-[var(--portal-accent)] mb-3">
        <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M9 12h6m-6 4h6M7 4h10a2 2 0 0 1 2 2v14l-7-3-7 3V6a2 2 0 0 1 2-2Z"
          />
        </svg>
      </div>
      <p className="font-semibold text-slate-800" style={{ fontFamily: "var(--font-portal-display), sans-serif" }}>
        {title}
      </p>
      {hint && <p className="text-sm text-slate-500 mt-1.5 leading-relaxed">{hint}</p>}
    </div>
  );
}
