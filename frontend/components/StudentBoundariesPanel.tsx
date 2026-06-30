"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ClipboardDocumentIcon,
  ShieldExclamationIcon,
  ArrowPathIcon,
} from "@heroicons/react/24/outline";
import { api, ApiError, StudentBoundaries } from "@/lib/api";
import {
  BOUNDARY_MODE_LABELS,
  BOUNDARY_MODE_STYLES,
  BOUNDARY_SIGNAL_LABELS,
  MODE_SEVERITY,
  parseBoundaryMode,
} from "@/lib/boundaries";
import { toast } from "@/lib/toast";

type Props = {
  studentId: number;
  token: string;
  onApplied?: () => void;
};

export default function StudentBoundariesPanel({ studentId, token, onApplied }: Props) {
  const [data, setData] = useState<StudentBoundaries | null>(null);
  const [loading, setLoading] = useState(true);
  const [copying, setCopying] = useState(false);
  const [applying, setApplying] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    api.students
      .getBoundaries(token, studentId)
      .then(setData)
      .catch((e) => {
        if (e instanceof ApiError) toast(e.message, "error");
      })
      .finally(() => setLoading(false));
  }, [studentId, token]);

  useEffect(() => {
    load();
  }, [load]);

  const currentMode = parseBoundaryMode(data?.boundary_mode);
  const suggestedMode = parseBoundaryMode(data?.suggested_mode);
  const needsUpgrade =
    data && MODE_SEVERITY[suggestedMode] > MODE_SEVERITY[currentMode];
  const styles = BOUNDARY_MODE_STYLES[currentMode];

  const copyMessage = async () => {
    if (!data) return;
    setCopying(true);
    try {
      let text = data.notification_message;
      if (!text) {
        const msg = await api.students.getBoundaryMessage(token, studentId, suggestedMode);
        text = msg.message;
      }
      if (!text) {
        toast("Нет текста для этого режима", "info");
        return;
      }
      await navigator.clipboard.writeText(text);
      toast("Сообщение скопировано — вставь в Telegram", "success");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Не удалось скопировать", "error");
    } finally {
      setCopying(false);
    }
  };

  const applySuggested = async () => {
    if (!data) return;
    setApplying(true);
    try {
      await api.students.applyBoundaries(token, studentId, {
        mode: data.suggested_mode,
        reason: data.suggested_reason,
      });
      toast("Режим применён", "success");
      load();
      onApplied?.();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка применения", "error");
    } finally {
      setApplying(false);
    }
  };

  if (loading) {
    return (
      <div className="mt-6 p-5 rounded-2xl border border-slate-100 bg-slate-50 animate-pulse h-28" />
    );
  }

  if (!data) return null;

  const activeSignals = Object.entries(data.signals).filter(([, v]) => v > 0);
  const displayRules =
    needsUpgrade && data.rules ? data.rules : data.rules;

  return (
    <div className={`mt-6 p-5 rounded-2xl border ${styles.panel}`}>
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className={`mt-1 w-2.5 h-2.5 rounded-full shrink-0 ${styles.dot}`} />
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <ShieldExclamationIcon className="w-5 h-5 text-slate-600" />
              <h2 className="font-semibold text-slate-900">Границы ученика</h2>
              <span
                className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-semibold border ${styles.badge}`}
              >
                {BOUNDARY_MODE_LABELS[currentMode]}
              </span>
            </div>
            {data.boundary_reason && currentMode !== "normal" && (
              <p className="mt-2 text-sm text-slate-600">{data.boundary_reason}</p>
            )}
          </div>
        </div>

        <div className="flex flex-wrap gap-2 shrink-0">
          {(needsUpgrade || currentMode !== "normal") && (
            <button
              type="button"
              onClick={copyMessage}
              disabled={copying}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
            >
              <ClipboardDocumentIcon className="w-4 h-4" />
              {copying ? "Копирую…" : "Скопировать сообщение"}
            </button>
          )}
          {needsUpgrade && (
            <button
              type="button"
              onClick={applySuggested}
              disabled={applying}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-blue text-white text-sm font-medium hover:bg-blue-900 disabled:opacity-50"
            >
              <ArrowPathIcon className="w-4 h-4" />
              {applying ? "Применяю…" : `Применить: ${BOUNDARY_MODE_LABELS[suggestedMode]}`}
            </button>
          )}
        </div>
      </div>

      {needsUpgrade && (
        <div className="mt-4 p-3 rounded-xl bg-white/70 border border-white text-sm text-slate-700">
          <p className="font-medium">
            CRM рекомендует ужесточить режим до «{BOUNDARY_MODE_LABELS[suggestedMode]}»
          </p>
          <p className="mt-1 text-slate-600">{data.suggested_reason}</p>
        </div>
      )}

      {activeSignals.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {activeSignals.map(([key, value]) => (
            <span
              key={key}
              className="inline-flex px-2.5 py-1 rounded-lg bg-white/80 border border-slate-200 text-xs text-slate-600"
            >
              {BOUNDARY_SIGNAL_LABELS[key] ?? key}: <strong className="ml-1">{value}</strong>
            </span>
          ))}
        </div>
      )}

      {displayRules && (currentMode !== "normal" || needsUpgrade) && (
        <dl className="mt-4 grid sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 rounded-xl bg-white/80">
            <dt className="text-slate-500">Перенос</dt>
            <dd className="mt-1 font-medium text-slate-800">{displayRules.reschedule_notice}</dd>
          </div>
          <div className="p-3 rounded-xl bg-white/80">
            <dt className="text-slate-500">Оплата</dt>
            <dd className="mt-1 font-medium text-slate-800">{displayRules.payment}</dd>
          </div>
          <div className="p-3 rounded-xl bg-white/80">
            <dt className="text-slate-500">Слоты</dt>
            <dd className="mt-1 font-medium text-slate-800">{displayRules.slots}</dd>
          </div>
        </dl>
      )}
    </div>
  );
}
