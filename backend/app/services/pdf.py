"""PDF: компиляция LaTeX (локально / latexonline.cc) или текстовый fallback."""

import logging
import os
import re
from datetime import date, datetime

from app.config import settings
from app.services.homework_output import (
    is_ai_garbage_latex,
    is_latex_document,
    is_repetitive_latex,
    needs_pdf_latex_rebuild,
)
from app.services.latex_compile import compile_tex_to_pdf
from app.services.latex_convert import (
    build_print_tex_document,
    latex_line_to_readable_plain,
    parse_homework_content,
)
from app.services.smart_homework import generate_smart_homework_latex

logger = logging.getLogger(__name__)


def ensure_media_dir():
    os.makedirs(settings.media_dir, exist_ok=True)


def homework_pdf_path(homework_id: int) -> str:
    return os.path.join(settings.media_dir, f"homework_{homework_id}.pdf")


def invalidate_homework_pdf(homework_id: int) -> None:
    cached = homework_pdf_path(homework_id)
    if os.path.isfile(cached):
        try:
            os.remove(cached)
        except OSError:
            pass


def homework_pdf_cache_fresh(cached: str, updated_at: datetime | None) -> bool:
    if not os.path.isfile(cached) or os.path.getsize(cached) <= 200:
        return False
    if updated_at is None:
        return True
    cache_mtime = datetime.utcfromtimestamp(os.path.getmtime(cached))
    return cache_mtime >= updated_at


def _font_paths() -> tuple[str, str]:
    import sys
    from pathlib import Path

    if sys.platform == "win32":
        win = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for regular, bold in [
            (win / "arial.ttf", win / "arialbd.ttf"),
            (win / "Arial.ttf", win / "Arialbd.ttf"),
        ]:
            if regular.is_file():
                return str(regular), str(bold) if bold.is_file() else str(regular)
    assets = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    regular = assets / "DejaVuSans.ttf"
    if regular.is_file():
        bold = assets / "DejaVuSans-Bold.ttf"
        return str(regular), str(bold) if bold.is_file() else str(regular)
    raise RuntimeError("Не найден шрифт с кириллицей (Arial / DejaVu)")


def _pdf_plain_fallback(path: str, lesson_date: date, content: str) -> None:
    from fpdf import FPDF

    sections = parse_homework_content(content)
    if not sections:
        raise ValueError("Нет содержимого для PDF")

    regular, bold = _font_paths()
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_font("Main", "", regular)
    pdf.add_font("Main", "B", bold)
    pdf.add_page()

    usable_w = pdf.w - pdf.l_margin - pdf.r_margin

    def writeln(text: str, size: int = 11, bold: bool = False, color=(30, 41, 59)):
        if not text.strip():
            return
        pdf.set_x(pdf.l_margin)
        pdf.set_font("Main", "B" if bold else "", size)
        pdf.set_text_color(*color)
        pdf.multi_cell(usable_w, 6, text)

    writeln("Домашнее задание", size=17, bold=True, color=(30, 58, 138))
    pdf.ln(2)
    writeln(f"Дата урока: {lesson_date.strftime('%d.%m.%Y')}", size=10, color=(100, 116, 139))
    pdf.ln(2)
    pdf.set_draw_color(30, 58, 138)
    pdf.set_line_width(0.4)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.ln(5)

    for section_title, lines in sections:
        if section_title:
            pdf.ln(2)
            writeln(section_title, size=12, bold=True, color=(16, 185, 129))
            pdf.ln(1)
        for line in lines:
            plain = latex_line_to_readable_plain(line)
            if not plain:
                continue
            prefix = "• " if not plain.startswith("•") else ""
            writeln(f"{prefix}{plain}")
            pdf.ln(1)

    pdf.ln(6)
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Main", size=8)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(usable_w, 5, "RepetCRM", align="C")

    if os.path.isfile(path):
        os.remove(path)
    pdf.output(path)
    logger.info("PDF (текстовый fallback): %s", path)


def generate_homework_pdf(
    homework_id: int,
    student_name: str,
    lesson_date: date,
    homework_text: str,
    *,
    subject: str = "",
    checklist: list[dict] | None = None,
    grade: str = "",
    homework_prefs: dict | None = None,
) -> str:
    ensure_media_dir()
    path = homework_pdf_path(homework_id)

    text = homework_text
    if checklist and (
        needs_pdf_latex_rebuild(text)
        or is_ai_garbage_latex(text)
        or is_repetitive_latex(text)
    ):
        text = generate_smart_homework_latex(
            student_name, subject, checklist, grade, homework_prefs=homework_prefs
        )
        logger.info("PDF: ДЗ пересобрано по чек-листу")

    try:
        from fpdf import FPDF  # noqa: F401
    except ImportError as e:
        raise RuntimeError(
            "Не установлен fpdf2. В backend: pip install -r requirements.txt"
        ) from e

    try:
        if is_latex_document(text) or re.search(r"\\begin\s*\{\s*task\s*\}", text, re.I):
            tex = build_print_tex_document(
                text,
                lesson_date,
                subject=subject or "предмету",
                student_name=student_name,
            )
            if compile_tex_to_pdf(tex, path):
                return path
            logger.warning("LaTeX compile не удался — текстовый PDF")

        _pdf_plain_fallback(path, lesson_date, text)
        if not os.path.isfile(path) or os.path.getsize(path) < 200:
            raise RuntimeError("PDF-файл не создан")
        return path
    except Exception as e:
        logger.exception("PDF failed")
        raise RuntimeError(f"Не удалось создать PDF: {e}") from e
