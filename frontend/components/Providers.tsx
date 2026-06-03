"use client";

import { ToastProvider } from "@/components/ToastProvider";

export default function Providers({ children }: { children: React.ReactNode }) {
  return <ToastProvider>{children}</ToastProvider>;
}
