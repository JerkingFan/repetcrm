"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { toast } from "@/lib/toast";

export default function PaymentRequisitesSettings() {
  const [details, setDetails] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getPaymentRequisites().then((r) => setDetails(r.payment_details)).catch(() => {});
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.updatePaymentRequisites(details);
      setDetails(r.payment_details);
      toast("Реквизиты сохранены", "success");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка сохранения", "error");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mt-8 p-6 rounded-2xl bg-white border shadow-sm space-y-4">
      <div>
        <h2 className="font-semibold text-brand-blue">Реквизиты для оплаты</h2>
        <p className="text-sm text-slate-500 mt-1">
          Родитель увидит их в кабинете, переведёт деньги и прикрепит чек (фото или PDF). Вы
          подтверждаете поступление в дашборде.
        </p>
      </div>
      <textarea
        value={details}
        onChange={(e) => setDetails(e.target.value)}
        rows={6}
        className="w-full px-4 py-3 rounded-xl border text-sm font-mono"
        placeholder={`Например:\nБанк: Беларусбанк\nIBAN: BY00...\nПолучатель: Иванов И.И.\nНазначение: Оплата занятий`}
      />
      <button
        type="button"
        onClick={save}
        disabled={saving}
        className="px-5 py-2.5 rounded-xl bg-brand-blue text-white text-sm font-medium disabled:opacity-50"
      >
        {saving ? "Сохранение…" : "Сохранить реквизиты"}
      </button>
    </div>
  );
}
