import Link from "next/link";

export default function PortalNotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-16 text-center">
      <h1 className="portal-title text-4xl">404</h1>
      <p className="mt-2 text-slate-600">Страница не найдена</p>
      <Link href="/portal" className="portal-btn-primary mt-6 inline-block">
        В кабинет
      </Link>
    </div>
  );
}
