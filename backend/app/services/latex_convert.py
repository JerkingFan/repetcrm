"""
Конвертация LaTeX из домашних заданий (facade для стабильных импортов).
"""

from app.services.latex.normalize import (
    build_python_script,
    clean_latex_task_text,
    content_has_raw_latex_delimiters,
    extract_latex_expressions,
    is_latex_homework_raw,
    latex_to_python_expression,
    normalize_homework_latex_document,
    normalize_math_delimiters,
    parse_latex_homework,
)
from app.services.latex.render import (
    build_print_tex_document,
    homework_html_to_python_script,
    latex_document_to_html,
    latex_line_to_readable_plain,
    latex_to_png_base64,
    line_has_math,
    line_to_plain_pdf_text,
    parse_homework_content,
    prepare_html_for_pdf,
    process_homework_html,
    render_mixed_line_png,
)
