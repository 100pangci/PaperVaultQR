import json
from pathlib import Path

BASE = Path("src/i18n/locales")

# 以 zh_cn 语义为准：按钮含义是“恢复默认（代码默认值）”
SET_DEFAULT_TEXTS = {
    "zh_cn": "恢复默认",
    "en_us": "Restore Defaults",
    "ja_jp": "デフォルトに戻す",
    "ko_kr": "기본값 복원",
    "ko_kp": "기본값 복구",
    "de_de": "Standardwerte wiederherstellen",
    "da_dk": "Gendan standardværdier",
    "es_es": "Restaurar valores predeterminados",
    "fr": "Restaurer les valeurs par défaut",
    "he_il": "שחזר ברירות מחדל",
    "hi_in": "डिफ़ॉल्ट पुनर्स्थापित करें",
    "it_it": "Ripristina predefiniti",
    "pt_br": "Restaurar padrões",
    "ru_ru": "Восстановить значения по умолчанию",
    "th_th": "คืนค่าเริ่มต้น",
    "tr": "Varsayılanları geri yükle",
    "ug_cn": "كۆڭۈلدىكى قىممەتنى ئەسلىگە كەلتۈر",
    "uk_ua": "Відновити типові значення",
    "vi_vn": "Khôi phục mặc định",
    "bo": "སོར་བཞག་སླར་གསོ",
}

REMOVE_KEYS = {"default_saved", "default_save_failed"}

for fp in BASE.glob("*.json"):
    code = fp.stem
    data = json.loads(fp.read_text(encoding="utf-8"))
    gui = data.setdefault("gui", {})

    if "set_default" in gui:
        gui["set_default"] = SET_DEFAULT_TEXTS.get(code, "Restore Defaults")

    for key in REMOVE_KEYS:
        gui.pop(key, None)

    fp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print("fixed locale keys and texts")
