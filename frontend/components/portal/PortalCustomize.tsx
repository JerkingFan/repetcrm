"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { api, ApiError } from "@/lib/api";
import { PortalCard } from "./PortalShell";
import { PORTAL_AVATARS, PORTAL_THEMES, avatarLabel, themeLabel } from "@/lib/portalTheme";

type Student = {
  portal_nickname?: string;
  portal_theme?: string;
  portal_avatar?: string;
};

export default function PortalCustomize({
  student,
  onSaved,
}: {
  student: Student;
  onSaved: (s: Awaited<ReturnType<typeof api.portal.customize>>) => void;
}) {
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [nickname, setNickname] = useState(student.portal_nickname || "");
  const [theme, setTheme] = useState(student.portal_theme || "ocean");
  const [avatar, setAvatar] = useState(student.portal_avatar || "rocket");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;
    setNickname(student.portal_nickname || "");
    setTheme(student.portal_theme || "ocean");
    setAvatar(student.portal_avatar || "rocket");
    setMsg("");
  }, [open, student.portal_nickname, student.portal_theme, student.portal_avatar]);

  const save = async () => {
    setBusy(true);
    setMsg("");
    try {
      const updated = await api.portal.customize({
        portal_nickname: nickname.trim(),
        portal_theme: theme,
        portal_avatar: avatar,
      });
      onSaved(updated);
      setMsg("Сохранено");
      setTimeout(() => setOpen(false), 600);
    } catch (e) {
      setMsg(e instanceof ApiError ? e.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  };

  const modal =
    open && mounted
      ? createPortal(
          <div className="fixed inset-0 z-[210] flex items-end sm:items-center justify-center bg-black/40 p-4">
            <PortalCard className="w-full max-w-md p-5 space-y-4 shadow-xl max-h-[90vh] overflow-y-auto">
              <div className="flex justify-between items-start gap-2">
                <div>
                  <h3 className="font-bold text-brand-blue text-lg">Свой кабинет</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Ник, аватар и тема оформления</p>
                </div>
                <button type="button" onClick={() => setOpen(false)} className="text-slate-400 text-sm">
                  Закрыть
                </button>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-500">Никнейм</label>
                <input
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  maxLength={64}
                  placeholder="Как тебя звать в кабинете"
                  className="mt-1 w-full px-3 py-2.5 rounded-xl border text-sm"
                />
              </div>

              <div>
                <p className="text-xs font-medium text-slate-500 mb-2">Аватар</p>
                <div className="grid grid-cols-4 gap-2">
                  {PORTAL_AVATARS.map((a) => (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => setAvatar(a.id)}
                      className={`rounded-xl border px-2 py-2.5 text-center text-lg transition ${
                        avatar === a.id
                          ? "border-brand-blue bg-brand-blue/10 ring-2 ring-brand-blue/30"
                          : "border-slate-200 bg-white"
                      }`}
                      title={avatarLabel(a.id)}
                    >
                      {a.emoji}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs font-medium text-slate-500 mb-2">Тема</p>
                <div className="grid grid-cols-1 gap-2">
                  {PORTAL_THEMES.map((t) => (
                    <button
                      key={t.id}
                      type="button"
                      onClick={() => setTheme(t.id)}
                      className={`flex items-center gap-3 rounded-xl border px-3 py-2.5 text-left transition ${
                        theme === t.id
                          ? "border-brand-blue ring-2 ring-brand-blue/25"
                          : "border-slate-200"
                      }`}
                    >
                      <span className="w-10 h-10 rounded-lg shrink-0" style={{ background: t.swatch }} />
                      <span className="text-sm font-medium text-slate-800">{themeLabel(t.id)}</span>
                    </button>
                  ))}
                </div>
              </div>

              {msg && <p className="text-xs text-slate-500">{msg}</p>}

              <button
                type="button"
                disabled={busy}
                onClick={save}
                className="w-full py-3 rounded-xl bg-brand-blue text-white text-sm font-semibold disabled:opacity-50"
              >
                {busy ? "…" : "Сохранить"}
              </button>
            </PortalCard>
          </div>,
          document.body
        )
      : null;

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="text-xs font-semibold px-2.5 py-1.5 rounded-xl border transition hover:bg-white/90"
        style={{
          color: "var(--portal-accent)",
          borderColor: "var(--portal-card-border)",
          background: "var(--portal-card)",
        }}
      >
        Оформить
      </button>
      {modal}
    </>
  );
}
