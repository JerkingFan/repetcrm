"use client";

import { useState } from "react";
import Link from "next/link";
import { AcademicCapIcon } from "@heroicons/react/24/outline";
import { api, ApiError } from "@/lib/api";
import { formatLessonTime } from "@/lib/calendar";
import { toast } from "@/lib/toast";
import TrialFollowupBanner from "@/components/TrialFollowupBanner";
import type { DashboardExtended } from "@/lib/api";

export default function TrialFunnelSection({
  data,
  onRefresh,
}: {
  data: DashboardExtended;
  onRefresh: () => void;
}) {
  const [conductingId, setConductingId] = useState<number | null>(null);
  const [followupMessage, setFollowupMessage] = useState<string | null>(null);

  const trials = data.trial_lessons_this_week;
  const followups = data.trial_followups;

  if (trials.length === 0 && followups.length === 0) return null;

  const markConducted = async (lessonId: number) => {
    setConductingId(lessonId);
    try {
      const res = await api.lessons.quickConduct(lessonId);
      if (res.trial_followup?.message) {
        setFollowupMessage(res.trial_followup.message);
      }
      toast("Урок отмечен проведённым", "success");
      onRefresh();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Ошибка", "error");
    } finally {
      setConductingId(null);
    }
  };

  return (
    <div className="mt-10 space-y-6">
      {followupMessage && (
        <TrialFollowupBanner message={followupMessage} />
      )}

      <div className="grid lg:grid-cols-2 gap-6">
        {trials.length > 0 && (
          <section className="p-6 rounded-2xl bg-white border shadow-sm">
            <h2 className="font-semibold text-brand-blue flex items-center gap-2">
              <AcademicCapIcon className="w-5 h-5" />
              Пробные на этой неделе
            </h2>
            <p className="text-xs text-slate-400 mt-1">Ученики со статусом пробный / лид</p>
            <ul className="mt-4 space-y-3">
              {trials.map((t) => (
                <li
                  key={t.lesson_id}
                  className="flex flex-wrap justify-between gap-2 p-3 rounded-xl border border-slate-100"
                >
                  <div>
                    <Link href={`/lessons/${t.lesson_id}`} className="font-medium hover:text-brand-blue">
                      {t.student_name}
                    </Link>
                    <p className="text-sm text-slate-500">
                      {new Date(t.lesson_date).toLocaleDateString("ru-RU")} ·{" "}
                      {formatLessonTime(t.lesson_time)}
                      {t.student_status === "lead" ? " · лид" : ""}
                    </p>
                  </div>
                  {t.is_conducted ? (
                    <span className="text-xs font-medium px-2 py-1 rounded-lg bg-emerald-50 text-brand-green h-fit">
                      проведён
                    </span>
                  ) : (
                    <button
                      type="button"
                      disabled={conductingId === t.lesson_id}
                      onClick={() => markConducted(t.lesson_id)}
                      className="text-xs font-medium px-3 py-1.5 rounded-lg bg-brand-green text-white disabled:opacity-50 h-fit"
                    >
                      {conductingId === t.lesson_id ? "…" : "Проведён"}
                    </button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        )}

        {followups.length > 0 && (
          <section className="p-6 rounded-2xl bg-white border shadow-sm space-y-4">
            <h2 className="font-semibold text-brand-blue">Дожать после пробного</h2>
            <p className="text-xs text-slate-400">Проведён 1 урок — отправьте родителю предложение</p>
            <ul className="space-y-4">
              {followups.map((f) => (
                <li key={f.student_id} className="space-y-2">
                  <div className="flex justify-between items-center gap-2">
                    <Link href={`/students/${f.student_id}`} className="font-medium hover:text-brand-blue">
                      {f.student_name}
                    </Link>
                    {f.parent_name && (
                      <span className="text-xs text-slate-500">{f.parent_name}</span>
                    )}
                  </div>
                  <TrialFollowupBanner message={f.message} title="" />
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
