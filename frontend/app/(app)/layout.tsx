import AuthGuard from "@/components/AuthGuard";
import Sidebar from "@/components/Sidebar";
import WhatsNewModal from "@/components/WhatsNewModal";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="app-shell">
        <Sidebar />
        <WhatsNewModal />
        <main className="app-main">{children}</main>
      </div>
    </AuthGuard>
  );
}
