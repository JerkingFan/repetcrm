import re

LATEX_INLINE_RE = re.compile(r"(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)", re.DOTALL)
LATEX_DISPLAY_RE = re.compile(r"\$\$(.+?)\$\$", re.DOTALL)
LATEX_PAREN_RE = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
LATEX_BRACKET_RE = re.compile(r"\\\[(.*?)\\\]", re.DOTALL)
