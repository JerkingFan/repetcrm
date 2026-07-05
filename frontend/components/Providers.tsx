"use client";

import { ToastProvider } from "@/components/ToastProvider";
import SentryInit from "@/components/SentryInit";
import PwaRegister from "@/components/PwaRegister";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ToastProvider>
      <SentryInit />
      <PwaRegister />
      {children}
    </ToastProvider>
  );
}
