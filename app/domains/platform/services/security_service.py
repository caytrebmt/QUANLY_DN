# -*- coding: utf-8 -*-
"""Password strength validation shared across platform routes."""

import re


def validate_password_strength(password: str):
    """Return (is_valid, message)."""
    pwd = (password or "").strip()
    if len(pwd) < 8:
        return False, "Mật khẩu phải có ít nhất 8 ký tự."
    if not re.search(r"[A-Z]", pwd):
        return False, "Mật khẩu phải có ít nhất 1 chữ in hoa."
    if not re.search(r"[a-z]", pwd):
        return False, "Mật khẩu phải có ít nhất 1 chữ thường."
    if not re.search(r"\d", pwd):
        return False, "Mật khẩu phải có ít nhất 1 chữ số."
    if not re.search(r"[^A-Za-z0-9]", pwd):
        return False, "Mật khẩu phải có ít nhất 1 ký tự đặc biệt."
    return True, ""
