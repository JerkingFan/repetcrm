import type { Metadata } from "next";
import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "RepetCRM — CRM для репетиторов с AI-домашками",
  description:
    "Учёт занятий и оплат + AI-генерация домашних заданий за 1 минуту. Порядок вместо Excel и чатов.",
  openGraph: {
    title: "RepetCRM — практика без хаоса",
    description:
      "CRM для репетиторов: занятия, оплаты и персональные домашки с AI.",
    type: "website",
  },
};

export default function HomePage() {
  return <LandingPage />;
}
