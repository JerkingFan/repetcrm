import Link from "next/link";

export default function AppNotFound() {
  return (
    <div className="max-w-lg mx-auto mt-16 space-y-4 text-center">
      <h1 className="text-4xl font-display font-bold text-slate-900">404</h1>
      <p className="text-slate-600">Страница не найдена</p>
      <Link href="/dashboard" className="rc-btn-primary inline-block">
        На главную
      </Link>
    </div>
  );
}
