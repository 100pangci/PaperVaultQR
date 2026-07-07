import os
import glob
import re
import base64
import sys
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from PIL import Image, ImageOps
from pyzbar.pyzbar import decode
from reedsolo import RSCodec

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.dirname(CURRENT_DIR)
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from i18n import tr as i18n_tr
from i18n.core_texts import detect_lang

BASE64_TAG = "<<BASE64>>"
RS_TAG = "<<RS:"


def tr(lang, key, **kwargs):
    return i18n_tr("scanner_decoder", lang, key, **kwargs)


def _build_output_file(parent_dir: str, folder_name: str, lang: str,
                       original_filename: str | None, is_base64: bool) -> str:
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


def _expand_bbox(bbox: tuple[int, int, int, int], img_w: int, img_h: int,
                 padding: int = 20) -> tuple[int, int, int, int]:
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


def _parse_payloads(decoded_objects) -> list[tuple[int, int, str | None, str]]:
    """
    解析QR码payload，支持两种格式：
    - 旧格式：[{idx}/{total}]{content}
    - 新格式：[{idx}/{total}][CRC32]{content}
    返回：[(idx, total, crc32_or_None, data)]
    """
    pattern_with_crc = re.compile(r"^\[(\d+)/(\d+)\]\[([0-9A-Fa-f]{8})\]([\s\S]*)$")
    pattern_without_crc = re.compile(r"^\[(\d+)/(\d+)\]([\s\S]*)$")
    parsed_chunks = []
    for obj in decoded_objects:
        payload = obj.data.decode("utf-8")

        match = pattern_with_crc.match(payload)
        if match:
            idx, total, crc32, data = int(match.group(1)), int(match.group(2)), match.group(3), match.group(4)
            parsed_chunks.append((idx, total, crc32, data))
            continue

        match = pattern_without_crc.match(payload)
        if match:
            idx, total, data = int(match.group(1)), int(match.group(2)), match.group(3)
            parsed_chunks.append((idx, total, None, data))

    return parsed_chunks


def _calculate_crc32(data: str) -> str:
    crc_value = zlib.crc32(data.encode("utf-8")) & 0xFFFFFFFF
    return format(crc_value, "08X")


def _verify_crc32(data: str, expected_crc32: str | None) -> bool:
    if expected_crc32 is None:
        return True
    return _calculate_crc32(data) == expected_crc32


def _parse_rs_meta(data: str) -> tuple[int, int] | None:
    """从payload数据中提取RS元数据：<<RS:original_count;redundancy_count>>"""
    match = re.search(rf'{re.escape(RS_TAG)}(\d+);(\d+)>>', data)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _strip_all_meta(data: str) -> str:
    """移除数据中的所有meta标记：FILENAME, RS, BASE64"""
    data = re.sub(r'<<FILENAME:[^>]+>>', '', data)
    data = re.sub(rf'{re.escape(RS_TAG)}\d+;\d+>>', '', data)
    data = data.replace(BASE64_TAG, '')
    return data


def _reed_solomon_decode(data_chunks: dict[int, str], redundancy_chunks: dict[int, str],
                         original_count: int, redundancy_count: int) -> dict[int, str]:
    """
    使用Reed-Solomon列解码恢复损坏/缺失的数据块。

    编码策略（列编码）：
    - 每列 = 所有块同一字节位置，RS编码生成冗余符号
    - 冗余块以base64存储（二进制→文本→QR）

    Returns:
        恢复后的完整数据块字典 {1..original_count: str}，失败返回空字典
    """
    if redundancy_count <= 0 or not redundancy_chunks:
        return {}

    # 解码冗余块：base64 -> bytes
    redun_bytes: dict[int, bytes] = {}
    for idx, b64_str in redundancy_chunks.items():
        try:
            redun_bytes[idx] = base64.b64decode(b64_str.encode("ascii"))
        except Exception:
            continue

    if not redun_bytes:
        return {}

    # 计算最大列长度
    max_len = 0
    for c in data_chunks.values():
        max_len = max(max_len, len(c.encode("utf-8")))
    for b in redun_bytes.values():
        max_len = max(max_len, len(b))
    if max_len == 0:
        return {}

    # 填充数据块到max_len
    data_bytes: dict[int, bytes] = {}
    for idx in range(1, original_count + 1):
        if idx in data_chunks:
            b = data_chunks[idx].encode("utf-8")
            data_bytes[idx] = b.ljust(max_len, b'\x00')

    # 填充冗余块
    for idx in redun_bytes:
        redun_bytes[idx] = redun_bytes[idx].ljust(max_len, b'\x00')

    total = original_count + redundancy_count
    rs = RSCodec(redundancy_count)

    recovered: dict[int, bytearray] = {}
    recovery_failed = False

    for col in range(max_len):
        column = bytearray(total)
        erase_pos = []

        for i in range(original_count):
            idx = i + 1
            if idx in data_bytes and col < len(data_bytes[idx]):
                column[i] = data_bytes[idx][col]
            else:
                erase_pos.append(i)

        for i in range(redundancy_count):
            idx = original_count + i + 1
            if idx in redun_bytes and col < len(redun_bytes[idx]):
                column[original_count + i] = redun_bytes[idx][col]
            else:
                erase_pos.append(original_count + i)

        if not erase_pos:
            # 列完整，直接复制
            for j in range(original_count):
                if j not in recovered:
                    recovered[j] = bytearray()
                recovered[j].append(column[j])
            continue

        try:
            decoded, _, _ = rs.decode(bytes(column), erase_pos=erase_pos)
            for j in range(original_count):
                if j not in recovered:
                    recovered[j] = bytearray()
                recovered[j].append(decoded[j])
        except Exception:
            recovery_failed = True
            continue

    if recovery_failed:
        return {}

    # 转换回字符串
    result: dict[int, str] = {}
    for j, barr in recovered.items():
        idx = j + 1
        result[idx] = bytes(barr).rstrip(b'\x00').decode("utf-8", errors="replace")

    return result


