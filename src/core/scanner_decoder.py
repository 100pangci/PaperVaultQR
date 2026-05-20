import os
import glob
import re
import base64
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from PIL import Image, ImageOps
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


def _high_threshold_binary(img: Image.Image, threshold: int = 220) -> Image.Image:
    gray = ImageOps.grayscale(img)
    return gray.point(lambda p: 0 if p < threshold else 255, mode="L")


def _expand_bbox(bbox: tuple[int, int, int, int], img_w: int, img_h: int, padding: int = 20) -> tuple[int, int, int, int]:
    left, top, right, bottom = bbox
    return (
        max(0, left - padding),
        max(0, top - padding),
        min(img_w, right + padding),
        min(img_h, bottom + padding),
    )


def _find_dark_component_bboxes(
    binary_img: Image.Image,
    min_area: int = 800,
    min_side: int = 20,
    downsample_max_side: int = 1200,
    max_components: int = 80,
) -> list[tuple[int, int, int, int]]:
    """
    在高阈值二值图中寻找黑色连通域，返回其 bbox 列表。
    约定：黑像素为 0，白像素为 255。
    """
    orig_w, orig_h = binary_img.size
    scale = 1.0
    if max(orig_w, orig_h) > downsample_max_side:
        scale = downsample_max_side / float(max(orig_w, orig_h))
        work_img = binary_img.resize(
            (max(1, int(orig_w * scale)), max(1, int(orig_h * scale))),
            Image.NEAREST,
        )
    else:
        work_img = binary_img

    arr = np.array(work_img, dtype=np.uint8)
    black = arr == 0
    h, w = black.shape
    visited = np.zeros((h, w), dtype=np.uint8)

    bboxes = []
    for y in range(h):
        for x in range(w):
            if not black[y, x] or visited[y, x]:
                continue

            stack = [(x, y)]
            visited[y, x] = 1
            min_x = max_x = x
            min_y = max_y = y
            area = 0

            while stack:
                cx, cy = stack.pop()
                area += 1
                if cx < min_x:
                    min_x = cx
                if cx > max_x:
                    max_x = cx
                if cy < min_y:
                    min_y = cy
                if cy > max_y:
                    max_y = cy

                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < w and 0 <= ny < h and black[ny, nx] and not visited[ny, nx]:
                        visited[ny, nx] = 1
                        stack.append((nx, ny))

            bw = max_x - min_x + 1
            bh = max_y - min_y + 1
            if area >= min_area and bw >= min_side and bh >= min_side:
                bboxes.append((min_x, min_y, max_x + 1, max_y + 1))
                if len(bboxes) >= max_components:
                    break
        if len(bboxes) >= max_components:
            break

    if scale != 1.0:
        inv = 1.0 / scale
        scaled = []
        for l, t, r, b in bboxes:
            scaled.append(
                (
                    max(0, int(l * inv)),
                    max(0, int(t * inv)),
                    min(orig_w, int(r * inv)),
                    min(orig_h, int(b * inv)),
                )
            )
        bboxes = scaled

    return bboxes


def _parse_payloads(decoded_objects) -> list[tuple[int, int, str]]:
    pattern = re.compile(r"^\[(\d+)/(\d+)\]([\s\S]*)$")
    parsed_chunks = []
    for obj in decoded_objects:
        payload = obj.data.decode("utf-8")
        match = pattern.match(payload)
        if match:
            idx, total, data = int(match.group(1)), int(match.group(2)), match.group(3)
            parsed_chunks.append((idx, total, data))
    return parsed_chunks


def _decode_image_file(img_path: str):
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        img_w, img_h = img.size

        all_decoded = []
        seen_payloads = set()

        # 1) 默认启用你的新算法：高阈值“全黑块”预处理
        binary = _high_threshold_binary(img, threshold=220)

        # 1.1 二值整图先解
        for obj in decode(binary):
            payload = obj.data
            if payload not in seen_payloads:
                seen_payloads.add(payload)
                all_decoded.append(obj)

        # 1.2 黑块连通域 -> 扩框20px -> 裁切解码（限量）
        bboxes = _find_dark_component_bboxes(
            binary,
            min_area=800,
            min_side=20,
            downsample_max_side=1200,
            max_components=80,
        )
        for bbox in bboxes:
            ex_bbox = _expand_bbox(bbox, img_w, img_h, padding=20)
            crop = binary.crop(ex_bbox)
            for obj in decode(crop):
                payload = obj.data
                if payload not in seen_payloads:
                    seen_payloads.add(payload)
                    all_decoded.append(obj)

        # 2) 原图轻量流程作为补充回退（提高召回）
        full_variants = [
            img,
            ImageOps.grayscale(img),
            ImageOps.autocontrast(ImageOps.grayscale(img)),
        ]
        for variant in full_variants:
            for obj in decode(variant):
                payload = obj.data
                if payload not in seen_payloads:
                    seen_payloads.add(payload)
                    all_decoded.append(obj)

    parsed_chunks = _parse_payloads(all_decoded)
    return all_decoded, parsed_chunks

def decode_folder(scan_dir: str, lang: str = "zh"):
    scan_dir = os.path.abspath(scan_dir)
    if not os.path.exists(scan_dir):
        return print(tr(lang, "missing_scan_dir", scan_dir=scan_dir))

    image_files = (
        glob.glob(os.path.join(scan_dir, "*.[pP][nN][gG]"))
        + glob.glob(os.path.join(scan_dir, "*.[jJ][pP][gG]"))
        + glob.glob(os.path.join(scan_dir, "*.[jJ][pP][eE][gG]"))
    )
    if not image_files:
        return print(tr(lang, "no_images", scan_dir=scan_dir))

    parent_dir = os.path.dirname(scan_dir)
    folder_name = os.path.basename(scan_dir)

    chunks_data = {}
    expected_total = None

    print("=" * 50)
    print(tr(lang, "start"))

    cpu_count = max(1, os.cpu_count() or 1)
    max_workers = min(8, max(2, cpu_count // 2))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(_decode_image_file, img_path): img_path for img_path in image_files}

        for future in as_completed(future_to_path):
            img_path = future_to_path[future]
            print(tr(lang, "scanning", filename=os.path.basename(img_path)))
            try:
                decoded_objects, parsed_chunks = future.result()

                for idx, total, data in parsed_chunks:
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
