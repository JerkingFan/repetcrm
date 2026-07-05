"use client";

import { useEffect } from "react";

/** Optional browser error reporting when NEXT_PUBLIC_SENTRY_DSN is set. */
export default function SentryInit() {
  useEffect(() => {
    const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN?.trim();
    if (!dsn) return;

    void import("@sentry/browser").then((Sentry) => {
      Sentry.init({
        dsn,
        environment: process.env.NODE_ENV,
        tracesSampleRate: 0.1,
      });
    });
  }, []);

  return null;
}
