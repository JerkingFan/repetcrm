"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  PlusIcon,
  PencilIcon,
  TrashIcon,
  AcademicCapIcon,
  BuildingLibraryIcon,
  PhoneIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import { getToken } from "@/lib/auth";
import { api, ApiError, StudentListItem } from "@/lib/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import Alert from "@/components/Alert";
import BoundaryModeBadge from "@/components/BoundaryModeBadge";

const emptyForm = {
  name: "",
  subject: "",
  grade: "",
  school: "",
  contact: "",
  parent_contact: "",
  notes: "",
};

export default function StudentsPage() {
  const [students, setStudents] = useState<StudentListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [search, setSearch] = useState("");
  const [searchDebounced, setSearchDebounced] = useState("");
  const pageSize = 20;
  const [profile, setProfile] = useState<{ subjects: string[]; grade_levels: string[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modal, setModal] = useState<"create" | "edit" | null>(null);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [view, setView] = useState<"cards" | "table">("cards");

  /** Только то, что репетитор выбрал при онбординге / в настройках */
  const subjectOptions = profile?.subjects ?? [];
  const gradeOptions = profile?.grade_levels ?? [];

  const subjectOptionsForForm = [
    ...new Set([
      ...subjectOptions,
      ...(form.subject && !subjectOptions.includes(form.subject) ? [form.subject] : []),
    ]),
  ];
  const gradeOptionsForForm = [
    ...new Set([
      ...gradeOptions,
      ...(form.grade && !gradeOptions.includes(form.grade) ? [form.grade] : []),
    ]),
  ];

  const profileReady = subjectOptions.length > 0 && gradeOptions.length > 0;

  useEffect(() => {
    const t = window.setTimeout(() => {
      setSearchDebounced(search);
      setPage(1);
    }, 300);
    return () => window.clearTimeout(t);
  }, [search]);

  const load = useCallback(() => {
    const token = getToken();
    if (!token) return;
    setLoading(true);
    Promise.all([
      api.students.list(token, { q: searchDebounced || undefined, page, page_size: pageSize }),
      profile ? Promise.resolve(null) : api.me(token),
    ])
      .then(([listRes, me]) => {
        setStudents(listRes.items);
        setTotal(listRes.total);
        setHasMore(listRes.has_more);
        if (me) setProfile({ subjects: me.subjects, grade_levels: me.grade_levels });
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [searchDebounced, page, pageSize, profile]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    if (!profileReady) {
      setError("Сначала укажите предметы и классы в онбординге или в разделе «Настройки»");
      return;
    }
    setError("");
    setForm({
      ...emptyForm,
      subject: subjectOptions[0],
      grade: gradeOptions[0],
    });
    setEditId(null);
    setModal("create");
  };

  const openEdit = (s: StudentListItem) => {
    setForm({
      name: s.name,
      subject: s.subject,
      grade: s.grade,
      school: s.school,
      contact: s.contact,
      parent_contact: s.parent_contact,
      notes: s.notes,
    });
    setEditId(s.id);
    setModal("edit");
  };

  const save = async () => {
    if (!form.name.trim()) {
      setError("Укажите имя ученика");
      return;
    }
    if (!form.subject || !form.grade) {
      setError("Выберите предмет и класс из вашего профиля");
      return;
    }
    const token = getToken();
    if (!token) return;
    try {
      if (modal === "create") {
        await api.students.create(token, form);
      } else if (editId) {
        await api.students.update(token, editId, form);
      }
      setModal(null);
      setError("");
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка сохранения");
    }
  };

  const remove = async (id: number) => {
    if (!confirm("Удалить ученика и все связанные занятия?")) return;
    const token = getToken();
    if (!token) return;
    try {
      await api.students.delete(token, id);
      load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка удаления");
    }
  };

  if (loading) return <LoadingSpinner />;

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-brand-blue">Ученики</h1>
          <p className="text-slate-500 text-sm mt-1">
            {total} учеников · карточки с классом, школой и контактами
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <MagnifyingGlassIcon className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Поиск по имени…"
              className="pl-9 pr-3 py-2 rounded-xl border border-slate-200 text-sm w-48 sm:w-56"
            />
          </div>
          <div className="flex rounded-lg border border-slate-200 p-0.5 bg-white text-sm">
            <button
              type="button"
              onClick={() => setView("cards")}
              className={`px-3 py-1.5 rounded-md ${view === "cards" ? "bg-brand-blue text-white" : "text-slate-600"}`}
            >
              Карточки
            </button>
            <button
              type="button"
              onClick={() => setView("table")}
              className={`px-3 py-1.5 rounded-md ${view === "table" ? "bg-brand-blue text-white" : "text-slate-600"}`}
            >
              Таблица
            </button>
          </div>
          <button
            onClick={openCreate}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand-green text-white font-medium hover:bg-emerald-600"
          >
            <PlusIcon className="w-5 h-5" />
            Добавить
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4">
          <Alert message={error} onClose={() => setError("")} />
        </div>
      )}

      {view === "cards" ? (
        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {students.map((s) => (
            <div
              key={s.id}
              className="p-6 rounded-2xl bg-white border border-slate-100 shadow-sm hover:shadow-md transition flex flex-col"
            >
              <Link href={`/students/${s.id}`} className="block flex-1">
                <div className="flex flex-wrap gap-2 mb-3">
                  <BoundaryModeBadge mode={s.boundary_mode} />
                  {s.grade && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-brand-blue/10 text-brand-blue text-xs font-semibold">
                      <AcademicCapIcon className="w-3.5 h-3.5" />
                      {s.grade}
                    </span>
                  )}
                  {s.subject && (
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-brand-green text-xs font-medium">
                      {s.subject}
                    </span>
                  )}
                </div>
                <h3 className="font-bold text-lg text-brand-blue">{s.name}</h3>
                {s.school && (
                  <p className="text-sm text-slate-500 mt-2 flex items-center gap-1.5">
                    <BuildingLibraryIcon className="w-4 h-4 shrink-0" />
                    {s.school}
                  </p>
                )}
                <div className="mt-3 space-y-1 text-xs text-slate-500">
                  {s.contact && (
                    <p className="flex items-center gap-1.5">
                      <PhoneIcon className="w-3.5 h-3.5" />
                      Ученик: {s.contact}
                    </p>
                  )}
                  {s.parent_contact && (
                    <p className="flex items-center gap-1.5">
                      <PhoneIcon className="w-3.5 h-3.5" />
                      Родитель: {s.parent_contact}
                    </p>
                  )}
                </div>
                {s.notes && (
                  <p className="mt-3 text-xs text-slate-400 line-clamp-2 border-t border-slate-100 pt-2">
                    {s.notes}
                  </p>
                )}
              </Link>
              <div className="mt-4 flex gap-2 pt-4 border-t border-slate-50">
                <button
                  onClick={() => openEdit(s)}
                  className="p-2 rounded-lg hover:bg-slate-100 text-slate-600"
                  title="Редактировать"
                >
                  <PencilIcon className="w-4 h-4" />
                </button>
                <button
                  onClick={() => remove(s.id)}
                  className="p-2 rounded-lg hover:bg-red-50 text-red-500"
                  title="Удалить"
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-8 overflow-x-auto rounded-2xl bg-white border border-slate-100 shadow-sm">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Имя</th>
                <th className="px-4 py-3 font-medium">Класс</th>
                <th className="px-4 py-3 font-medium">Предмет</th>
                <th className="px-4 py-3 font-medium">Школа</th>
                <th className="px-4 py-3 font-medium">Контакты</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody>
              {students.map((s) => (
                <tr key={s.id} className="border-t border-slate-100 hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium">
                    <Link href={`/students/${s.id}`} className="text-brand-blue hover:underline">
                      {s.name}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{s.grade || "—"}</td>
                  <td className="px-4 py-3">{s.subject || "—"}</td>
                  <td className="px-4 py-3">{s.school || "—"}</td>
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {s.parent_contact && <div>Род.: {s.parent_contact}</div>}
                    {s.contact && <div>Учен.: {s.contact}</div>}
                    {!s.parent_contact && !s.contact && "—"}
                  </td>
                  <td className="px-4 py-3">
                    <button onClick={() => openEdit(s)} className="text-brand-blue text-xs hover:underline">
                      Изменить
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {students.length === 0 && !searchDebounced && (
        <p className="mt-12 text-center text-slate-500">Добавьте первого ученика</p>
      )}
      {students.length === 0 && searchDebounced && (
        <p className="mt-12 text-center text-slate-500">Никого не найдено по запросу «{searchDebounced}»</p>
      )}

      {total > pageSize && (
        <div className="mt-8 flex items-center justify-center gap-4">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            className="px-4 py-2 rounded-xl border text-sm disabled:opacity-40"
          >
            Назад
          </button>
          <span className="text-sm text-slate-500">
            Страница {page} · показано {students.length} из {total}
          </span>
          <button
            type="button"
            disabled={!hasMore}
            onClick={() => setPage((p) => p + 1)}
            className="px-4 py-2 rounded-xl border text-sm disabled:opacity-40"
          >
            Далее
          </button>
        </div>
      )}

      {modal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 overflow-y-auto">
          <div className="bg-white rounded-2xl p-6 w-full max-w-lg space-y-4 my-8">
            <h2 className="font-bold text-lg text-brand-blue">
              {modal === "create" ? "Новый ученик" : "Редактировать ученика"}
            </h2>
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-slate-500 mb-1">Имя *</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border"
                  placeholder="Анна Иванова"
                />
              </div>
              {profileReady ? (
                <>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Класс *</label>
                    <select
                      value={form.grade}
                      onChange={(e) => setForm({ ...form, grade: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white focus:border-brand-green focus:ring-2 focus:ring-brand-green/20 outline-none"
                      required
                    >
                      <option value="" disabled>
                        Выберите класс
                      </option>
                      {gradeOptionsForForm.map((g) => (
                        <option key={g} value={g}>
                          {g}
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-slate-400">Из вашего профиля репетитора</p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-500 mb-1">Предмет *</label>
                    <select
                      value={form.subject}
                      onChange={(e) => setForm({ ...form, subject: e.target.value })}
                      className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white focus:border-brand-green focus:ring-2 focus:ring-brand-green/20 outline-none"
                      required
                    >
                      <option value="" disabled>
                        Выберите предмет
                      </option>
                      {subjectOptionsForForm.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-slate-400">Из вашего профиля репетитора</p>
                  </div>
                </>
              ) : (
                <div className="sm:col-span-2 p-4 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-900">
                  <p>Вы не указали предметы и классы при настройке.</p>
                  <Link href="/settings" className="mt-2 inline-block font-medium text-brand-blue hover:underline">
                    Перейти в настройки →
                  </Link>
                </div>
              )}
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-slate-500 mb-1">Школа</label>
                <input
                  value={form.school}
                  onChange={(e) => setForm({ ...form, school: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border"
                  placeholder="Лицей № 12"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Контакт ученика</label>
                <input
                  value={form.contact}
                  onChange={(e) => setForm({ ...form, contact: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border"
                  placeholder="Telegram, телефон"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-500 mb-1">Контакт родителя</label>
                <input
                  value={form.parent_contact}
                  onChange={(e) => setForm({ ...form, parent_contact: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border"
                  placeholder="+7 ..."
                />
              </div>
              <div className="sm:col-span-2">
                <label className="block text-xs font-medium text-slate-500 mb-1">Заметки</label>
                <textarea
                  value={form.notes}
                  onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  className="w-full px-4 py-3 rounded-xl border h-20 text-sm"
                  placeholder="Цели, особенности, пробелы..."
                />
              </div>
            </div>
            <div className="flex gap-3 pt-2">
              <button
                onClick={save}
                className="flex-1 py-3 rounded-xl bg-brand-green text-white font-medium"
              >
                Сохранить
              </button>
              <button onClick={() => setModal(null)} className="flex-1 py-3 rounded-xl border">
                Отмена
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
