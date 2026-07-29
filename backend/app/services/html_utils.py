import re

import bleach

# Allowlist for homework HTML preview (LaTeX→HTML, AI output, tutor edits).
_HOMEWORK_ALLOWED_TAGS = frozenset(
    {
        "div",
        "p",
        "span",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "td",
        "th",
        "img",
        "sup",
        "sub",
        "strong",
        "em",
        "b",
        "i",
        "u",
        "br",
        "hr",
        "pre",
        "code",
        "blockquote",
        "a",
        "section",
        "article",
    }
)

_HOMEWORK_ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "*": ["class"],
    "img": ["src", "alt", "width", "height", "class"],
    "a": ["href", "title", "rel", "target", "class"],
    "td": ["colspan", "rowspan", "class"],
    "th": ["colspan", "rowspan", "class"],
    "div": ["class"],
    "span": ["class"],
    "p": ["class"],
}


def sanitize_homework_html(html: str) -> str:
    """Strip scripts, event handlers and dangerous tags from stored/preview HTML."""
    if not html or not html.strip():
        return html
    return bleach.clean(
        html,
        tags=_HOMEWORK_ALLOWED_TAGS,
        attributes=_HOMEWORK_ALLOWED_ATTRIBUTES,
        protocols=["http", "https", "data"],
        strip=True,
    )


def is_html_fragment(text: str) -> bool:
    return bool(text and text.lstrip().startswith("<"))


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
    return sanitize_homework_html(text)


def sanitize_homework_storage(text: str) -> str:
    """Sanitize HTML before persisting; leave LaTeX/plain text unchanged."""
    if is_html_fragment(text):
        return sanitize_homework_html(text)
    return text
