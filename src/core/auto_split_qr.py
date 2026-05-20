import argparse
import base64
import locale
import math
import os
import tempfile
import ctypes

import segno
from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt

# ==============================================================================
#                               核心配置区域
# ==============================================================================
CHUNK_SIZE = 500       
QR_ERROR = 'M'         
QR_WIDTH_CM = 4.0
FONT_SIZE_LABEL = 10

COLS_PER_PAGE = 4
PAGE_MARGIN = 1.0
TARGET_ENCODING = "utf-8"
BASE64_TAG = "<<BASE64>>"
# ==============================================================================

MESSAGES = {
    "zh": {
        "missing_input": "❌ 找不到文件 '{input_file}'",
        "data_loaded_text": "📄 数据加载完毕 (UTF-8 文本模式)",
        "data_loaded_base64": "📄 数据加载完毕 (base64 兼容模式)",
        "original_chars": "   - 原始字符数: {total_chars}",
        "generated_count": "   - 生成数量: {total_chunks} 个二维码",
        "progress": "✅ 处理进度: {current} / {total}",
        "saved": "\n💾 成功生成打印文档: {output_doc}",
        "part_label": "Part {current} / {total}",
        "suffix": "_冷存储",
    },
    "en": {
        "missing_input": "❌ File not found: '{input_file}'",
        "data_loaded_text": "📄 Data loaded (UTF-8 text mode)",
        "data_loaded_base64": "📄 Data loaded (base64-compatible mode)",
        "original_chars": "   - Total characters: {total_chars}",
        "generated_count": "   - Generated: {total_chunks} QR codes",
        "progress": "✅ Progress: {current} / {total}",
        "saved": "\n💾 Print document generated successfully: {output_doc}",
        "part_label": "Part {current} / {total}",
        "suffix": "_ColdStorage",
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

def tr(lang: str, key: str, **kwargs) -> str:
    return MESSAGES[lang][key].format(**kwargs)

def _encode_input_data(raw_data: bytes) -> tuple[str, bool]:
    try:
        return raw_data.decode(TARGET_ENCODING), False
    except UnicodeDecodeError:
        return base64.b64encode(raw_data).decode("ascii"), True

def setup_page(doc):
    section = doc.sections[0]
    section.page_height = Cm(29.7)
    section.page_width = Cm(21.0)
    section.left_margin, section.right_margin = Cm(PAGE_MARGIN), Cm(PAGE_MARGIN)
    section.top_margin, section.bottom_margin = Cm(PAGE_MARGIN), Cm(PAGE_MARGIN)

def process_file(input_path: str, lang: str = "zh"):
    input_path = os.path.abspath(input_path)
    if not os.path.exists(input_path):
        return print(tr(lang, "missing_input", input_file=input_path))

    original_filename = os.path.basename(input_path)
    base_name, _ = os.path.splitext(input_path)
    output_doc = f"{base_name}{tr(lang, 'suffix')}.docx"

    with open(input_path, "rb") as f:
        raw_data = f.read()

    full_text, is_base64 = _encode_input_data(raw_data)
    total_chars = len(full_text)
    total_chunks = math.ceil(total_chars / CHUNK_SIZE)

    print("="*50)
    print(tr(lang, "data_loaded_base64" if is_base64 else "data_loaded_text"))
    print(tr(lang, "original_chars", total_chars=total_chars))
    print(tr(lang, "generated_count", total_chunks=total_chunks))
    print("="*50)

    doc = Document()
    setup_page(doc)

    # 移除文档默认的空段落，防止排版被顶偏
    for p in doc.paragraphs:
        p._element.getparent().remove(p._element)

    total_rows = math.ceil(total_chunks / COLS_PER_PAGE)
    
    # 🌟 修复空页的关键：使用唯一自适应大表格，让 Word 引擎自动进行跨页断行
    current_table = doc.add_table(rows=total_rows, cols=COLS_PER_PAGE)
    current_table.autofit = False

    with tempfile.TemporaryDirectory() as temp_dir:
        for i in range(total_chunks):
            idx = i + 1
            start = i * CHUNK_SIZE
            chunk_content = full_text[start : start + CHUNK_SIZE]

            if is_base64:
                if idx == 1:
                    payload = f"[{idx}/{total_chunks}]<<FILENAME:{original_filename}>>{BASE64_TAG}{chunk_content}"
                else:
                    payload = f"[{idx}/{total_chunks}]{chunk_content}"
            else:
                payload = f"[{idx}/{total_chunks}]{chunk_content}"
                # 🌟 在最后一个二维码末尾追加包含原文件名的隐藏标记
                if idx == total_chunks:
                    payload += f"<<FILENAME:{original_filename}>>"

            qr = segno.make(payload, error=QR_ERROR)
            img_path = os.path.join(temp_dir, f"qr_{idx}.png")
            qr.save(img_path, scale=10, border=1)

            row_idx = i // COLS_PER_PAGE
            col_idx = i % COLS_PER_PAGE
            cell = current_table.cell(row_idx, col_idx)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

            p_label = cell.paragraphs[0]
            p_label.alignment, p_label.paragraph_format.space_before, p_label.paragraph_format.space_after = WD_ALIGN_PARAGRAPH.CENTER, Pt(0), Pt(0)
            run_label = p_label.add_run(tr(lang, "part_label", current=idx, total=total_chunks))
            run_label.font.bold, run_label.font.size = True, Pt(FONT_SIZE_LABEL)

            p_img = cell.add_paragraph()
            p_img.alignment, p_img.paragraph_format.space_before, p_img.paragraph_format.space_after = WD_ALIGN_PARAGRAPH.CENTER, Pt(0), Pt(0)
            p_img.add_run().add_picture(img_path, width=Cm(QR_WIDTH_CM))

            print(tr(lang, "progress", current=idx, total=total_chunks))

        doc.save(output_doc)
        print(tr(lang, "saved", output_doc=output_doc))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--lang", choices=("auto", "zh", "en"), default="auto")
    parser.add_argument("target", nargs="?")
    args = parser.parse_args()

    lang = detect_lang(None if args.lang == "auto" else args.lang)
    if not args.target:
        return print(tr(lang, "missing_input", input_file="<No file provided>"))

    target_path = os.path.abspath(args.target)
    if os.path.isdir(target_path):
        try:
            from core import scanner_decoder
        except ImportError:
            import scanner_decoder
        scanner_decoder.decode_folder(target_path, lang=lang)
    else:
        process_file(target_path, lang=lang)

if __name__ == "__main__":
    main()
