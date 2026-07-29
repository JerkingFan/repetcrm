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
import { api, authFetch, ApiError, StudentRecord } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import LoadError from "@/components/LoadError";
import StudentBoundariesPanel from "@/components/StudentBoundariesPanel";
import StudentPortalPanel from "@/components/StudentPortalPanel";
import ParentPortalPanel from "@/components/ParentPortalPanel";
import TrialFollowupBanner from "@/components/TrialFollowupBanner";
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
  const [loadError, setLoadError] = useState("");
  const [studentLoading, setStudentLoading] = useState(true);
  const [lessons, setLessons] = useState<LessonHistoryItem[]>([]);
  const [lessonsPage, setLessonsPage] = useState(1);
  const [hasMoreLessons, setHasMoreLessons] = useState(false);
  const [lessonsLoading, setLessonsLoading] = useState(true);
  const [homework, setHomework] = useState<
    Awaited<ReturnType<typeof api.students.listHomework>>["items"]
  >([]);
  const [hwPage, setHwPage] = useState(1);
  const [hasMoreHw, setHasMoreHw] = useState(false);
  const [hwLoading, setHwLoading] = useState(true);
  const [trialFollowup, setTrialFollowup] = useState("");

  const loadStudent = useCallback(() => {
    setStudentLoading(true);
    setLoadError("");
    api.students
      .get<StudentRecord>(id)
      .then(setData)
      .catch((e) =>
        setLoadError(e instanceof ApiError ? e.message : "Не удалось загрузить ученика")
      )
      .finally(() => setStudentLoading(false));
  }, [id]);

  const loadLessons = useCallback(
    async (page: number, append: boolean) => {
      setLessonsLoading(true);
      try {
        const res = await api.students.listLessons(id, { page, page_size: 20 });
        setLessons((prev) => (append ? [...prev, ...res.items] : res.items));
        setHasMoreLessons(res.has_more);
        setLessonsPage(page);
      } finally {
        setLessonsLoading(false);
      }
    },
    [id]
  );

  const loadHomework = useCallback(
    async (page: number, append: boolean) => {
      setHwLoading(true);
      try {
        const res = await api.students.listHomework(id, { page, page_size: 20 });
        setHomework((prev) => (append ? [...prev, ...res.items] : res.items));
        setHasMoreHw(res.has_more);
        setHwPage(page);
      } finally {
        setHwLoading(false);
      }
    },
    [id]
  );

  useEffect(() => {
    loadStudent();
    loadLessons(1, false);
    loadHomework(1, false);
    api.students
      .trialFollowup(id)
      .then((f) => setTrialFollowup(f.show ? f.message : ""))
      .catch(() => setTrialFollowup(""));
  }, [loadStudent, loadLessons, loadHomework, id]);

  const downloadPdf = async (homeworkId: number) => {
    const tryFetchPdf = () => authFetch(api.homework.pdfUrl(homeworkId));

    let res = await tryFetchPdf();
    if (res.status === 202) {
      const started = (await res.json()) as { job_id: string };
      const polled = await pollJobUntilDone(started.job_id);
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

  if (studentLoading && !data) return <LoadingSpinner />;
  if (loadError && !data) return <LoadError message={loadError} onRetry={loadStudent} />;
  if (!data) return null;

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
        <h1 className="rc-page-title">{data.name}</h1>
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
          {data.parent_name && (
            <div>
              <dt className="text-slate-500">Имя родителя</dt>
              <dd className="font-medium mt-1">{data.parent_name}</dd>
            </div>
          )}
          {data.parent_email && (
            <div>
              <dt className="text-slate-500">Email родителя</dt>
              <dd className="font-medium mt-1">{data.parent_email}</dd>
            </div>
          )}
          {data.parent_phone && (
            <div>
              <dt className="text-slate-500 flex items-center gap-1">
                <PhoneIcon className="w-4 h-4" /> Телефон родителя
              </dt>
              <dd className="font-medium mt-1">{data.parent_phone}</dd>
            </div>
          )}
          {!data.parent_name && !data.parent_email && !data.parent_phone && data.parent_contact && (
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

      {trialFollowup && (
        <div className="mt-6">
          <TrialFollowupBanner message={trialFollowup} />
        </div>
      )}

      <StudentBoundariesPanel studentId={id} onApplied={loadStudent} />

      <StudentPortalPanel studentId={id} />

      <ParentPortalPanel studentId={id} />

      <h2 className="mt-10 text-lg font-semibold">Все домашние задания</h2>
      <p className="text-sm text-slate-500 mt-1">История ДЗ по ученику в одном месте</p>
      <div className="mt-4 space-y-3">
        {homework.length ? (
          homework.map((hw) => (
            <div
              key={hw.id}
              className="p-5 rounded-2xl bg-white border border-slate-100 flex flex-col sm:flex-row sm:items-start justify-between gap-4"
            >
              <div className="min-w-0 flex-1">
                <p className="font-medium">
                  {new Date(hw.lesson_date).toLocaleDateString("ru-RU")}
                </p>
                {hw.preview && (
                  <p className="text-sm text-slate-600 mt-2 line-clamp-2">{hw.preview}</p>
                )}
                <Link
                  href={`/lessons/${hw.lesson_id}`}
                  className="text-sm text-brand-blue hover:underline mt-2 inline-block"
                >
                  Открыть урок →
                </Link>
              </div>
              <button
                onClick={() => downloadPdf(hw.id)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-blue text-white text-sm hover:bg-brand-ink shrink-0"
              >
                <ArrowDownTrayIcon className="w-4 h-4" />
                PDF
              </button>
            </div>
          ))
        ) : !hwLoading ? (
          <p className="text-slate-500">Домашних заданий пока нет</p>
        ) : null}
        {hwLoading && homework.length === 0 && <LoadingSpinner label="Загрузка ДЗ..." />}
        {hasMoreHw && (
          <button
            type="button"
            onClick={() => loadHomework(hwPage + 1, true)}
            disabled={hwLoading}
            className="w-full py-3 rounded-xl border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {hwLoading ? "Загрузка…" : "Показать ещё ДЗ"}
          </button>
        )}
      </div>

      <h2 className="mt-10 text-lg font-semibold">История занятий</h2>
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
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-brand-blue text-white text-sm hover:bg-brand-ink"
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
