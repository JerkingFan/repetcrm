"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { PortalTab } from "@/lib/portalUi";
import { formatRuDate } from "@/lib/portalUi";
import { formatLessonTime } from "@/lib/calendar";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";
import PortalBottomNav from "@/components/portal/PortalBottomNav";
import PortalHomework from "@/components/portal/PortalHomework";
import PortalProgress from "@/components/portal/PortalProgress";
import PortalShell from "@/components/portal/PortalShell";
import { PortalHome, PortalSchedule } from "@/components/portal/PortalSections";

function InstallHint({ onDismiss }: { onDismiss: () => void }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-semibold text-slate-800 text-sm">Сохранить на экран</p>
          <p className="text-xs text-slate-500 mt-0.5">
            В Safari/Chrome: «Поделиться» → «На экран „Домой“» — кабинет откроется как приложение.
          </p>
        </div>
        <button type="button" onClick={onDismiss} className="text-slate-400 text-sm shrink-0">
          Закрыть
        </button>
      </div>
    </div>
  );
}

function PortalContent() {
  const params = useSearchParams();
  const tokenFromUrl = params.get("token") || "";

  const [student, setStudent] = useState<Awaited<ReturnType<typeof api.portal.me>> | null>(null);
  const [lessons, setLessons] = useState<Awaited<ReturnType<typeof api.portal.lessons>>>([]);
  const [homework, setHomework] = useState<Awaited<ReturnType<typeof api.portal.homework>>>([]);
  const [progress, setProgress] = useState<Awaited<ReturnType<typeof api.portal.progress>> | null>(
    null
  );
  const [tab, setTab] = useState<PortalTab>("home");
  const [selectedHw, setSelectedHw] = useState<number | null>(null);
  const [hwDetail, setHwDetail] = useState<Awaited<ReturnType<typeof api.portal.homeworkDetail>> | null>(
    null
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [comment, setComment] = useState("");
  const [success, setSuccess] = useState("");
  const [showInstall, setShowInstall] = useState(false);
  const [rescheduleLesson, setRescheduleLesson] = useState<{
    id: number;
    lesson_date: string;
    lesson_time: string;
  } | null>(null);
  const [rescheduleMsg, setRescheduleMsg] = useState("");
  const [rescheduleDate, setRescheduleDate] = useState("");
  const [rescheduleTime, setRescheduleTime] = useState("");
  const [rescheduleSaving, setRescheduleSaving] = useState(false);

  const loadData = async () => {
    const me = await api.portal.me();
    setStudent(me);
    const [ls, hw, pr] = await Promise.all([
      api.portal.lessons(),
      api.portal.homework(),
      api.portal.progress().catch(() => null),
    ]);
    setLessons(ls);
    setHomework(hw);
    setProgress(pr);
  };

  useEffect(() => {
    (async () => {
      try {
        if (tokenFromUrl) {
          await api.portal.login(tokenFromUrl);
          if (typeof window !== "undefined") {
            window.history.replaceState({}, "", "/portal");
          }
        }
        await loadData();
        const dismissed = localStorage.getItem("portal_install_hint_v1");
        if (!dismissed) setShowInstall(true);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Не удалось войти");
      } finally {
        setLoading(false);
      }
    })();
  }, [tokenFromUrl]);

  useEffect(() => {
    if (tab !== "progress" || !student) return;
    api.portal.progress().then(setProgress).catch(() => setProgress(null));
  }, [tab, student]);

  useEffect(() => {
    if (!selectedHw) {
      setHwDetail(null);
      return;
    }
    api.portal.homeworkDetail(selectedHw).then(setHwDetail).catch(() => setHwDetail(null));
  }, [selectedHw]);

  useEffect(() => {
    if (!selectedHw || !hwDetail) return;
    const needsPoll = hwDetail.submissions.some(
      (s) => s.ai_review_status === "pending" || s.ai_review_status === "running"
    );
    if (!needsPoll) return;
    const timer = setInterval(() => {
      api.portal.homeworkDetail(selectedHw).then(setHwDetail).catch(() => {});
    }, 3000);
    return () => clearInterval(timer);
  }, [selectedHw, hwDetail]);

  const pendingCount = useMemo(
    () =>
      homework.filter(
        (h) => !h.has_submission || h.submission_status === "needs_revision"
      ).length,
    [homework]
  );

  const nextLesson = useMemo(() => {
    const upcoming = lessons.filter((l) => !l.is_conducted);
    return upcoming[0] || null;
  }, [lessons]);

  const pendingHomework = useMemo(
    () =>
      homework.filter(
        (h) => !h.has_submission || h.submission_status === "needs_revision"
      ),
    [homework]
  );

  const openHomework = (id: number) => {
    setSelectedHw(id);
    setTab("homework");
    setSuccess("");
  };

  const submitFile = async (file: File) => {
    if (!selectedHw) return;
    setUploading(true);
    setError("");
    setSuccess("");
    try {
      await api.portal.submitHomework(selectedHw, file, comment);
      setSuccess("Ответ отправлен! AI проверяет решение…");
      setComment("");
      await loadData();
      setHwDetail(await api.portal.homeworkDetail(selectedHw));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка загрузки");
    } finally {
      setUploading(false);
    }
  };

  const logout = async () => {
    await api.portal.logout();
    setStudent(null);
    setLessons([]);
    setHomework([]);
    setProgress(null);
  };

  const submitReschedule = async () => {
    if (!rescheduleLesson) return;
    setRescheduleSaving(true);
    setError("");
    try {
      await api.portal.requestReschedule({
        lesson_id: rescheduleLesson.id,
        message: rescheduleMsg,
        preferred_date: rescheduleDate || null,
        preferred_time: rescheduleTime,
      });
      setSuccess("Запрос на перенос отправлен репетитору");
      setRescheduleLesson(null);
      setRescheduleMsg("");
      setRescheduleDate("");
      setRescheduleTime("");
      await loadData();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось отправить запрос");
    } finally {
      setRescheduleSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <LoadingSpinner label="Вход в кабинет…" />
      </div>
    );
  }

  if (!student) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8 bg-[radial-gradient(ellipse_at_top,_#e8eefc_0%,_#f8fafc_50%)]">
        <div className="max-w-sm w-full text-center space-y-4 rounded-2xl border bg-white p-8 shadow-sm">
          <p className="text-[11px] font-semibold tracking-wide uppercase text-brand-blue/70">
            RepetCRM
          </p>
          <h1 className="text-2xl font-bold text-brand-blue">Кабинет ученика</h1>
          {error ? (
            <Alert message={error} />
          ) : (
            <p className="text-slate-500 text-sm">
              Откройте персональную ссылку от репетитора — вход без пароля.
            </p>
          )}
        </div>
      </div>
    );
  }

  const titles: Record<PortalTab, { title: string; subtitle?: string }> = {
    home: { title: "Главная", subtitle: student.subject || undefined },
    homework: {
      title: selectedHw ? "Задание" : "Домашние задания",
      subtitle: pendingCount ? `${pendingCount} ждут сдачи` : "Все сдано",
    },
    schedule: {
      title: "Расписание",
      subtitle: student.tutor_name ? `с ${student.tutor_name}` : undefined,
    },
    progress: { title: "Прогресс", subtitle: "темы и динамика" },
  };

  return (
    <PortalShell
      title={titles[tab].title}
      subtitle={titles[tab].subtitle}
      right={
        <button
          type="button"
          onClick={logout}
          className="text-xs font-semibold text-slate-500 hover:text-rose-600 px-2 py-1.5 rounded-lg border border-slate-200 bg-white shrink-0"
        >
          Выйти
        </button>
      }
    >
      {error && <Alert message={error} onClose={() => setError("")} />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess("")} />}

      {tab === "home" && showInstall && (
        <InstallHint
          onDismiss={() => {
            localStorage.setItem("portal_install_hint_v1", "1");
            setShowInstall(false);
          }}
        />
      )}

      {tab === "home" && (
        <PortalHome
          student={student}
          nextLesson={nextLesson}
          pendingHomework={pendingHomework}
          onOpenTab={setTab}
          onOpenHomework={openHomework}
        />
      )}

      {tab === "homework" && (
        <PortalHomework
          items={homework}
          selectedId={selectedHw}
          detail={hwDetail}
          comment={comment}
          uploading={uploading}
          onSelect={openHomework}
          onBack={() => {
            setSelectedHw(null);
            setHwDetail(null);
          }}
          onCommentChange={setComment}
          onSubmitFile={submitFile}
        />
      )}

      {tab === "schedule" && (
        <PortalSchedule
          lessons={lessons}
          calendarUrl={api.portal.calendarIcsUrl()}
          onRequestReschedule={(l) => setRescheduleLesson(l)}
        />
      )}

      {tab === "progress" && <PortalProgress data={progress} />}

      {rescheduleLesson && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-2xl w-full max-w-md p-5 space-y-4 shadow-xl">
            <h3 className="font-bold text-brand-blue text-lg">Запрос на перенос</h3>
            <p className="text-sm text-slate-600">
              Урок {formatRuDate(rescheduleLesson.lesson_date)} в{" "}
              {formatLessonTime(rescheduleLesson.lesson_time)}
            </p>
            <textarea
              value={rescheduleMsg}
              onChange={(e) => setRescheduleMsg(e.target.value)}
              placeholder="Почему нужно перенести?"
              className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-sm min-h-[80px]"
            />
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-500">Желаемая дата</label>
                <input
                  type="date"
                  value={rescheduleDate}
                  onChange={(e) => setRescheduleDate(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-xl border border-slate-200 text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">Время</label>
                <input
                  type="time"
                  value={rescheduleTime}
                  onChange={(e) => setRescheduleTime(e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-xl border border-slate-200 text-sm"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setRescheduleLesson(null)}
                className="flex-1 py-2.5 rounded-xl border border-slate-200 text-sm font-medium"
              >
                Отмена
              </button>
              <button
                type="button"
                disabled={rescheduleSaving}
                onClick={submitReschedule}
                className="flex-1 py-2.5 rounded-xl bg-brand-blue text-white text-sm font-semibold disabled:opacity-50"
              >
                {rescheduleSaving ? "…" : "Отправить"}
              </button>
            </div>
          </div>
        </div>
      )}

      <PortalBottomNav
        tab={tab}
        onChange={(t) => {
          setTab(t);
          if (t !== "homework") {
            setSelectedHw(null);
            setHwDetail(null);
          }
        }}
        homeworkBadge={pendingCount}
      />
    </PortalShell>
  );
}

export default function PortalPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <LoadingSpinner label="Загрузка…" />
        </div>
      }
    >
      <PortalContent />
    </Suspense>
  );
}
