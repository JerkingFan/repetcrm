"""Password strength rules for registration."""

from __future__ import annotations

import re

_MIN_LENGTH = 10

_COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "password12",
        "password123",
        "password1234",
        "1234567890",
        "qwertyuiop",
        "repetcrm123",
    }
)


def validate_password_strength(password: str) -> str:
    """Return password if valid; raise ValueError with a user-facing message."""
    if len(password) < _MIN_LENGTH:
        raise ValueError(f"Пароль должен быть не короче {_MIN_LENGTH} символов")
    if password.strip() != password:
        raise ValueError("Пароль не должен начинаться или заканчиваться пробелом")
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        raise ValueError("Слишком простой пароль — выберите другой")
    if not re.search(r"[A-Za-zА-Яа-яЁё]", password):
        raise ValueError("Пароль должен содержать хотя бы одну букву")
    if not re.search(r"\d", password):
        raise ValueError("Пароль должен содержать хотя бы одну цифру")
    return password
