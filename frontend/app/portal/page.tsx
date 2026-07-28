"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import type { PortalTab } from "@/lib/portalUi";
import Alert from "@/components/Alert";
import LoadingSpinner from "@/components/LoadingSpinner";
import PortalBottomNav from "@/components/portal/PortalBottomNav";
import PortalHomework from "@/components/portal/PortalHomework";
import PortalShell from "@/components/portal/PortalShell";
import { PortalHome, PortalPay, PortalSchedule } from "@/components/portal/PortalSections";

function PortalContent() {
  const params = useSearchParams();
  const tokenFromUrl = params.get("token") || "";

  const [student, setStudent] = useState<Awaited<ReturnType<typeof api.portal.me>> | null>(null);
  const [lessons, setLessons] = useState<Awaited<ReturnType<typeof api.portal.lessons>>>([]);
  const [homework, setHomework] = useState<Awaited<ReturnType<typeof api.portal.homework>>>([]);
  const [tab, setTab] = useState<PortalTab>("home");
  const [selectedHw, setSelectedHw] = useState<number | null>(null);
  const [hwDetail, setHwDetail] = useState<Awaited<ReturnType<typeof api.portal.homeworkDetail>> | null>(
    null
  );
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [paying, setPaying] = useState(false);
  const [comment, setComment] = useState("");
  const [success, setSuccess] = useState("");
  const [payAmount, setPayAmount] = useState("40");

  const loadData = async () => {
    const me = await api.portal.me();
    setStudent(me);
    const [ls, hw] = await Promise.all([api.portal.lessons(), api.portal.homework()]);
    setLessons(ls);
    setHomework(hw);
  };

  useEffect(() => {
    (async () => {
      try {
        if (tokenFromUrl) {
          await api.portal.login(tokenFromUrl);
        }
        await loadData();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Не удалось войти");
      } finally {
        setLoading(false);
      }
    })();
  }, [tokenFromUrl]);

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

  const pay = async (provider: "card" | "erip") => {
    const amount = Number(payAmount);
    if (amount <= 0) return;
    setPaying(true);
    setError("");
    try {
      const r = await api.portal.createPaymentIntent(amount, provider);
      if (r.payment_url) window.location.href = r.payment_url;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка оплаты");
    } finally {
      setPaying(false);
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
    schedule: { title: "Расписание", subtitle: student.tutor_name ? `с ${student.tutor_name}` : undefined },
    pay: { title: "Оплата", subtitle: "Баланс и пополнение" },
  };

  return (
    <PortalShell title={titles[tab].title} subtitle={titles[tab].subtitle}>
      {error && <Alert message={error} onClose={() => setError("")} />}
      {success && <Alert type="success" message={success} onClose={() => setSuccess("")} />}

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
        <PortalSchedule lessons={lessons} calendarUrl={api.portal.calendarIcsUrl()} />
      )}

      {tab === "pay" && (
        <PortalPay
          balance={student.balance}
          amount={payAmount}
          onAmountChange={setPayAmount}
          onPay={pay}
          paying={paying}
        />
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
