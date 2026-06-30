"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  ArrowDownTrayIcon,
  AcademicCapIcon,
  BuildingLibraryIcon,
  PhoneIcon,
} from "@heroicons/react/24/outline";
import { getToken } from "@/lib/auth";
import { api, StudentRecord } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import StudentBoundariesPanel from "@/components/StudentBoundariesPanel";
import BoundaryModeBadge from "@/components/BoundaryModeBadge";
import { toast } from "@/lib/toast";
import { pollJobUntilDone } from "@/lib/jobPoll";

type LessonHistoryItem = {
  id: number;
  lesson_date: string;
  homework_id?: number | null;
};

export default function StudentDetailPage() {
  const params = useParams();
  const id = Number(params.id);
  const [data, setData] = useState<StudentRecord | null>(null);
  const [lessons, setLessons] = useState<LessonHistoryItem[]>([]);
  const [lessonsPage, setLessonsPage] = useState(1);
  const [hasMoreLessons, setHasMoreLessons] = useState(false);
  const [lessonsLoading, setLessonsLoading] = useState(true);
  const [token, setToken] = useState<string | null>(null);

  const loadStudent = useCallback(() => {
    const t = getToken();
    if (!t) return;
    setToken(t);
    api.students.get<StudentRecord>(t, id).then(setData);
  }, [id]);

  const loadLessons = useCallback(
    async (page: number, append: boolean) => {
      const t = getToken();
      if (!t) return;
      setLessonsLoading(true);
      try {
        const res = await api.students.listLessons(t, id, { page, page_size: 20 });
        setLessons((prev) => (append ? [...prev, ...res.items] : res.items));
        setHasMoreLessons(res.has_more);
        setLessonsPage(page);
      } finally {
        setLessonsLoading(false);
      }
    },
    [id]
  );

  useEffect(() => {
    loadStudent();
    loadLessons(1, false);
  }, [loadStudent, loadLessons]);

  const downloadPdf = async (homeworkId: number) => {
    const token = getToken();
    if (!token) return;
    const tryFetchPdf = async () => {
      return await fetch(api.homework.pdfUrl(homeworkId), {
        headers: { Authorization: `Bearer ${token}` },
      });
    };

    let res = await tryFetchPdf();
    if (res.status === 202) {
      const started = (await res.json()) as { job_id: string };
      const polled = await pollJobUntilDone(token, started.job_id);
      if (!polled.ok) {
        toast(polled.error || "Ошибка сборки PDF", "error");
        return;
      }
      res = await tryFetchPdf();
    }

    if (!res.ok) {
      toast("Ошибка скачивания PDF", "error");
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `homework_${homeworkId}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!data) return <LoadingSpinner />;

  return (
    <div>
      <Link href="/students" className="text-sm text-brand-blue hover:underline">
        ← Ученики
      </Link>

      <div className="mt-6 p-6 rounded-2xl bg-white border border-slate-100 shadow-sm">
        <div className="flex flex-wrap gap-2 mb-4">
          <BoundaryModeBadge mode={data.boundary_mode} />
          {data.grade && (
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-brand-blue/10 text-brand-blue text-sm font-semibold">
              <AcademicCapIcon className="w-4 h-4" />
              {data.grade}
            </span>
          )}
          {data.subject && (
            <span className="px-3 py-1 rounded-full bg-emerald-50 text-brand-green text-sm font-medium">
              {data.subject}
            </span>
          )}
        </div>
        <h1 className="text-2xl font-bold text-brand-blue">{data.name}</h1>
        <dl className="mt-6 grid sm:grid-cols-2 gap-4 text-sm">
          {data.school && (
            <div>
              <dt className="text-slate-500 flex items-center gap-1">
                <BuildingLibraryIcon className="w-4 h-4" /> Школа
              </dt>
              <dd className="font-medium mt-1">{data.school}</dd>
            </div>
          )}
          {data.contact && (
            <div>
              <dt className="text-slate-500 flex items-center gap-1">
                <PhoneIcon className="w-4 h-4" /> Контакт ученика
              </dt>
              <dd className="font-medium mt-1">{data.contact}</dd>
            </div>
          )}
          {data.parent_contact && (
            <div>
              <dt className="text-slate-500 flex items-center gap-1">
                <PhoneIcon className="w-4 h-4" /> Родитель
              </dt>
              <dd className="font-medium mt-1">{data.parent_contact}</dd>
            </div>
          )}
        </dl>
        {data.notes && (
          <div className="mt-4 p-4 rounded-xl bg-slate-50 text-sm text-slate-600">
            <p className="text-xs font-medium text-slate-500 mb-1">Заметки</p>
            {data.notes}
          </div>
        )}
      </div>

      {token && (
        <StudentBoundariesPanel
          studentId={id}
          token={token}
          onApplied={loadStudent}
        />
      )}

      <h2 className="mt-10 text-lg font-semibold">История занятий и домашек</h2>
      <div className="mt-6 space-y-4">
        {lessons.length ? (
          lessons.map((l) => (
            <div
              key={l.id}
              className="p-5 rounded-2xl bg-white border border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div>
                <p className="font-medium">
                  {new Date(l.lesson_date).toLocaleDateString("ru-RU")}
                </p>
                <Link
                  href={`/lessons/${l.id}`}
                  className="text-sm text-brand-blue hover:underline mt-1 inline-block"
                >
                  Открыть урок →
                </Link>
              </div>
              {l.homework_id ? (
                <button
                  onClick={() => downloadPdf(l.homework_id!)}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-blue text-white text-sm hover:bg-blue-900"
                >
                  <ArrowDownTrayIcon className="w-4 h-4" />
                  Скачать PDF
                </button>
              ) : (
                <span className="text-sm text-slate-400">ДЗ не сгенерировано</span>
              )}
            </div>
          ))
        ) : !lessonsLoading ? (
          <p className="text-slate-500">Занятий пока нет</p>
        ) : null}
        {lessonsLoading && lessons.length === 0 && <LoadingSpinner label="Загрузка занятий..." />}
        {hasMoreLessons && (
          <button
            type="button"
            onClick={() => loadLessons(lessonsPage + 1, true)}
            disabled={lessonsLoading}
            className="w-full py-3 rounded-xl border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {lessonsLoading ? "Загрузка…" : "Показать ещё"}
          </button>
        )}
      </div>
    </div>
  );
}
