"""Компиляция LaTeX → PDF (локально или latexonline.cc, как Overleaf)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

PDFLATEX_PREAMBLE = r"""\documentclass[a4paper,12pt]{article}
\usepackage[T1,T2A]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[russian]{babel}
\usepackage{amsmath,amssymb}
\usepackage{geometry}
\geometry{top=2cm, bottom=2cm, left=2.5cm, right=2.5cm}
"""

# Для локального XeLaTeX (если установлен TeX)
XELATEX_PREAMBLE = r"""\documentclass[a4paper,12pt]{article}
\usepackage{fontspec}
\usepackage{polyglossia}
\setdefaultlanguage{russian}
\setmainfont{DejaVu Serif}
\usepackage{amsmath,amssymb}
\usepackage{geometry}
\geometry{top=2cm, bottom=2cm, left=2.5cm, right=2.5cm}
"""


def find_latex_engine() -> str | None:
    for engine in ("xelatex", "lualatex", "pdflatex"):
        if shutil.which(engine):
            return engine
    return None


def compile_tex_local(tex: str, out_path: str, *, timeout: int = 120) -> bool:
    engine = find_latex_engine()
    if not engine:
        return False

    with tempfile.TemporaryDirectory(prefix="repetcrm_tex_") as tmp:
        tex_path = Path(tmp) / "homework.tex"
        tex_path.write_text(tex, encoding="utf-8")
        cmd = [engine, "-interaction=nonstopmode", "-halt-on-error", "homework.tex"]
        try:
            proc = subprocess.run(
                cmd,
                cwd=tmp,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            built = Path(tmp) / "homework.pdf"
            if built.is_file() and built.stat().st_size > 400:
                if proc.returncode != 0:
                    subprocess.run(cmd, cwd=tmp, capture_output=True, timeout=timeout)
                if built.is_file() and built.stat().st_size > 400:
                    shutil.copy(built, out_path)
                    logger.info("PDF (локальный %s): %s", engine, out_path)
                    return True
            logger.warning("LaTeX local: %s", (proc.stderr or "")[-500:])
        except subprocess.TimeoutExpired:
            logger.warning("LaTeX local timeout")
        except Exception as e:
            logger.warning("LaTeX local error: %s", e)
    return False


def compile_tex_online(tex: str, out_path: str, *, timeout: float = 90.0) -> bool:
    """latexonline.cc — облачная компиляция (аналог Overleaf без API-ключа)."""
    if not settings.latex_online_compile:
        return False
    base = settings.latex_online_url.rstrip("/")
    # pdflatex + T2A/fontenc — кириллица на latexonline.cc
    url = f"{base}?command=pdflatex&text={quote(tex)}"
    if len(url) > 12000:
        logger.warning("LaTeX online: документ слишком длинный для URL")
        return False
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.get(url)
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                Path(out_path).write_bytes(r.content)
                logger.info("PDF (latexonline.cc): %s", out_path)
                return True
            logger.warning(
                "LaTeX online HTTP %s: %s",
                r.status_code,
                (r.text or "")[:300],
            )
    except Exception as e:
        logger.warning("LaTeX online error: %s", e)
    return False


def compile_tex_to_pdf(tex: str, out_path: str) -> bool:
    if compile_tex_online(tex, out_path):
        return True
    return compile_tex_local(tex, out_path)
