"""Core 运行相关的语言与文案辅助。"""

from __future__ import annotations

import ctypes
import locale
import os

from . import available_locale_codes, normalize_lang

AUTO_LANGUAGE_VALUE = "auto"
CLI_LANGUAGE_CHOICES = ("auto", *available_locale_codes())


def _resolve_supported_locale(locale_name: str) -> str | None:
    candidate = (locale_name or "").strip().lower().replace("-", "_")
    if not candidate:
        return None

    for raw in (candidate, candidate.split(".", 1)[0]):
        normalized = normalize_lang(raw)
        if normalized in available_locale_codes():
            return normalized

        base = normalized.split("_", 1)[0]
        if base in available_locale_codes():
            return base

    return None


def detect_lang(explicit_lang: str | None = None) -> str:
    if explicit_lang and str(explicit_lang).strip().lower() != AUTO_LANGUAGE_VALUE:
        return _resolve_supported_locale(str(explicit_lang)) or normalize_lang(explicit_lang)

    if os.name == "nt":
        try:
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            lang_code = locale.windows_locale.get(lang_id & 0x3FF, "")
            resolved = _resolve_supported_locale(lang_code)
            if resolved:
                return resolved
        except Exception:
            pass

    try:
        loc = locale.getdefaultlocale()[0] or ""
        resolved = _resolve_supported_locale(loc)
        if resolved:
            return resolved
    except Exception:
        pass

    return "en_us"
