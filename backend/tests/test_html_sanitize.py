"""HTML sanitization for homework preview (XSS protection)."""

from app.services.html_utils import sanitize_homework_html, sanitize_homework_storage


def test_strips_script_tags():
    dirty = '<div>Hello<script>alert("xss")</script></div>'
    clean = sanitize_homework_html(dirty)
    assert "<script" not in clean.lower()
    assert "Hello" in clean


def test_strips_onclick_handlers():
    dirty = '<p onclick="alert(1)">Task</p>'
    clean = sanitize_homework_html(dirty)
    assert "onclick" not in clean.lower()
    assert "Task" in clean


def test_preserves_safe_formatting():
    dirty = '<div class="task"><strong>Задача 1</strong><p>x<sup>2</sup></p></div>'
    clean = sanitize_homework_html(dirty)
    assert "<strong>" in clean
    assert "Задача 1" in clean


def test_sanitize_storage_skips_latex():
    latex = r"\documentclass{article}\begin{document}test\end{document}"
    assert sanitize_homework_storage(latex) == latex


def test_sanitize_storage_cleans_html():
    dirty = "<div>ok<script>x</script></div>"
    clean = sanitize_homework_storage(dirty)
    assert "<script" not in clean.lower()
