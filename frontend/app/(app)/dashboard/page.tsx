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
      color: "bg-blue-50 text-brand-blue",
      href: "/students",
    },
    {
      label: "Уроков за месяц",
      value: stats.lessons_this_month,
      icon: CalendarDaysIcon,
      color: "bg-emerald-50 text-brand-green",
      href: "/lessons",
    },
    {
      label: "Оплаты за месяц",
      value: formatMoney(stats.payments_this_month),
      icon: BanknotesIcon,
      color: "bg-emerald-50 text-brand-green",
      href: "/lessons",
    },
    {
      label: "Дебиторка",
      value: formatMoney(stats.unpaid_total),
      icon: ExclamationTriangleIcon,
      color: "bg-amber-50 text-amber-600",
      href: "/lessons?filter=unpaid",
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-blue">Дашборд</h1>
      <p className="mt-1 text-slate-500">Обзор практики: уроки, оплаты, долги и ДЗ</p>

      <div className="mt-8 grid sm:grid-cols-2 xl:grid-cols-4 gap-6">
        {cards.map((c) => (
          <Link
            key={c.label}
            href={c.href}
            className="p-6 rounded-2xl bg-white shadow-sm border border-slate-100 hover:shadow-md transition"
          >
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${c.color}`}>
              <c.icon className="w-6 h-6" />
            </div>
            <p className="mt-4 text-sm text-slate-500">{c.label}</p>
            <p className="text-2xl font-bold text-slate-800 mt-1">{c.value}</p>
          </Link>
        ))}
      </div>

      <div className="mt-10 grid lg:grid-cols-2 gap-6">
        <section className="p-6 rounded-2xl bg-white border shadow-sm">
          <h2 className="font-semibold text-brand-blue flex items-center gap-2">
            <ClockIcon className="w-5 h-5" />
            Ближайшие уроки
          </h2>
          {data.upcoming_lessons.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Нет запланированных уроков на 2 недели</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {data.upcoming_lessons.map((l) => (
                <li key={l.id}>
                  <Link
                    href={`/lessons/${l.id}`}
                    className="flex justify-between gap-3 p-3 rounded-xl hover:bg-slate-50 border border-transparent hover:border-slate-100"
                  >
                    <div className="min-w-0">
                      <p className="font-medium">{l.student_name}</p>
                      <p className="text-sm text-slate-500">
                        {new Date(l.lesson_date).toLocaleDateString("ru-RU")} ·{" "}
                        {formatLessonTime(l.lesson_time)} · {l.duration_minutes} мин
                      </p>
                      {l.meeting_url && (
                        <a
                          href={l.meeting_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs font-semibold text-brand-green hover:underline mt-0.5 inline-block"
                        >
                          Войти в урок →
                        </a>
                      )}
                    </div>
                    <span
                      className={`text-xs font-medium px-2 py-1 rounded-lg h-fit shrink-0 ${
                        l.is_paid ? "bg-emerald-50 text-brand-green" : "bg-amber-50 text-amber-700"
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

        <section className="p-6 rounded-2xl bg-white border shadow-sm">
          <h2 className="font-semibold text-brand-blue flex items-center gap-2">
            <BanknotesIcon className="w-5 h-5" />
            Кто должен
          </h2>
          {data.debtors.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Неоплаченных занятий нет</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {data.debtors.map((d) => (
                <li key={d.student_id}>
                  <Link
                    href={`/students/${d.student_id}`}
                    className="flex justify-between p-3 rounded-xl hover:bg-slate-50"
                  >
                    <span className="font-medium">{d.student_name}</span>
                    <span className="text-amber-700 font-semibold">
                      {formatMoney(d.unpaid_amount)} · {d.unpaid_lessons} ур.
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="p-6 rounded-2xl bg-white border shadow-sm">
          <h2 className="font-semibold text-brand-blue flex items-center gap-2">
            <UserMinusIcon className="w-5 h-5" />
            Давно не были
          </h2>
          <p className="text-xs text-slate-400 mt-1">Более 30 дней без занятий</p>
          {data.inactive_students.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Все ученики недавно занимались</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {data.inactive_students.map((s) => (
                <li key={s.student_id}>
                  <Link
                    href={`/students/${s.student_id}`}
                    className="flex justify-between p-3 rounded-xl hover:bg-slate-50"
                  >
                    <span className="font-medium">{s.student_name}</span>
                    <span className="text-sm text-slate-500">
                      {s.last_lesson_date
                        ? `${s.days_since} дн. назад`
                        : "ещё не было уроков"}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="p-6 rounded-2xl bg-white border shadow-sm">
          <h2 className="font-semibold text-brand-blue flex items-center gap-2">
            <DocumentTextIcon className="w-5 h-5" />
            Просроченные ДЗ
          </h2>
          <p className="text-xs text-slate-400 mt-1">Урок проведён, ДЗ не сгенерировано (3+ дня)</p>
          {data.overdue_homework.length === 0 ? (
            <p className="mt-4 text-sm text-slate-500">Всё в порядке</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {data.overdue_homework.map((h) => (
                <li key={h.lesson_id}>
                  <Link
                    href={`/lessons/${h.lesson_id}`}
                    className="flex justify-between p-3 rounded-xl hover:bg-slate-50"
                  >
                    <span className="font-medium">{h.student_name}</span>
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

      <div className="mt-10 p-6 rounded-2xl bg-brand-blue text-white">
        <h2 className="font-semibold text-lg">Быстрые действия</h2>
        <div className="mt-4 flex flex-wrap gap-4">
          <Link
            href="/students"
            className="px-5 py-2.5 rounded-xl bg-white/20 hover:bg-white/30 text-sm font-medium"
          >
            + Ученик
          </Link>
          <Link
            href="/lessons/new"
            className="px-5 py-2.5 rounded-xl bg-brand-green hover:bg-emerald-600 text-sm font-medium"
          >
            + Новое занятие
          </Link>
        </div>
      </div>
    </div>
  );
}
