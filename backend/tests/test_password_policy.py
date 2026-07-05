"""Password policy tests."""

import pytest

from app.password_policy import validate_password_strength


def test_accepts_strong_password():
    assert validate_password_strength("MySecurePass1") == "MySecurePass1"


def test_rejects_short_password():
    with pytest.raises(ValueError, match="10"):
        validate_password_strength("short1")


def test_rejects_common_password():
    with pytest.raises(ValueError, match="простой"):
        validate_password_strength("password1234")


def test_rejects_without_digit():
    with pytest.raises(ValueError, match="цифру"):
        validate_password_strength("onlylettershere")
