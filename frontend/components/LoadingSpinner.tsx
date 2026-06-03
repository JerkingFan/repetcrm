export default function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 gap-4">
      <div className="animate-spin w-10 h-10 border-4 border-brand-blue border-t-transparent rounded-full" />
      {label && <p className="text-sm text-slate-500">{label}</p>}
    </div>
  );
}
