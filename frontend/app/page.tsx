import type { Metadata } from "next";
import LandingPage from "@/components/landing/LandingPage";

export const metadata: Metadata = {
  title: "RepetCRM — практика без хаоса",
  description:
    "CRM для репетиторов: занятия, оплаты и персональные домашки с AI в одном кабинете.",
  openGraph: {
    title: "RepetCRM — практика без хаоса",
    description:
      "Занятия, оплаты и персональные домашки с AI — без Excel и хаоса в чатах.",
    type: "website",
  },
};

export default function HomePage() {
  return <LandingPage />;
}
