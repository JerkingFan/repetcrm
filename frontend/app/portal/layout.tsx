import type { Metadata, Viewport } from "next";
import { Manrope, Unbounded } from "next/font/google";

const display = Unbounded({
  subsets: ["latin", "cyrillic"],
  variable: "--font-portal-display",
  display: "swap",
});

const body = Manrope({
  subsets: ["latin", "cyrillic"],
  variable: "--font-portal-body",
  display: "swap",
});

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
  return <div className={`portal-root ${display.variable} ${body.variable}`}>{children}</div>;
}
