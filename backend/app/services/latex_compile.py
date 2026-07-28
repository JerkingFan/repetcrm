"""Компиляция LaTeX → PDF (локально или latexonline.cc, как Overleaf)."""

from __future__ import annotations

import io
import logging
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from urllib.parse import quote, urlparse, urlunparse

import httpx

from app.config import settings
from app.services.circuit_breaker import CircuitBreaker, CircuitOpenError

logger = logging.getLogger(__name__)

_latex_circuit = CircuitBreaker(
    "latex_online",
    failure_threshold=settings.latex_circuit_failures,
    reset_timeout_sec=settings.latex_circuit_reset_sec,
)

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


def _latex_online_base() -> str:
    """https://latexonline.cc/compile → https://latexonline.cc"""
    raw = (settings.latex_online_url or "https://latexonline.cc/compile").rstrip("/")
    parsed = urlparse(raw)
    # если в URL уже /compile — берём origin
    path = parsed.path.rstrip("/")
    if path.endswith("/compile"):
        path = path[: -len("/compile")] or ""
    return urlunparse((parsed.scheme, parsed.netloc, path, "", "", "")).rstrip("/")


def _tex_tar_bytes(tex: str) -> bytes:
    payload = tex.encode("utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        info = tarfile.TarInfo(name="main.tex")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    return buf.getvalue()


def compile_tex_online(tex: str, out_path: str, *, timeout: float = 55.0) -> bool:
    """latexonline.cc — качественный PDF с формулами (POST tar, без лимита URL)."""
    if not settings.latex_online_compile:
        return False
    try:
        _latex_circuit.before_call()
    except CircuitOpenError:
        logger.warning("LaTeX online skipped — circuit open")
        return False

    base = _latex_online_base()
    # POST /data — длинные ДЗ; GET /compile?text= — только короткие
    data_url = f"{base}/data?target=main.tex&command=pdflatex"
    try:
        tar_bytes = _tex_tar_bytes(tex)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.post(
                data_url,
                files={"file": ("archive.tar", tar_bytes, "application/x-tar")},
            )
            if r.status_code == 200 and r.content[:4] == b"%PDF":
                Path(out_path).write_bytes(r.content)
                logger.info("PDF (latexonline POST): %s (%s bytes)", out_path, len(r.content))
                _latex_circuit.record_success()
                return True

            # fallback GET для коротких документов
            compile_url = f"{base}/compile?command=pdflatex&text={quote(tex)}"
            if len(compile_url) <= 12000:
                r2 = client.get(compile_url)
                if r2.status_code == 200 and r2.content[:4] == b"%PDF":
                    Path(out_path).write_bytes(r2.content)
                    logger.info("PDF (latexonline GET): %s", out_path)
                    _latex_circuit.record_success()
                    return True
                logger.warning(
                    "LaTeX online GET HTTP %s: %s",
                    r2.status_code,
                    (r2.text or "")[:300],
                )
            else:
                logger.warning(
                    "LaTeX online POST HTTP %s: %s",
                    r.status_code,
                    (r.text or "")[:300],
                )
            _latex_circuit.record_failure()
    except Exception as e:
        logger.warning("LaTeX online error: %s", e)
        _latex_circuit.record_failure()
    return False


def compile_tex_to_pdf(tex: str, out_path: str) -> bool:
    # Сначала облачный LaTeX (качество как раньше), потом локальный TeX.
    if compile_tex_online(tex, out_path, timeout=55.0):
        return True
    return compile_tex_local(tex, out_path, timeout=90)
