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
} from "@heroicons/react/24/outline";
import { useState } from "react";
import { api } from "@/lib/api";

const nav = [
  { href: "/dashboard", label: "Дашборд", icon: HomeIcon },
  { href: "/students", label: "Ученики", icon: UserGroupIcon },
  { href: "/lessons", label: "Занятия", icon: CalendarDaysIcon },
  { href: "/boards", label: "Виртуальная доска", icon: PencilSquareIcon },
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
      <div className={`border-b border-slate-200 ${collapsed ? "px-2 py-4" : "px-4 py-6"}`}>
        <div className="flex items-center justify-between gap-2">
          <Link
            href="/dashboard"
            className={`font-bold text-brand-blue ${collapsed ? "text-lg px-2" : "text-xl"}`}
            title="RepetCRM"
          >
            {collapsed ? "R" : <>Repet<span className="text-brand-green">CRM</span></>}
          </Link>
          <button
            type="button"
            className="hidden lg:inline-flex p-2 rounded-lg hover:bg-slate-100 text-slate-600"
            onClick={onToggleCollapsed}
            aria-label={collapsed ? "Развернуть меню" : "Свернуть меню"}
            title={collapsed ? "Развернуть" : "Свернуть"}
          >
            {collapsed ? <ChevronRightIcon className="w-5 h-5" /> : <ChevronLeftIcon className="w-5 h-5" />}
          </button>
        </div>
      </div>
      <nav className={`flex-1 space-y-1 ${collapsed ? "p-2" : "p-4"}`}>
        {nav.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname.startsWith(href + "/");
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              title={label}
              className={`flex items-center gap-3 rounded-xl text-sm font-medium transition ${
                active
                  ? "bg-brand-blue text-white"
                  : "text-slate-600 hover:bg-slate-100"
              } ${collapsed ? "justify-center px-3 py-3" : "px-4 py-3"}`}
            >
              <Icon className="w-5 h-5" />
              {!collapsed && label}
            </Link>
          );
        })}
      </nav>
      <div className={`border-t border-slate-200 ${collapsed ? "p-2" : "p-4"}`}>
        <button
          onClick={onLogout}
          title="Выйти"
          className={`flex items-center gap-3 w-full rounded-xl text-sm text-slate-600 hover:bg-red-50 hover:text-red-600 transition ${
            collapsed ? "justify-center px-3 py-3" : "px-4 py-3"
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
        className="lg:hidden fixed top-4 left-4 z-50 p-2 rounded-lg bg-white shadow-md"
        onClick={() => setOpen(!open)}
        aria-label="Меню"
      >
        {open ? <XMarkIcon className="w-6 h-6" /> : <Bars3Icon className="w-6 h-6" />}
      </button>
      {open && (
        <div
          className="lg:hidden fixed inset-0 bg-black/40 z-40"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-40 bg-white border-r border-slate-200 flex flex-col transform transition-all duration-200 lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        } ${collapsed ? "w-16" : "w-64"}`}
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
