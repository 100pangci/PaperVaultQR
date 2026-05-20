"""UI text helpers for the GUI layer."""

from __future__ import annotations

from . import available_locale_codes, get_locale_meta, get_texts, normalize_lang, tr

GUI_NAMESPACE = "gui"
PROJECT_URL = "https://github.com/100pangci/PaperVaultQR"
AUTO_LANGUAGE_VALUE = "auto"


def get_gui_texts(lang: str):
    return get_texts(GUI_NAMESPACE, lang)


def get_gui_text(lang: str, key: str, **kwargs):
    return tr(GUI_NAMESPACE, lang, key, **kwargs)


def build_language_options():
    options = [(AUTO_LANGUAGE_VALUE, AUTO_LANGUAGE_VALUE)]
    for code in available_locale_codes():
        display_name = get_locale_meta(code).get("display_name", code)
        options.append((code, f"{display_name} ({code})"))
    return options


def resolve_lang(selection: str | None) -> str:
    if selection == AUTO_LANGUAGE_VALUE:
        return normalize_lang(None)
    return normalize_lang(selection)
