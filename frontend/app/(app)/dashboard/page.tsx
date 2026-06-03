"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  UserGroupIcon,
  CalendarDaysIcon,
  BanknotesIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline";
import { getToken } from "@/lib/auth";
import { api } from "@/lib/api";
import { formatMoney } from "@/lib/currency";
import LoadingSpinner from "@/components/LoadingSpinner";

export default function DashboardPage() {
  const [stats, setStats] = useState<{
    students_count: number;
    lessons_this_month: number;
    payments_this_month: number;
    unpaid_total: number;
  } | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api.dashboard(token).then(setStats);
  }, []);

  if (!stats) return <LoadingSpinner label="Загрузка дашборда..." />;

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
      href: "/lessons",
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-blue">Дашборд</h1>
      <p className="mt-1 text-slate-500">Обзор вашей репетиторской практики</p>
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
