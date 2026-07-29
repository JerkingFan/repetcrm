"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  HomeIcon,
  UserGroupIcon,
  CalendarDaysIcon,
  PencilSquareIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon,
  Bars3Icon,
  XMarkIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  SparklesIcon,
  MagnifyingGlassIcon,
} from "@heroicons/react/24/outline";
import { useState } from "react";
import { api } from "@/lib/api";

const nav = [
  { href: "/dashboard", label: "Дашборд", icon: HomeIcon },
  { href: "/search", label: "Поиск", icon: MagnifyingGlassIcon },
  { href: "/students", label: "Ученики", icon: UserGroupIcon },
  { href: "/lessons", label: "Занятия", icon: CalendarDaysIcon },
  { href: "/prompts", label: "Промпты ДЗ", icon: SparklesIcon },
  { href: "/boards", label: "Доска", icon: PencilSquareIcon },
  { href: "/settings", label: "Настройки", icon: Cog6ToothIcon },
];

function SidebarNav({
  pathname,
  onNavigate,
  onLogout,
  collapsed,
  onToggleCollapsed,
}: {
  pathname: string;
  onNavigate: () => void;
  onLogout: () => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}) {
  return (
    <>
      <div className={`border-b border-white/10 ${collapsed ? "px-2 py-4" : "px-4 py-5"}`}>
        <div className="flex items-center justify-between gap-2">
          <Link
            href="/dashboard"
            className={`app-sidebar-brand ${collapsed ? "text-lg px-2" : "text-xl"}`}
            title="RepetCRM"
          >
            {collapsed ? (
              "R"
            ) : (
              <>
                Repet<span className="text-teal-300">CRM</span>
              </>
            )}
          </Link>
          <button
            type="button"
            className="hidden lg:inline-flex p-2 rounded-lg text-teal-100/70 hover:bg-white/10 hover:text-white"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "Развернуть меню" : "Свернуть меню"}
            title={collapsed ? "Развернуть" : "Свернуть"}
          >
            {collapsed ? <ChevronRightIcon className="w-5 h-5" /> : <ChevronLeftIcon className="w-5 h-5" />}
          </button>
        </div>
        {!collapsed && (
          <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-teal-200/50">
            Практика репетитора
          </p>
        )}
      </div>
      <nav className={`flex-1 space-y-1 ${collapsed ? "p-2" : "p-3"}`}>
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              title={label}
              className={`app-nav-link ${
                active ? "app-nav-link-active" : "app-nav-link-idle"
              } ${collapsed ? "justify-center px-3 py-3" : "px-3.5 py-2.5"}`}
            >
              <Icon className="w-5 h-5 shrink-0" />
              {!collapsed && label}
            </Link>
          );
        })}
      </nav>
      <div className={`border-t border-white/10 ${collapsed ? "p-2" : "p-3"}`}>
        <button
          onClick={onLogout}
          title="Выйти"
          className={`app-nav-link app-nav-link-idle w-full ${
            collapsed ? "justify-center px-3 py-3" : "px-3.5 py-2.5"
          }`}
        >
          <ArrowRightOnRectangleIcon className="w-5 h-5" />
          {!collapsed && "Выйти"}
        </button>
      </div>
    </>
  );
}

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => pathname.startsWith("/boards"));

  const logout = async () => {
    await api.logout();
    router.push("/login");
  };

  return (
    <>
      <button
        className="lg:hidden fixed top-4 left-4 z-50 p-2.5 rounded-xl bg-brand-ink text-white shadow-lift"
        onClick={() => setOpen(!open)}
        aria-label="Меню"
      >
        {open ? <XMarkIcon className="w-6 h-6" /> : <Bars3Icon className="w-6 h-6" />}
      </button>
      {open && (
        <div className="lg:hidden fixed inset-0 bg-brand-ink/50 backdrop-blur-sm z-40" onClick={() => setOpen(false)} />
      )}
      <aside
        className={`app-sidebar ${open ? "translate-x-0" : "-translate-x-full"} ${
          collapsed ? "w-16" : "w-64"
        }`}
      >
        <SidebarNav
          pathname={pathname}
          onNavigate={() => setOpen(false)}
          onLogout={logout}
          collapsed={collapsed}
          onToggleCollapsed={() => setCollapsed((v) => !v)}
        />
      </aside>
    </>
  );
}
