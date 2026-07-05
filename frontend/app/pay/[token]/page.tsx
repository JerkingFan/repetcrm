"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function PayPage() {
  const params = useParams();
  const token = String(params.token || "");
  const [payment, setPayment] = useState<Awaited<ReturnType<typeof api.payments.getPublic>> | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = () => {
    api.payments
      .getPublic(token)
      .then(setPayment)
      .catch(() => setPayment(null))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (token) load();
  }, [token]);

  const confirmCard = async () => {
    setPaying(true);
    setError("");
    try {
      await api.payments.simulatePay(token);
      setSuccess("Оплата прошла успешно!");
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка оплаты");
    } finally {
      setPaying(false);
    }
  };

  if (loading) return <LoadingSpinner label="Загрузка..." />;

  if (!payment) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <Alert message="Ссылка на оплату не найдена или истекла" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white rounded-2xl border shadow-sm p-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold text-brand-blue">Оплата занятий</h1>
          <p className="text-sm text-slate-500 mt-1">{payment.student_name}</p>
        </div>

        <p className="text-3xl font-bold">{formatMoney(payment.amount)}</p>

        {payment.status === "paid" ? (
          <div className="p-4 rounded-xl bg-emerald-50 text-brand-green font-medium">
            Оплачено ✓
          </div>
        ) : payment.provider === "erip" ? (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">Оплатите через ЕРИП по коду:</p>
            <p className="text-2xl font-mono font-bold tracking-wider text-center p-4 bg-slate-50 rounded-xl">
              {payment.erip_code}
            </p>
            <p className="text-xs text-slate-400">
              В банке: Платежи → ЕРИП → введите код. После оплаты баланс обновится автоматически
              (webhook).
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-slate-600">Оплата банковской картой</p>
            <button
              type="button"
              onClick={confirmCard}
              disabled={paying}
              className="w-full py-3 rounded-xl bg-brand-green text-white font-medium disabled:opacity-50"
            >
              {paying ? "Обработка…" : `Оплатить ${formatMoney(payment.amount)}`}
            </button>
            <p className="text-xs text-slate-400 text-center">
              В продакшене — редирект на платёжный шлюз. Webhook подтвердит оплату.
            </p>
          </div>
        )}

        {error && <Alert message={error} />}
        {success && <Alert type="success" message={success} />}
      </div>
    </div>
  );
}
