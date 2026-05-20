import json
import os
from functools import lru_cache

DEFAULT_LOCALE = "en_us"
LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

LANG_ALIASES = {
    "auto": DEFAULT_LOCALE,
    "en": "en_us",
    "en_us": "en_us",
    "en-us": "en_us",
    "zh": "zh_cn",
    "zh_cn": "zh_cn",
    "zh-cn": "zh_cn",
    "jp": "ja_jp",
    "ja": "ja_jp",
    "ja_jp": "ja_jp",
    "ja-jp": "ja_jp",
}


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LOCALE
    normalized = str(lang).strip().lower().replace("-", "_")
    return LANG_ALIASES.get(normalized, normalized)


def _locale_path(locale_code: str) -> str:
    return os.path.join(LOCALES_DIR, f"{locale_code}.json")


@lru_cache(maxsize=None)
def _load_locale_data(locale_code: str) -> dict:
    locale_code = normalize_lang(locale_code)
    locale_path = _locale_path(locale_code)

    if os.path.exists(locale_path):
        with open(locale_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return {}


def available_locale_codes() -> list[str]:
    if not os.path.isdir(LOCALES_DIR):
        return []
    codes = []
    for filename in os.listdir(LOCALES_DIR):
        if filename.lower().endswith(".json"):
            codes.append(normalize_lang(os.path.splitext(filename)[0]))
    return sorted(set(codes))


def get_locale_meta(lang: str) -> dict:
    return _load_locale_data(lang).get("meta", {})


def get_texts(namespace: str, lang: str, fallback_lang: str = DEFAULT_LOCALE) -> dict:
    lang = normalize_lang(lang)
    fallback_lang = normalize_lang(fallback_lang)

    data = _load_locale_data(lang)
    texts = data.get(namespace, {})
    if texts:
        return texts

    if fallback_lang != lang:
        fallback_data = _load_locale_data(fallback_lang)
        return fallback_data.get(namespace, {})

    return {}


def tr(namespace: str, lang: str, key: str, **kwargs) -> str:
    texts = get_texts(namespace, lang)
    template = texts.get(key)
    if template is None:
        template = get_texts(namespace, DEFAULT_LOCALE).get(key, key)
    return template.format(**kwargs)
