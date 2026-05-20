"""Core 运行相关的语言与文案辅助。"""

from __future__ import annotations

import ctypes
import locale
import os

from . import normalize_lang

AUTO_LANGUAGE_VALUE = "auto"
CLI_LANGUAGE_CHOICES = ("auto", "zh", "en", "jp")


def detect_lang(explicit_lang: str | None = None) -> str:
    if explicit_lang and str(explicit_lang).strip().lower() != AUTO_LANGUAGE_VALUE:
        return normalize_lang(explicit_lang)

    if os.name == "nt":
        try:
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            locale_id = lang_id & 0x3FF
            if locale_id == 0x04:
                return "zh"
            if locale_id == 0x11:
                return "jp"
        except Exception:
            pass

    try:
        loc = (locale.getdefaultlocale()[0] or "").lower()
        if "zh" in loc:
            return "zh"
        if "ja" in loc or "jp" in loc:
            return "jp"
    except Exception:
        pass

    return "en"
