"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  UserGroupIcon,
  CalendarDaysIcon,
  BanknotesIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  UserMinusIcon,
  DocumentTextIcon,
} from "@heroicons/react/24/outline";
import { api, DashboardExtended } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import { formatLessonTime } from "@/lib/calendar";
import LoadingSpinner from "@/components/LoadingSpinner";
import AnalyticsSection from "@/components/AnalyticsSection";
import TrialFunnelSection from "@/components/TrialFunnelSection";
import PendingReceiptsSection from "@/components/PendingReceiptsSection";
import RescheduleRequestsSection from "@/components/RescheduleRequestsSection";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardExtended | null>(null);

  const reload = () => {
    api.dashboardExtended().then(setData);
  };

  useEffect(() => {
    reload();
  }, []);

  if (!data) return <LoadingSpinner label="Загрузка дашборда..." />;

  const stats = data.stats;

  const cards = [
    {
      label: "Учеников",
      value: stats.students_count,
      icon: UserGroupIcon,
      tone: "bg-teal-50 text-brand-blue",
      href: "/students",
    },
    {
      label: "Уроков за месяц",
      value: stats.lessons_this_month,
      icon: CalendarDaysIcon,
      tone: "bg-emerald-50 text-emerald-700",
      href: "/lessons",
    },
    {
      label: "Оплаты за месяц",
      value: formatMoney(stats.payments_this_month),
      icon: BanknotesIcon,
      tone: "bg-cyan-50 text-cyan-700",
      href: "/lessons",
    },
    {
      label: "Дебиторка",
      value: formatMoney(stats.unpaid_total),
      icon: ExclamationTriangleIcon,
      tone: "bg-amber-50 text-amber-700",
      href: "/lessons?filter=unpaid",
    },
  ];

  return (
    <div className="max-w-6xl">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-brand-blue/70">
            Сегодня
          </p>
          <h1 className="rc-page-title mt-1">Дашборд</h1>
          <p className="rc-page-sub">Уроки, оплаты, долги и ДЗ — всё под рукой</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/students" className="rc-btn-ink !py-2.5">
            + Ученик
          </Link>
          <Link href="/lessons/new" className="rc-btn-primary !py-2.5">
            + Занятие
          </Link>
        </div>
      </div>

      <div className="mt-8 grid sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {cards.map((c, i) => (
          <Link
            key={c.label}
            href={c.href}
            className="rc-stat"
            style={{ animationDelay: `${i * 50}ms` }}
          >
            <div className={`w-11 h-11 rounded-xl flex items-center justify-center ${c.tone}`}>
              <c.icon className="w-5 h-5" />
            </div>
            <p className="mt-4 text-sm text-slate-500">{c.label}</p>
            <p className="font-display text-2xl font-bold text-brand-ink mt-1 tracking-tight">
              {c.value}
            </p>
          </Link>
        ))}
      </div>

      <div className="mt-8 grid lg:grid-cols-2 gap-5">
        <section className="rc-card-pad">
          <h2 className="rc-section-title flex items-center gap-2">
            <ClockIcon className="w-5 h-5 text-brand-blue" />
            Ближайшие уроки
          </h2>
          {data.upcoming_lessons.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Нет запланированных уроков на 2 недели</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {data.upcoming_lessons.map((l) => (
                <li key={l.id}>
                  <Link
                    href={`/lessons/${l.id}`}
                    className="flex justify-between gap-3 p-3 rounded-xl hover:bg-teal-50/60 border border-transparent hover:border-teal-100/80 transition"
                  >
                    <div className="min-w-0">
                      <p className="font-semibold text-slate-900">{l.student_name}</p>
                      <p className="text-sm text-slate-500 mt-0.5">
                        {new Date(l.lesson_date).toLocaleDateString("ru-RU")} ·{" "}
                        {formatLessonTime(l.lesson_time)} · {l.duration_minutes} мин
                      </p>
                      {l.meeting_url && (
                        <span
                          onClick={(e) => {
                            e.preventDefault();
                            window.open(l.meeting_url!, "_blank", "noopener,noreferrer");
                          }}
                          className="text-xs font-bold text-brand-green hover:underline mt-1 inline-block cursor-pointer"
                        >
                          Войти в урок →
                        </span>
                      )}
                    </div>
                    <span
                      className={`text-xs font-semibold px-2 py-1 rounded-lg h-fit shrink-0 ${
                        l.is_paid ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                      }`}
                    >
                      {l.is_paid ? "оплачено" : formatMoney(l.payment_amount)}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rc-card-pad">
          <h2 className="rc-section-title flex items-center gap-2">
            <BanknotesIcon className="w-5 h-5 text-brand-blue" />
            Кто должен
          </h2>
          {data.debtors.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Неоплаченных занятий нет</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {data.debtors.map((d) => (
                <li key={d.student_id}>
                  <Link
                    href={`/students/${d.student_id}`}
                    className="flex justify-between p-3 rounded-xl hover:bg-amber-50/50 transition"
                  >
                    <span className="font-semibold text-slate-900">{d.student_name}</span>
                    <span className="text-amber-700 font-bold tabular-nums">
                      {formatMoney(d.unpaid_amount)} · {d.unpaid_lessons} ур.
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rc-card-pad">
          <h2 className="rc-section-title flex items-center gap-2">
            <UserMinusIcon className="w-5 h-5 text-brand-blue" />
            Давно не были
          </h2>
          <p className="text-xs text-slate-400 mt-1">Более 30 дней без занятий</p>
          {data.inactive_students.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Все ученики недавно занимались</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {data.inactive_students.map((s) => (
                <li key={s.student_id}>
                  <Link
                    href={`/students/${s.student_id}`}
                    className="flex justify-between p-3 rounded-xl hover:bg-slate-50 transition"
                  >
                    <span className="font-semibold text-slate-900">{s.student_name}</span>
                    <span className="text-sm text-slate-500">
                      {s.last_lesson_date ? `${s.days_since} дн. назад` : "ещё не было уроков"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rc-card-pad">
          <h2 className="rc-section-title flex items-center gap-2">
            <DocumentTextIcon className="w-5 h-5 text-brand-blue" />
            Просроченные ДЗ
          </h2>
          <p className="text-xs text-slate-400 mt-1">Урок проведён, ДЗ не сгенерировано (3+ дня)</p>
          {data.overdue_homework.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Всё в порядке</p>
          ) : (
            <ul className="mt-4 space-y-2">
              {data.overdue_homework.map((h) => (
                <li key={h.lesson_id}>
                  <Link
                    href={`/lessons/${h.lesson_id}`}
                    className="flex justify-between p-3 rounded-xl hover:bg-amber-50/50 transition"
                  >
                    <span className="font-semibold text-slate-900">{h.student_name}</span>
                    <span className="text-sm text-amber-700">
                      {new Date(h.lesson_date).toLocaleDateString("ru-RU")} · {h.days_since} дн.
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <TrialFunnelSection data={data} onRefresh={reload} />

      <RescheduleRequestsSection />

      <PendingReceiptsSection receipts={data.pending_payment_receipts} onRefresh={reload} />

      <AnalyticsSection />

      <div className="mt-8 relative overflow-hidden rounded-2xl bg-ink-hero text-white p-6 sm:p-8 shadow-lift">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "linear-gradient(115deg, transparent 35%, rgba(255,255,255,0.16) 50%, transparent 65%)",
          }}
          aria-hidden
        />
        <div className="relative">
          <h2 className="font-display text-xl font-bold tracking-tight">Быстрые действия</h2>
          <p className="text-sm text-white/70 mt-1">Добавь ученика или запланируй занятие</p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href="/students"
              className="px-5 py-2.5 rounded-xl bg-white/15 hover:bg-white/25 text-sm font-semibold border border-white/20 transition"
            >
              + Ученик
            </Link>
            <Link
              href="/lessons/new"
              className="px-5 py-2.5 rounded-xl bg-white text-brand-ink text-sm font-bold hover:brightness-95 transition"
            >
              + Новое занятие
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
