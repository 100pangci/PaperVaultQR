import os
import glob
import re
import base64
import sys
from PIL import Image
from pyzbar.pyzbar import decode

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from i18n import tr as i18n_tr
from i18n.core_texts import detect_lang

BASE64_TAG = "<<BASE64>>"


def tr(lang, key, **kwargs):
    return i18n_tr("scanner_decoder", lang, key, **kwargs)


def _build_output_file(parent_dir: str, folder_name: str, lang: str, original_filename: str | None, is_base64: bool) -> str:
    suffix = tr(lang, "suffix")
    if original_filename:
        original_filename = os.path.basename(original_filename)
        name, ext = os.path.splitext(original_filename)
        if is_base64 and not ext:
            ext = ".bin"
        elif not is_base64 and not ext:
            ext = ".txt"
        return os.path.join(parent_dir, f"{name}{suffix}{ext}")
    return os.path.join(parent_dir, f"{folder_name}{suffix}{'.bin' if is_base64 else '.txt'}")


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

    print("=" * 50)
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

    original_text = "".join([chunks_data[i] for i in range(1, expected_total + 1)])

    original_filename = None
    is_base64 = False

    header_match = re.match(r"^<<FILENAME:(.+?)>>" + re.escape(BASE64_TAG), original_text)
    if header_match:
        original_filename = header_match.group(1)
        original_text = original_text[header_match.end():]
        is_base64 = True
    else:
        filename_match = re.search(r"<<FILENAME:(.+?)>>$", original_text)
        if filename_match:
            original_filename = filename_match.group(1)
            original_text = original_text[:filename_match.start()]

    output_file = _build_output_file(parent_dir, folder_name, lang, original_filename, is_base64)

    if is_base64:
        try:
            decoded_bytes = base64.b64decode(original_text.encode("ascii"), validate=True)
        except Exception as e:
            return print(tr(lang, "scan_error", error=e))
        with open(output_file, "wb") as f:
            f.write(decoded_bytes)
    else:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(original_text)

    print(tr(lang, "saved", output_file=output_file))


if __name__ == "__main__":
    import sys

    lang = detect_lang()
    test_dir = sys.argv[1] if len(sys.argv) > 1 else "scanned_pages"
    decode_folder(test_dir, lang=lang)
