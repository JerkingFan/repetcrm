"""PDF export for parent monthly reports."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.schemas import ParentMonthlyReportOut
from app.services.pdf import _font_paths


def parent_report_pdf_path(student_id: int, month: str) -> str:
    safe = month.replace("-", "")
    return os.path.join(
        tempfile.gettempdir(),
        f"repetcrm-parent-report-{student_id}-{safe}.pdf",
    )


def generate_parent_report_pdf(report: ParentMonthlyReportOut, *, student_id: int) -> str:
    from fpdf import FPDF

    path = parent_report_pdf_path(student_id, report.month)
    regular, bold = _font_paths()
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_font("Main", "", regular)
    pdf.add_font("Main", "B", bold)
    pdf.add_page()

    usable_w = pdf.w - pdf.l_margin - pdf.r_margin

    def writeln(text: str, size: int = 11, bold: bool = False, color=(30, 41, 59)):
        if not str(text).strip():
            return
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Main", "B" if bold else "", size)
        pdf.set_text_color(*color)
        pdf.multi_cell(usable_w, 6, str(text))

    writeln("Отчёт за месяц", size=17, bold=True, color=(30, 58, 138))
    writeln(report.month_label.capitalize(), size=12, color=(100, 116, 139))
    pdf.ln(3)
    writeln(f"Ученик: {report.student_name}", bold=True)
    if report.subject or report.grade:
        writeln(f"{report.subject} · {report.grade}".strip(" ·"))
    writeln(f"Репетитор: {report.tutor_name}")
    pdf.ln(4)

    writeln("Занятия", size=13, bold=True, color=(16, 185, 129))
    writeln(
        f"Проведено: {report.lessons_conducted} из {report.lessons_total} запланированных"
    )
    for item in report.lessons:
        paid = "оплачено" if item.is_paid else "не оплачено"
        done = "проведён" if item.is_conducted else "запланирован"
        writeln(
            f"• {item.lesson_date.strftime('%d.%m.%Y')} {item.lesson_time} — {done}, {paid}"
        )
    pdf.ln(3)

    if report.topics_covered:
        writeln("Темы на занятиях", size=13, bold=True, color=(16, 185, 129))
        for topic in report.topics_covered:
            writeln(f"• {topic}")
        pdf.ln(3)

    if report.homework:
        writeln("Домашние задания", size=13, bold=True, color=(16, 185, 129))
        for hw in report.homework:
            writeln(f"• {hw.lesson_date.strftime('%d.%m.%Y')} — {hw.status_label}")
        pdf.ln(3)

    writeln("Оплаты", size=13, bold=True, color=(16, 185, 129))
    writeln(f"Поступило за месяц: {report.payments_total:.2f} Br")
    writeln(f"Текущий баланс: {report.balance:.2f} Br")
    pdf.ln(6)
    pdf.set_font("Main", size=8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(usable_w, 5, "RepetCRM", align="C")

    if os.path.isfile(path):
        os.remove(path)
    pdf.output(path)
    return path


def read_parent_report_pdf_bytes(path: str) -> bytes:
    return Path(path).read_bytes()
