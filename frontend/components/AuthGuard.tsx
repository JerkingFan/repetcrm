"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { clearLegacyToken } from "@/lib/auth";
import { api } from "@/lib/api";

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ok, setOk] = useState(false);

  useEffect(() => {
    let cancelled = false;
    clearLegacyToken();

    async function checkAuth() {
      async function loadUser() {
        const user = await api.me();
        if (cancelled) return;
        if (!user.onboarding_completed && pathname !== "/onboarding") {
          router.replace("/onboarding");
          return;
        }
        setOk(true);
      }

      try {
        await loadUser();
      } catch {
        const refreshed = await api.refresh();
        if (!refreshed) {
          if (!cancelled) router.replace("/login");
          return;
        }
        try {
          await loadUser();
        } catch {
          if (!cancelled) router.replace("/login");
        }
      }
    }

    checkAuth();
    return () => {
      cancelled = true;
    };
  }, [router, pathname]);

  if (!ok) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-10 h-10 border-4 border-brand-blue border-t-transparent rounded-full" />
      </div>
    );
  }
  return <>{children}</>;
}
