"use client";

import { useRef, useState } from "react";
import {
  AI_VERDICT_LABEL,
  aiVerdictBoxClass,
  formatRuDate,
  submissionChipClass,
  SUBMISSION_STATUS_LABEL,
} from "@/lib/portalUi";
import { PortalCard, PortalEmpty } from "./PortalShell";

type HomeworkItem = {
  id: number;
  lesson_date: string;
  preview: string;
  has_submission: boolean;
  submission_status: string;
};

type Submission = {
  id: number;
  original_filename: string;
  submitted_at: string;
  status?: string;
  comment?: string;
  ai_review_status?: string;
  ai_verdict?: string;
  ai_score?: number | null;
  ai_feedback?: string;
  ai_review_error?: string;
};

type HomeworkDetail = {
  id: number;
  lesson_date: string;
  homework_text: string;
  preview_html?: string;
  submissions: Submission[];
};

export default function PortalHomework({
  items,
  selectedId,
  detail,
  comment,
  uploading,
  onSelect,
  onBack,
  onCommentChange,
  onSubmitFile,
}: {
  items: HomeworkItem[];
  selectedId: number | null;
  detail: HomeworkDetail | null;
  comment: string;
  uploading: boolean;
  onSelect: (id: number) => void;
  onBack: () => void;
  onCommentChange: (v: string) => void;
  onSubmitFile: (file: File) => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  const pending = items.filter(
    (h) => !h.has_submission || h.submission_status === "needs_revision"
  );
  const done = items.filter(
    (h) => h.has_submission && h.submission_status !== "needs_revision"
  );

  if (selectedId && detail) {
    const latest = detail.submissions[0];
    return (
      <>
        <button
          type="button"
          onClick={onBack}
          className="text-sm font-medium text-brand-blue inline-flex items-center gap-1"
        >
          ← К списку ДЗ
        </button>

        <PortalCard className="p-5 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                ДЗ · {formatRuDate(detail.lesson_date)}
              </h2>
              <p className="text-sm text-slate-500 mt-0.5">Прочитайте задание и сдайте фото решения</p>
            </div>
            {latest?.status && (
              <span
                className={`text-[11px] font-medium px-2 py-1 rounded-lg shrink-0 ${submissionChipClass(
                  latest.status
                )}`}
              >
                {SUBMISSION_STATUS_LABEL[latest.status] || latest.status}
              </span>
            )}
          </div>

          <div
            className="prose prose-sm max-w-none text-slate-700 max-h-64 overflow-y-auto p-4 bg-slate-50 rounded-xl border border-slate-100"
            dangerouslySetInnerHTML={{
              __html: detail.preview_html || detail.homework_text,
            }}
          />
        </PortalCard>

        <PortalCard className="p-5 space-y-4">
          <h3 className="font-semibold text-slate-800">Сдать решение</h3>
          <p className="text-sm text-slate-500 -mt-2">
            Лучше фото в хорошем свете. PDF тоже можно, но AI проверяет только фото.
          </p>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const f = e.dataTransfer.files?.[0];
              if (f) onSubmitFile(f);
            }}
            className={`rounded-2xl border-2 border-dashed p-6 text-center transition ${
              dragOver
                ? "border-brand-green bg-emerald-50"
                : "border-slate-200 bg-slate-50/80"
            }`}
          >
            <p className="text-sm font-medium text-slate-700">
              {uploading ? "Отправляем…" : "Перетащите файл сюда"}
            </p>
            <p className="text-xs text-slate-500 mt-1">JPG, PNG, WebP или PDF</p>
            <div className="mt-4 flex flex-wrap justify-center gap-2">
              <button
                type="button"
                disabled={uploading}
                onClick={() => cameraRef.current?.click()}
                className="px-4 py-2.5 rounded-xl bg-brand-blue text-white text-sm font-semibold disabled:opacity-50"
              >
                Сфотографировать
              </button>
              <button
                type="button"
                disabled={uploading}
                onClick={() => fileRef.current?.click()}
                className="px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-semibold text-slate-700 disabled:opacity-50"
              >
                Из галереи / файла
              </button>
            </div>
            <input
              ref={cameraRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onSubmitFile(f);
                e.target.value = "";
              }}
            />
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,image/jpeg,image/png,image/webp"
              className="hidden"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) onSubmitFile(f);
                e.target.value = "";
              }}
            />
          </div>

          <input
            type="text"
            placeholder="Комментарий к решению (необязательно)"
            value={comment}
            onChange={(e) => onCommentChange(e.target.value)}
            className="w-full px-4 py-3 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-brand-blue/20 focus:border-brand-blue"
          />

          {latest &&
            (latest.ai_review_status === "pending" || latest.ai_review_status === "running") && (
              <div className="p-4 rounded-xl border border-sky-200 bg-sky-50 text-sm text-sky-950">
                <p className="font-semibold">AI проверяет решение…</p>
                <p className="mt-1 text-sky-800/80">Обычно 10–30 секунд. Страница обновится сама.</p>
              </div>
            )}

          {latest?.ai_review_status === "done" && latest.ai_verdict && (
            <div
              className={`p-4 rounded-xl border text-sm ${aiVerdictBoxClass(latest.ai_verdict)}`}
            >
              <p className="font-bold text-base">
                {AI_VERDICT_LABEL[latest.ai_verdict] || latest.ai_verdict}
                {latest.ai_score != null ? ` · ${latest.ai_score}%` : ""}
              </p>
              {latest.ai_feedback && (
                <p className="mt-2 leading-relaxed whitespace-pre-wrap">{latest.ai_feedback}</p>
              )}
              <p className="mt-3 text-xs opacity-75">
                Предварительная оценка AI. Репетитор может подтвердить или изменить.
              </p>
            </div>
          )}

          {latest?.ai_review_status === "skipped" && latest.ai_feedback && (
            <p className="text-sm text-slate-500 bg-slate-50 rounded-xl p-3">{latest.ai_feedback}</p>
          )}

          {latest?.ai_review_status === "error" && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-sm text-amber-900">
              Автопроверка не сработала — репетитор проверит вручную.
              {latest.ai_review_error && (
                <p className="text-xs mt-1 opacity-70">{latest.ai_review_error}</p>
              )}
            </div>
          )}

          {detail.submissions.length > 0 && (
            <div className="pt-2 border-t border-slate-100">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">
                История отправок
              </p>
              <ul className="space-y-2">
                {detail.submissions.map((s) => (
                  <li
                    key={s.id}
                    className="flex justify-between gap-2 text-sm text-slate-600 bg-slate-50 rounded-lg px-3 py-2"
                  >
                    <span className="truncate font-medium">{s.original_filename}</span>
                    <span className="text-xs text-slate-400 shrink-0">
                      {new Date(s.submitted_at).toLocaleString("ru-RU", {
                        day: "numeric",
                        month: "short",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </PortalCard>
      </>
    );
  }

  const renderList = (list: HomeworkItem[], title: string) => (
    <PortalCard>
      <div className="px-5 pt-4 pb-2">
        <h3 className="font-semibold text-slate-800">{title}</h3>
      </div>
      {list.length === 0 ? (
        <PortalEmpty
          title={title === "Нужно сдать" ? "Всё сдано" : "Пока пусто"}
          hint={title === "Нужно сдать" ? "Новые задания появятся после урока" : undefined}
        />
      ) : (
        <ul className="divide-y divide-slate-100">
          {list.map((h) => (
            <li key={h.id}>
              <button
                type="button"
                onClick={() => onSelect(h.id)}
                className="w-full text-left px-5 py-4 hover:bg-slate-50 transition"
              >
                <div className="flex justify-between gap-2 items-center">
                  <span className="font-medium text-slate-800">{formatRuDate(h.lesson_date)}</span>
                  <span
                    className={`text-[11px] font-medium px-2 py-0.5 rounded-lg ${submissionChipClass(
                      h.submission_status
                    )}`}
                  >
                    {SUBMISSION_STATUS_LABEL[h.submission_status] ||
                      (h.has_submission ? "Сдано" : "Не сдано")}
                  </span>
                </div>
                {h.preview && (
                  <p className="text-xs text-slate-500 mt-1.5 line-clamp-2">{h.preview}</p>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </PortalCard>
  );

  return (
    <>
      {renderList(pending, "Нужно сдать")}
      {done.length > 0 && renderList(done, "Сданные")}
    </>
  );
}
