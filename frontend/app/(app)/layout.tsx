import AuthGuard from "@/components/AuthGuard";
import Sidebar from "@/components/Sidebar";
import WhatsNewModal from "@/components/WhatsNewModal";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <div className="min-h-screen flex">
        <Sidebar />
        <WhatsNewModal />
        <main className="flex-1 lg:ml-0 pt-16 lg:pt-0 p-4 lg:p-8 overflow-auto">
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}