def _decode_image_file(img_path: str):
    with Image.open(img_path) as img:
        img = img.convert("RGB")
        img_w, img_h = img.size

        all_decoded = []
        seen_payloads = set()

        binary = _high_threshold_binary(img, threshold=220)

        for obj in decode(binary):
            payload = obj.data
            if payload not in seen_payloads:
                seen_payloads.add(payload)
                all_decoded.append(obj)

        bboxes = _find_dark_component_bboxes(
            binary, min_area=800, min_side=20,
            downsample_max_side=1200, max_components=80,
        )
        for bbox in bboxes:
            ex_bbox = _expand_bbox(bbox, img_w, img_h, padding=20)
            crop = binary.crop(ex_bbox)
            for obj in decode(crop):
                payload = obj.data
                if payload not in seen_payloads:
                    seen_payloads.add(payload)
                    all_decoded.append(obj)

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

    chunks_data: dict[int, tuple[str | None, str]] = {}  # {idx: (crc32, data)}
    expected_total = None
    has_crc32 = False
    rs_original_count: int | None = None
    rs_redundancy_count: int | None = None
    processed_files = 0

    print("=" * 50)
    print(tr(lang, "start"))

    cpu_count = max(1, os.cpu_count() or 1)
    max_workers = min(8, max(2, cpu_count // 2))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_path = {executor.submit(_decode_image_file, img_path): img_path
                          for img_path in image_files}

        for future in as_completed(future_to_path):
            img_path = future_to_path[future]
            print(tr(lang, "scanning", filename=os.path.basename(img_path)))
            try:
                decoded_objects, parsed_chunks = future.result()

                for idx, chunk_total, crc32, raw_data in parsed_chunks:
                    if expected_total is None:
                        expected_total = chunk_total
                    if crc32 is not None:
                        has_crc32 = True
                    # 提取RS元数据
                    if rs_original_count is None:
                        rs_meta = _parse_rs_meta(raw_data)
                        if rs_meta:
                            rs_original_count, rs_redundancy_count = rs_meta
                    chunks_data[idx] = (crc32, raw_data)

                print(tr(lang, "fragments", count=len(decoded_objects)))
            except Exception as e:
                print(tr(lang, "scan_error", error=e))
            finally:
                processed_files += 1
                display_total = expected_total if expected_total is not None else "?"
                print(f"__PROGRESS__::{len(chunks_data)}::{display_total}")
                print(tr(lang, "progress", total=display_total,
                           current=len(chunks_data)))

    print("=" * 50)
    if not expected_total:
        return print(tr(lang, "no_qr"))

    # --- 分离数据和冗余块 ---
    if rs_original_count is not None and rs_redundancy_count is not None:
        actual_data_count = rs_original_count
        actual_redundancy = rs_redundancy_count
        print(tr(lang, "redundancy_enabled",
                   redundancy_blocks=actual_redundancy,
                   max_recoverable=actual_redundancy))
    else:
        actual_data_count = expected_total
        actual_redundancy = 0
        if has_crc32:
            print(tr(lang, "redundancy_not_enabled"))

    # --- CRC32校验 ---
    missing_chunks = [i for i in range(1, expected_total + 1) if i not in chunks_data]
    crc_failed_chunks: list[int] = []
    valid_chunks = 0

    if has_crc32:
        for idx in list(chunks_data.keys()):
            crc32, data = chunks_data[idx]
            if _verify_crc32(data, crc32):
                valid_chunks += 1
            else:
                crc_failed_chunks.append(idx)

        print(tr(lang, "verification_summary",
                   valid_count=valid_chunks,
                   corrupted_count=len(crc_failed_chunks)))

        if crc_failed_chunks:
            print(tr(lang, "crc_check_failed", chunk_ids=crc_failed_chunks))
        else:
            print(tr(lang, "crc_check_passed"))

    if missing_chunks:
        print(tr(lang, "missing_chunks", missing_chunks=missing_chunks))

    total_corrupted = len(missing_chunks) + len(crc_failed_chunks)
    print(tr(lang, "total_corrupted", corrupted_count=total_corrupted))

    # --- Reed-Solomon纠错 ---
    if has_crc32 and total_corrupted > 0 and actual_redundancy > 0:
        if total_corrupted <= actual_redundancy:
            print(tr(lang, "rs_recovery_started"))

            # 构建有效数据块和冗余块字典
            valid_data: dict[int, str] = {}
            redundancy_data: dict[int, str] = {}

            for idx, (crc32, raw_data) in chunks_data.items():
                clean = _strip_all_meta(raw_data)
                if idx <= actual_data_count:
                    if idx not in crc_failed_chunks:
                        valid_data[idx] = clean
                else:
                    redundancy_data[idx] = clean

            recovered = _reed_solomon_decode(
                valid_data, redundancy_data,
                actual_data_count, actual_redundancy,
            )

            if recovered:
                recovered_count = 0
                for idx in range(1, actual_data_count + 1):
                    if idx in missing_chunks or idx in crc_failed_chunks:
                        if idx in recovered:
                            rec_data = recovered[idx]
                            new_crc = _calculate_crc32(rec_data)
                            chunks_data[idx] = (new_crc, rec_data)
                            recovered_count += 1

                if recovered_count > 0:
                    print(tr(lang, "rs_recovery_success",
                               recovered_count=recovered_count))

                    new_failed = []
                    for idx in range(1, actual_data_count + 1):
                        if idx in chunks_data:
                            c, d = chunks_data[idx]
                            if not _verify_crc32(d, c):
                                new_failed.append(idx)
                    if not new_failed:
                        print(tr(lang, "rs_verification_passed"))
                    else:
                        print(tr(lang, "rs_verification_failed",
                                   chunk_ids=new_failed))
                else:
                    print(tr(lang, "rs_recovery_failed",
                               max_recoverable=actual_redundancy))
            else:
                print(tr(lang, "rs_recovery_failed",
                           max_recoverable=actual_redundancy))
        else:
            print(tr(lang, "rs_recovery_failed",
                       max_recoverable=actual_redundancy))

    # --- 重新统计（只关心数据块，冗余块不参与最终校验）---
    verify_total = actual_data_count if rs_original_count is not None else expected_total
    missing_chunks = [i for i in range(1, verify_total + 1) if i not in chunks_data]
    crc_failed_chunks = []
    for idx in list(chunks_data.keys()):
        crc32, data = chunks_data[idx]
        if not _verify_crc32(data, crc32):
            crc_failed_chunks.append(idx)

    all_recovered = len(missing_chunks) == 0 and len(crc_failed_chunks) == 0
    if not all_recovered:
        unrecoverable = sorted(set(missing_chunks + crc_failed_chunks))
        print(tr(lang, "corrupted_blocks_tip",
                   unrecoverable_count=len(unrecoverable),
                   chunk_ids=unrecoverable))
        return

    # --- 重组数据 ---
    clean_chunks: dict[int, str] = {}
    is_base64 = any(BASE64_TAG in v for _, v in chunks_data.values())
    original_filename = None
    for _, v in chunks_data.values():
        fname_match = re.search(r'<<FILENAME:([^>]+)>>', v)
        if fname_match:
            original_filename = fname_match.group(1)
            break

    for idx in range(1, actual_data_count + 1):
        _, raw_data = chunks_data.get(idx, (None, ""))
        clean = _strip_all_meta(raw_data)
        clean_chunks[idx] = clean

    original_text = "".join(clean_chunks[i] for i in range(1, actual_data_count + 1))

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