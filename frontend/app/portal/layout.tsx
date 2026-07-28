import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "Кабинет ученика · RepetCRM",
  description: "Задания, уроки и прогресс — в одном кабинете",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#0c1222",
};

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return <div className="portal-root">{children}</div>;
}
