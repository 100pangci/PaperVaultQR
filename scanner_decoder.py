import argparse
import glob
import locale
import os
import re

from PIL import Image
from pyzbar.pyzbar import decode

SCAN_DIR = "scanned_pages"
OUTPUT_FILE = "decoder.json"

MESSAGES = {
    "zh": {
        "missing_scan_dir": "❌ 请将扫描仪扫出的图片丢进新建的 '{scan_dir}' 文件夹中运行。",
        "no_images": "❌ 文件夹 '{scan_dir}' 中没有找到图片。",
        "start": "🔍 开始解析扫描件...",
        "scanning": "👉 扫描图片: {filename}",
        "fragments": "   - 识别出 {count} 个碎片。",
        "scan_error": "   ⚠️ 识别错误: {error}",
        "no_qr": "❌ 扫描失败：未检测到有效二维码。建议使用300/600 DPI 灰度扫描。",
        "progress": "📊 进度：共需 {expected_total} 块，已收集 {collected} 块。",
        "missing": "❌ 缺少以下碎片，请检查重新扫描：{missing_chunks}",
        "saved": "\n🎉 完美还原！已保存至 '{output_file}'",
    },
    "en": {
        "missing_scan_dir": "❌ Put the scanned images into the newly created '{scan_dir}' folder and run again.",
        "no_images": "❌ No images found in folder '{scan_dir}'.",
        "start": "🔍 Start decoding scanned pages...",
        "scanning": "👉 Scanning image: {filename}",
        "fragments": "   - Detected {count} fragment(s).",
        "scan_error": "   ⚠️ Decode error: {error}",
        "no_qr": "❌ Scan failed: no valid QR code detected. Try grayscale scans at 300/600 DPI.",
        "progress": "📊 Progress: {collected} / {expected_total} chunks collected.",
        "missing": "❌ Missing chunks: {missing_chunks}",
        "saved": "\n🎉 Reconstruction complete! Saved to '{output_file}'",
    },
}


def detect_lang(explicit_lang=None):
    if explicit_lang in {"zh", "en"}:
        return explicit_lang

    for env_key in ("APP_LANG", "LANGUAGE", "LC_ALL", "LANG"):
        value = os.environ.get(env_key, "").lower()
        if value.startswith("zh") or "zh_" in value or "zh-" in value:
            return "zh"
        if value.startswith("en") or "en_" in value or "en-" in value:
            return "en"

    try:
        locale_name = locale.getlocale()[0] or ""
    except (ValueError, TypeError):
        locale_name = ""

    return "zh" if "zh" in locale_name.lower() else "en"


def tr(lang, key, **kwargs):
    return MESSAGES[lang][key].format(**kwargs)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Decode QR chunks from scanned images and rebuild the original text."
    )
    parser.add_argument(
        "-l",
        "--lang",
        choices=("auto", "zh", "en"),
        default="auto",
        help="Language for console output.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    lang = detect_lang(None if args.lang == "auto" else args.lang)
    decode_folder(SCAN_DIR, lang=lang)


def decode_folder(scan_dir: str, lang: str = "zh", output_file: str = OUTPUT_FILE):
    """Decode QR images in `scan_dir` and write reconstructed text to `output_file`.
    This function is callable from other modules (e.g. when a user drags a folder)."""
    if not os.path.exists(scan_dir):
        os.makedirs(scan_dir)
        return print(tr(lang, "missing_scan_dir", scan_dir=scan_dir))

    image_files = glob.glob(os.path.join(scan_dir, "*.[pjJ][pnN][gG]"))
    if not image_files:
        return print(tr(lang, "no_images", scan_dir=scan_dir))

    chunks_data = {}
    expected_total = None

    print("=" * 50)
    print(tr(lang, "start"))

    # 正则表达式 ([\s\S]* 支持匹配可能包含的换行符)
    pattern = re.compile(r"^\[(\d+)/(\d+)\]([\s\S]*)$")

    for img_path in image_files:
        print(tr(lang, "scanning", filename=os.path.basename(img_path)))
        try:
            img = Image.open(img_path)
            decoded_objects = decode(img)

            for obj in decoded_objects:
                payload = obj.data.decode("utf-8")
                match = pattern.match(payload)
                if match:
                    idx, total, data = int(match.group(1)), int(match.group(2)), match.group(3)
                    if expected_total is None:
                        expected_total = total
                    chunks_data[idx] = data

            print(tr(lang, "fragments", count=len(decoded_objects)))
        except Exception as e:
            print(tr(lang, "scan_error", error=e))

    print("=" * 50)
    if not expected_total:
        return print(tr(lang, "no_qr"))

    missing_chunks = [i for i in range(1, expected_total + 1) if i not in chunks_data]
    print(tr(lang, "progress", expected_total=expected_total, collected=len(chunks_data)))

    if missing_chunks:
        return print(tr(lang, "missing", missing_chunks=missing_chunks))

    # 简单粗暴地按顺序拼接纯文本，没有任何花里胡哨的转换！
    original_text = "".join([chunks_data[i] for i in range(1, expected_total + 1)])

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(original_text)

    print(tr(lang, "saved", output_file=output_file))


if __name__ == "__main__":
    main()
