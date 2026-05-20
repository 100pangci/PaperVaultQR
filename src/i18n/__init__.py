import json
import sys
from functools import lru_cache
from pathlib import Path

DEFAULT_LOCALE = "en_us"

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


def _candidate_locales_dirs() -> list[Path]:
    package_dir = Path(__file__).resolve().parent
    candidates: list[Path] = []

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundle_root = Path(meipass)
        candidates.extend(
            [
                bundle_root / "i18n" / "locales",
                bundle_root / "src" / "i18n" / "locales",
                bundle_root / "locales",
            ]
        )

    candidates.extend(
        [
            package_dir / "locales",
            package_dir.parent / "locales",
        ]
    )

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique_candidates.append(candidate)
    return unique_candidates


def _resolve_locales_dir() -> Path:
    for candidate in _candidate_locales_dirs():
        if candidate.is_dir():
            return candidate
    return _candidate_locales_dirs()[0]


LOCALES_DIR = _resolve_locales_dir()


def _locale_path(locale_code: str) -> Path:
    return LOCALES_DIR / f"{locale_code}.json"


@lru_cache(maxsize=None)
def _load_locale_data(locale_code: str) -> dict:
    locale_code = normalize_lang(locale_code)
    locale_path = _locale_path(locale_code)

    if locale_path.exists():
        with locale_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    return {}


def available_locale_codes() -> list[str]:
    if not LOCALES_DIR.is_dir():
        return []

    codes = []
    for file_path in LOCALES_DIR.glob("*.json"):
        codes.append(normalize_lang(file_path.stem))
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
