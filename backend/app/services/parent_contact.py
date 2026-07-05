"""Sync legacy parent_contact with structured parent fields."""

from __future__ import annotations

from app.models import Student


def parse_legacy_parent_contact(raw: str) -> tuple[str, str]:
    """Return (email, phone) from a legacy single-line contact."""
    value = (raw or "").strip()
    if not value:
        return "", ""
    if "@" in value:
        return value, ""
    return "", value


def sync_parent_contact(student: Student) -> None:
    """Keep parent_contact populated for CSV export and old UI."""
    parts = [
        (student.parent_name or "").strip(),
        (student.parent_email or "").strip(),
        (student.parent_phone or "").strip(),
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for part in parts:
        if part and part not in seen:
            seen.add(part)
            unique.append(part)
    student.parent_contact = " · ".join(unique)
