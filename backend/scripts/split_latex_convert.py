"""Split latex_convert into patterns + normalize + render modules."""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
text = (ROOT / "app/services/latex_convert.py").read_text(encoding="utf-8")

patterns_src = """import re

LATEX_INLINE_RE = re.compile(r"(?<!\\$)\\$(?!\\$)(.+?)(?<!\\$)\\$(?!\\$)", re.DOTALL)
LATEX_DISPLAY_RE = re.compile(r"\\$\\$(.+?)\\$\\$", re.DOTALL)
LATEX_PAREN_RE = re.compile(r"\\\\\\((.+?)\\\\\\)", re.DOTALL)
LATEX_BRACKET_RE = re.compile(r"\\\\\\[(.*?)\\\\\\]", re.DOTALL)
"""

i_render = text.index("def _latex_to_mathtext")
normalize_body = text[text.index("def clean_latex_task_text") : i_render]
render_body = text[i_render:]

base = ROOT / "app/services/latex"
base.mkdir(exist_ok=True)

(base / "patterns.py").write_text(patterns_src, encoding="utf-8")

normalize_header = '''"""LaTeX normalization, parsing, Python expression export."""
from __future__ import annotations

import re
from typing import Iterable

from app.services.latex.patterns import (
    LATEX_BRACKET_RE,
    LATEX_DISPLAY_RE,
    LATEX_INLINE_RE,
    LATEX_PAREN_RE,
)

'''
(base / "normalize.py").write_text(normalize_header + normalize_body, encoding="utf-8")

render_header = '''"""Math rendering and HTML/PDF output pipeline."""
from __future__ import annotations

import base64
import io
import re
from html import escape

from app.services.latex.normalize import *  # noqa: F403

'''
(base / "render.py").write_text(render_header + render_body, encoding="utf-8")

facade = '''"""
Конвертация LaTeX из домашних заданий (facade для стабильных импортов).
"""

from app.services.latex.normalize import (
    clean_latex_task_text,
    content_has_raw_latex_delimiters,
    extract_latex_expressions,
    is_latex_homework_raw,
    latex_to_python_expression,
    normalize_homework_latex_document,
    normalize_math_delimiters,
    parse_homework_content,
    parse_latex_homework,
)
from app.services.latex.render import (
    build_print_tex_document,
    build_python_script,
    homework_html_to_python_script,
    latex_document_to_html,
    latex_to_png_base64,
    line_has_math,
    line_to_plain_pdf_text,
    prepare_html_for_pdf,
    process_homework_html,
    render_mixed_line_png,
)
'''
(ROOT / "app/services/latex_convert.py").write_text(facade, encoding="utf-8")
(base / "__init__.py").write_text('"""LaTeX homework conversion package."""\n', encoding="utf-8")

# remove broken files from first attempt
for name in ("html.py", "python_export.py"):
    p = base / name
    if p.exists():
        p.unlink()
print("done")
