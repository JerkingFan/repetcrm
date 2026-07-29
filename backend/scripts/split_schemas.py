"""One-off: split app/schemas.py into app/schemas/ package."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
text = (ROOT / "app/schemas.py").read_text(encoding="utf-8")

HEADER = '''from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.password_policy import validate_password_strength
from app.schemas.constraints import *  # noqa: F403

'''

sections: dict[str, tuple[str, str | None]] = {
    "auth": ("# Auth", "# Students"),
    "students": ("# Students", "# Checklist"),
    "checklist": ("# Checklist", "# Lessons"),
    "lessons": ("# Lessons", "# Homework"),
    "homework": ("# Homework", "# Dashboard"),
    "dashboard": ("# Dashboard", "class BoardSnapshotOut"),
    "boards": ("class BoardSnapshotOut", "# Student portal"),
    "portal": ("# Student portal", "class ParentPortalLoginIn"),
    "parent_portal": ("class ParentPortalLoginIn", "class PortalPaymentIntentIn"),
    "packages": ("class PortalPaymentIntentIn", "# Public trial booking"),
    "booking": ("# Public trial booking", None),
}

base = ROOT / "app/schemas"
base.mkdir(exist_ok=True)

(base / "constraints.py").write_text(
    '''"""Shared field length limits aligned with SQLAlchemy models."""

NAME_MAX = 255
SUBJECT_MAX = 255
GRADE_MAX = 255
SCHOOL_MAX = 255
CONTACT_MAX = 255
PHONE_MAX = 64
EMAIL_MAX = 255
NOTES_MAX = 10000
MEETING_URL_MAX = 500
TOPIC_MAX = 500
SPECIAL_NOTES_MAX = 2000
BOUNDARY_REASON_MAX = 2000
BOARD_TITLE_MAX = 255
''',
    encoding="utf-8",
)

for name, (start, end) in sections.items():
    i = text.index(start)
    j = len(text) if end is None else text.index(end)
    body = text[i:j].rstrip() + "\n"
    if not body.startswith("class ") and not body.startswith("from "):
        body = "\n".join(body.splitlines()[1:]) + "\n"
    (base / f"{name}.py").write_text(HEADER + body, encoding="utf-8")

init_lines = ['"""Pydantic schemas — domain modules re-exported for stable imports."""', ""]
for name in sections:
    init_lines.append(f"from app.schemas.{name} import *  # noqa: F403")
init_lines.append("from app.schemas.constraints import *  # noqa: F403")
(base / "__init__.py").write_text("\n".join(init_lines) + "\n", encoding="utf-8")
print("Wrote", len(list(base.glob("*.py"))), "files")
