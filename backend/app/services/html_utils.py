import re


def strip_markdown_wrapper(text: str) -> str:
    text = text.strip()
    fenced = re.search(r"```(?:latex|tex)\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    text = re.sub(r"^```(?:html|latex|tex)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_latex_document(text: str) -> str:
    """Вырезает .tex из ответа модели (markdown, текст до/после документа)."""
    t = strip_markdown_wrapper(text)
    m = re.search(
        r"(\\documentclass[\s\S]*?\\end\s*\{\s*document\s*\})",
        t,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).strip()
    return t


def ensure_html_fragment(text: str) -> str:
    text = strip_markdown_wrapper(text)
    if not text.startswith("<"):
        text = f"<div>{text}</div>"
    return text
