import os
import glob
import re
import locale
import ctypes
from PIL import Image
from pyzbar.pyzbar import decode

MESSAGES = {
    "zh": {
        "missing_scan_dir": "❌ 找不到文件夹 '{scan_dir}'",
        "no_images": "❌ 文件夹 '{scan_dir}' 中没有找到图片。",
        "start": "🔍 开始解析扫描件...",
        "scanning": "👉 扫描图片: {filename}",
        "fragments": "   - 识别出 {count} 个碎片。",
        "scan_error": "   ⚠️ 识别错误: {error}",
        "no_qr": "❌ 扫描失败：未检测到有效二维码。建议使用300/600 DPI 灰度扫描。",
        "progress": "📊 进度：共需 {expected_total} 块，已收集 {collected} 块。",
        "missing": "❌ 缺少以下碎片，请检查重新扫描：{missing_chunks}",
        "saved": "\n🎉 完美还原！已保存至 '{output_file}'",
        "suffix": "_恢复",
    },
    "en": {
        "missing_scan_dir": "❌ Folder not found: '{scan_dir}'",
        "no_images": "❌ No images found in folder '{scan_dir}'.",
        "start": "🔍 Start decoding scanned pages...",
        "scanning": "👉 Scanning image: {filename}",
        "fragments": "   - Detected {count} fragment(s).",
        "scan_error": "   ⚠️ Decode error: {error}",
        "no_qr": "❌ Scan failed: no valid QR code detected. Try grayscale scans at 300/600 DPI.",
        "progress": "📊 Progress: {collected} / {expected_total} chunks collected.",
        "missing": "❌ Missing chunks: {missing_chunks}",
        "saved": "\n🎉 Reconstruction complete! Saved to '{output_file}'",
        "suffix": "_Recovered",
    },
}

def detect_lang(explicit_lang: str | None = None) -> str:
    if explicit_lang in {"zh", "en"}: return explicit_lang
    if os.name == "nt":
        try:
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            if (lang_id & 0x3FF) == 0x04: return "zh"
        except: pass
    try:
        import locale
        if "zh" in (locale.getdefaultlocale()[0] or "").lower(): return "zh"
    except: pass
    return "en"

def tr(lang, key, **kwargs):
    return MESSAGES[lang][key].format(**kwargs)

def decode_folder(scan_dir: str, lang: str = "zh"):
    scan_dir = os.path.abspath(scan_dir)
    if not os.path.exists(scan_dir):
        return print(tr(lang, "missing_scan_dir", scan_dir=scan_dir))

    image_files = glob.glob(os.path.join(scan_dir, "*.[pjJ][pnN][gG]"))
    if not image_files:
        return print(tr(lang, "no_images", scan_dir=scan_dir))

    parent_dir = os.path.dirname(scan_dir)
    folder_name = os.path.basename(scan_dir)

    chunks_data = {}
    expected_total = None

    print("="*50)
    print(tr(lang, "start"))

    pattern = re.compile(r"^\[(\d+)/(\d+)\]([\s\S]*)$")

    for img_path in image_files:
        print(tr(lang, "scanning", filename=os.path.basename(img_path)))
        try:
            with Image.open(img_path) as img:
                decoded_objects = decode(img)
            
            for obj in decoded_objects:
                payload = obj.data.decode("utf-8")
                match = pattern.match(payload)
                if match:
                    idx, total, data = int(match.group(1)), int(match.group(2)), match.group(3)
                    if expected_total is None: expected_total = total
                    chunks_data[idx] = data
                        
            print(tr(lang, "fragments", count=len(decoded_objects)))
        except Exception as e:
            print(tr(lang, "scan_error", error=e))

    print("="*50)
    if not expected_total:
        return print(tr(lang, "no_qr"))

    missing_chunks =[i for i in range(1, expected_total + 1) if i not in chunks_data]
    print(tr(lang, "progress", expected_total=expected_total, collected=len(chunks_data)))

    if missing_chunks:
        return print(tr(lang, "missing", missing_chunks=missing_chunks))

    # 完全拼接文本
    original_text = "".join([chunks_data[i] for i in range(1, expected_total + 1)])

    # 🌟 尝试通过正则寻找尾部附加的文件名标记
    filename_match = re.search(r"<<FILENAME:(.+?)>>$", original_text)
    if filename_match:
        original_filename = filename_match.group(1)
        # 将文本中属于文件名的标记去除，只保留真正的内容
        original_text = original_text[:filename_match.start()]
        
        name, ext = os.path.splitext(original_filename)
        output_file = os.path.join(parent_dir, f"{name}{tr(lang, 'suffix')}{ext}")
    else:
        # 兼容旧版本生成的二维码（没有内置文件名）
        output_file = os.path.join(parent_dir, f"{folder_name}{tr(lang, 'suffix')}.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(original_text)

    print(tr(lang, "saved", output_file=output_file))

if __name__ == "__main__":
    import sys
    lang = detect_lang()
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "scanned_pages"
    decode_folder(test_dir, lang=lang)