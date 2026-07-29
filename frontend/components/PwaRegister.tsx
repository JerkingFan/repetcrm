"use client";

import { useEffect } from "react";
import { flushQueue, type QueuedMutation } from "@/lib/offlineQueue";
import { getApiUrl } from "@/lib/apiUrl";

export default function PwaRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {
      /* optional — ignore registration errors in dev */
    });
  }, []);

  useEffect(() => {
    const send = async (item: QueuedMutation) => {
      const res = await fetch(`${getApiUrl()}${item.path}`, {
        method: item.method,
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: item.body,
      });
      return res.ok;
    };

    const flush = async () => {
      try {
        await flushQueue(send);
      } catch {
        // ignore
      }
    };

    // Initial attempt on load
    if (navigator.onLine) flush();
    // Retry when connection is restored
    window.addEventListener("online", flush);
    return () => window.removeEventListener("online", flush);
  }, []);

  return null;
}
