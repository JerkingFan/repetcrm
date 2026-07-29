"use client";

export default function Skeleton({
  className = "",
}: {
  className?: string;
}) {
  return <div className={`animate-pulse rounded-xl bg-slate-200/80 dark:bg-slate-700/60 ${className}`} />;
}
