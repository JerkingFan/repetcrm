"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AcademicCapIcon,
  SparklesIcon,
  UserGroupIcon,
  CalendarDaysIcon,
  ChevronRightIcon,
  ChevronLeftIcon,
} from "@heroicons/react/24/outline";
import { getToken } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";
import ChipSelect from "@/components/ChipSelect";
import { SUBJECT_PRESETS, GRADE_PRESETS, TEACHING_FORMATS } from "@/lib/constants";
import Alert from "@/components/Alert";

const TOUR_STEPS = [
  {
    icon: UserGroupIcon,
    title: "Ученики",
    text: "Ведите карточки с классом, школой и контактами родителей — всё под рукой.",
  },
  {
    icon: CalendarDaysIcon,
    title: "Занятия и оплаты",
    text: "Журнал уроков с чек-листом тем и учётом оплат — без потерь в Excel.",
  },
  {
    icon: SparklesIcon,
    title: "AI-домашки",
    text: "После урока нейросеть за минуту соберёт персональное ДЗ в PDF.",
  },
];

export default function OnboardingWizard() {
  const router = useRouter();
  const [retake, setRetake] = useState(false);
  const [step, setStep] = useState(0);
  const [name, setName] = useState("");
  const [subjects, setSubjects] = useState<string[]>([]);
  const [gradeLevels, setGradeLevels] = useState<string[]>([]);
  const [teachingFormat, setTeachingFormat] = useState("both");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [checking, setChecking] = useState(true);

  const totalSteps = 5;

  useEffect(() => {
    setRetake(new URLSearchParams(window.location.search).get("retake") === "1");
  }, []);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    api
      .me(token)
      .then((u) => {
        if (u.onboarding_completed && !retake) {
          router.replace("/dashboard");
          return;
        }
        setName(u.name);
        if (u.subjects?.length) setSubjects(u.subjects);
        if (u.grade_levels?.length) setGradeLevels(u.grade_levels);
        if (u.teaching_format) setTeachingFormat(u.teaching_format);
      })
      .catch(() => router.replace("/login"))
      .finally(() => setChecking(false));
  }, [router, retake]);

  const next = () => {
    setError("");
    if (step === 1 && subjects.length === 0) {
      setError("Выберите хотя бы один предмет");
      return;
    }
    if (step === 2 && gradeLevels.length === 0) {
      setError("Выберите хотя бы один класс или уровень");
      return;
    }
    setStep((s) => Math.min(s + 1, totalSteps - 1));
  };

  const back = () => setStep((s) => Math.max(s - 1, 0));

  const finish = async () => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      await api.completeOnboarding(token, {
        subjects,
        grade_levels: gradeLevels,
        teaching_format: teachingFormat,
      });
      router.push("/dashboard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось сохранить");
    } finally {
      setLoading(false);
    }
  };

  if (checking) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-10 h-10 border-4 border-brand-blue border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-emerald-50 flex flex-col">
      <header className="px-6 py-4 flex items-center justify-between max-w-3xl mx-auto w-full">
        <span className="font-bold text-brand-blue text-xl">
          Repet<span className="text-brand-green">CRM</span>
        </span>
        <span className="text-sm text-slate-500">
          Шаг {step + 1} из {totalSteps}
        </span>
      </header>

      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-2xl bg-white rounded-3xl shadow-xl border border-slate-100 p-8 lg:p-10">
          <div className="h-2 rounded-full bg-slate-100 overflow-hidden mb-8">
            <div
              className="h-full bg-gradient-to-r from-brand-blue to-brand-green transition-all duration-300"
              style={{ width: `${((step + 1) / totalSteps) * 100}%` }}
            />
          </div>

          {error && (
            <div className="mb-6">
              <Alert message={error} onClose={() => setError("")} />
            </div>
          )}

          {step === 0 && (
            <div className="text-center">
              <div className="mx-auto w-16 h-16 rounded-2xl bg-brand-blue/10 flex items-center justify-center">
                <AcademicCapIcon className="w-9 h-9 text-brand-blue" />
              </div>
              <h1 className="mt-6 text-2xl font-bold text-brand-blue">
                Добро пожаловать{name ? `, ${name}` : ""}!
              </h1>
              <p className="mt-4 text-slate-600 leading-relaxed">
                Короткий обзорный тур займёт 2 минуты. Мы спросим, какие предметы и классы вы ведёте —
                так CRM подстроится под вашу практику.
              </p>
              <ul className="mt-8 text-left space-y-3 text-sm text-slate-600">
                <li className="flex gap-2">
                  <span className="text-brand-green font-bold">1.</span>
                  Предметы (можно несколько)
                </li>
                <li className="flex gap-2">
                  <span className="text-brand-green font-bold">2.</span>
                  Классы и уровни учеников
                </li>
                <li className="flex gap-2">
                  <span className="text-brand-green font-bold">3.</span>
                  Формат занятий и обзор возможностей
                </li>
              </ul>
            </div>
          )}

          {step === 1 && (
            <div>
              <h2 className="text-xl font-bold text-brand-blue">Какие предметы вы ведёте?</h2>
              <p className="mt-2 text-sm text-slate-500">Можно выбрать несколько или добавить свой</p>
              <div className="mt-6">
                <ChipSelect
                  label=""
                  presets={SUBJECT_PRESETS}
                  selected={subjects}
                  onChange={setSubjects}
                  customPlaceholder="Например: Логопедика"
                />
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-xl font-bold text-brand-blue">С какими классами работаете?</h2>
              <p className="mt-2 text-sm text-slate-500">
                Отметьте все подходящие уровни — при добавлении ученика класс подставится из списка
              </p>
              <div className="mt-6">
                <ChipSelect
                  label=""
                  presets={GRADE_PRESETS}
                  selected={gradeLevels}
                  onChange={setGradeLevels}
                  customPlaceholder="Например: Подготовка к ЦТ"
                />
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 className="text-xl font-bold text-brand-blue">Формат занятий</h2>
              <p className="mt-2 text-sm text-slate-500">Как вы обычно проводите уроки?</p>
              <div className="mt-6 grid gap-3">
                {TEACHING_FORMATS.map((f) => (
                  <label
                    key={f.id}
                    className={`flex items-center gap-4 p-4 rounded-xl border-2 cursor-pointer transition ${
                      teachingFormat === f.id
                        ? "border-brand-green bg-emerald-50"
                        : "border-slate-200 hover:border-slate-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name="format"
                      value={f.id}
                      checked={teachingFormat === f.id}
                      onChange={() => setTeachingFormat(f.id)}
                      className="w-4 h-4 text-brand-green"
                    />
                    <span className="font-medium">{f.label}</span>
                  </label>
                ))}
              </div>
            </div>
          )}

          {step === 4 && (
            <div>
              <h2 className="text-xl font-bold text-brand-blue text-center">Что умеет RepetCRM</h2>
              <p className="mt-2 text-sm text-slate-500 text-center">Краткий обзор перед стартом</p>
              <div className="mt-8 space-y-4">
                {TOUR_STEPS.map(({ icon: Icon, title, text }) => (
                  <div
                    key={title}
                    className="flex gap-4 p-4 rounded-xl bg-slate-50 border border-slate-100"
                  >
                    <div className="w-12 h-12 rounded-xl bg-brand-blue/10 flex items-center justify-center shrink-0">
                      <Icon className="w-6 h-6 text-brand-blue" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-brand-blue">{title}</h3>
                      <p className="text-sm text-slate-600 mt-1">{text}</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="mt-6 text-center text-sm text-slate-500">
                Профиль можно изменить позже в разделе «Настройки»
              </p>
            </div>
          )}

          <div className="mt-10 flex justify-between gap-4">
            <button
              type="button"
              onClick={back}
              disabled={step === 0}
              className="inline-flex items-center gap-1 px-5 py-2.5 rounded-xl border text-sm font-medium disabled:opacity-40"
            >
              <ChevronLeftIcon className="w-4 h-4" />
              Назад
            </button>
            {step < totalSteps - 1 ? (
              <button
                type="button"
                onClick={next}
                className="inline-flex items-center gap-1 px-6 py-2.5 rounded-xl bg-brand-blue text-white text-sm font-semibold hover:bg-blue-900"
              >
                Далее
                <ChevronRightIcon className="w-4 h-4" />
              </button>
            ) : (
              <button
                type="button"
                onClick={finish}
                disabled={loading}
                className="inline-flex items-center gap-1 px-6 py-2.5 rounded-xl bg-brand-green text-white text-sm font-semibold hover:bg-emerald-600 disabled:opacity-60"
              >
                {loading ? "Сохранение..." : "Начать работу"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
