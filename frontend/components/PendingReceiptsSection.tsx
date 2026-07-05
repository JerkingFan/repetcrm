"use client";

import { useState } from "react";
import Link from "next/link";
import { BanknotesIcon } from "@heroicons/react/24/outline";
import { api, ApiError, authFetch, DashboardExtended } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { toast } from "@/lib/toast";

export default function PendingReceiptsSection({
  receipts,
  onRefresh,
}: {
  receipts: DashboardExtended["pending_payment_receipts"];
  onRefresh: () => void;
}) {
  const [busyId, setBusyId] = useState<number | null>(null);

  if (receipts.length === 0) return null;

  const openFile = async (id: number) => {
    const res = await authFetch(api.paymentReceipts.fileUrl(id));
    if (!res.ok) {
      toast("Не удалось открыть чек", "error");
      return;
    }
    const blob = await res.blob();
    window.open(URL.createObjectURL(blob), "_blank");
  };

  const confirm = async (id: number) => {
    setBusyId(id);
    try {
      await api.paymentReceipts.confirm(id);
      toast("Оплата зачислена на баланс", "success");
      onRefresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка", "error");
    } finally {
      setBusyId(null);
    }
  };

  const reject = async (id: number) => {
    const note = window.prompt("Причина отклонения (необязательно):") ?? "";
    setBusyId(id);
    try {
      await api.paymentReceipts.reject(id, note);
      toast("Чек отклонён", "success");
      onRefresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка", "error");
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className="mt-10 p-6 rounded-2xl bg-white border shadow-sm">
      <h2 className="font-semibold text-brand-blue flex items-center gap-2">
        <BanknotesIcon className="w-5 h-5" />
        Ожидают подтверждения
      </h2>
      <p className="text-xs text-slate-400 mt-1">Родитель прислал чек об оплате</p>
      <ul className="mt-4 space-y-3">
        {receipts.map((r) => (
          <li key={r.id} className="p-4 rounded-xl border border-amber-100 bg-amber-50/50 space-y-2">
            <div className="flex flex-wrap justify-between gap-2">
              <div>
                <Link href={`/students/${r.student_id}`} className="font-medium hover:text-brand-blue">
                  {r.student_name}
                </Link>
                <p className="text-sm text-slate-600">
                  {formatMoney(r.amount)} · {new Date(r.created_at).toLocaleString("ru-RU")}
                </p>
                {r.parent_note && <p className="text-xs text-slate-500 mt-1">{r.parent_note}</p>}
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => openFile(r.id)}
                  className="px-3 py-1.5 rounded-lg border text-xs bg-white"
                >
                  Чек
                </button>
                <button
                  type="button"
                  disabled={busyId === r.id}
                  onClick={() => confirm(r.id)}
                  className="px-3 py-1.5 rounded-lg bg-brand-green text-white text-xs font-medium disabled:opacity-50"
                >
                  Зачислить
                </button>
                <button
                  type="button"
                  disabled={busyId === r.id}
                  onClick={() => reject(r.id)}
                  className="px-3 py-1.5 rounded-lg border text-xs text-red-600 bg-white disabled:opacity-50"
                >
                  Отклонить
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
