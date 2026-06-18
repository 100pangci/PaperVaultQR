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
        
        # 先尝试新格式（带CRC32）
        match = pattern_with_crc.match(payload)
        if match:
            idx, total, crc32, data = int(match.group(1)), int(match.group(2)), match.group(3), match.group(4)
            parsed_chunks.append((idx, total, crc32, data))
            continue
        
        # 再尝试旧格式（不带CRC32）
        match = pattern_without_crc.match(payload)
        if match:
            idx, total, data = int(match.group(1)), int(match.group(2)), match.group(3)
            parsed_chunks.append((idx, total, None, data))
    
    return parsed_chunks


def _calculate_crc32(data: str) -> str:
    """计算字符串的CRC32校验和，返回8字符的16进制字符串"""
    crc_value = zlib.crc32(data.encode("utf-8")) & 0xFFFFFFFF
    return format(crc_value, "08X")


def _verify_crc32(data: str, expected_crc32: str | None) -> bool:
    """验证数据的CRC32校验和"""
    if expected_crc32 is None:
        return True  # 没有CRC32，跳过校验
    calculated_crc32 = _calculate_crc32(data)
    return calculated_crc32 == expected_crc32


def _reed_solomon_decode(chunks: dict[int, str], redundancy_blocks: int, original_count: int) -> dict[int, str]:
    """使用Reed-Solomon解码恢复损坏的数据块"""
    if redundancy_blocks <= 0:
        return chunks
    
    # 找出缺失的块
    missing_indices = [i for i in range(1, original_count + redundancy_blocks + 1) if i not in chunks]
    if not missing_indices:
        return chunks
    
    # 检查是否超出纠错能力
    if len(missing_indices) > redundancy_blocks:
        return chunks
    
    # 将现有块转换为字节数组
    chunk_bytes = {}
    max_len = 0
    for idx, chunk in chunks.items():
        chunk_bytes[idx] = chunk.encode("utf-8")
        max_len = max(max_len, len(chunk_bytes[idx]))
    
    # 填充所有块到相同长度
    for idx in chunk_bytes:
        chunk_bytes[idx] = chunk_bytes[idx].ljust(max_len, b'\x00')
    
    # 创建Reed-Solomon解码器
    rs = RSCodec(redundancy_blocks)
    
    # 对每个字符位置进行解码
    recovered_chunks = {i: bytearray() for i in range(1, original_count + 1)}
    
    for i in range(max_len):
        # 构建当前列的数据
        column = []
        column_indices = []
        for idx in range(1, original_count + redundancy_blocks + 1):
            if idx in chunk_bytes:
                column.append(chunk_bytes[idx][i])
                column_indices.append(idx)
            else:
                column.append(0)  # 填充占位符
                column_indices.append(idx)
        
        try:
            # 尝试解码
            decoded_column = rs.decode(column)
            
            # 提取原始数据块
            for j in range(original_count):
                recovered_chunks[j + 1].append(decoded_column[j])
        except Exception:
            # 解码失败，跳过此位置
            continue
    
    # 转换回字符串并更新块
    for i in range(1, original_count + 1):
        if i not in chunks:  # 只更新缺失的块
            chunk_str = bytes(recovered_chunks[i]).rstrip(b'\x00').decode("utf-8")
            chunks[i] = chunk_str
    
    return chunks


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

    # 存储块数据：{idx: (crc32, data)}
    chunks_data = {}
    expected_total = None
    has_crc32 = False  # 检测是否使用了CRC32
    processed_files = 0
    total_files = len(image_files)

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

                for idx, chunk_total, crc32, data in parsed_chunks:
                    if expected_total is None:
                        expected_total = chunk_total
                    if crc32 is not None:
                        has_crc32 = True
                    chunks_data[idx] = (crc32, data)

                print(tr(lang, "fragments", count=len(decoded_objects)))
            except Exception as e:
                print(tr(lang, "scan_error", error=e))
            finally:
                processed_files += 1
                display_total = expected_total if expected_total is not None else "?"
                
                # 1. 发送 GUI 控制指令（控制平面）
                print(f"__PROGRESS__::{len(chunks_data)}::{display_total}")
                
                # 2. 输出多语言日志（数据平面）
                print(tr(lang, "progress", total=display_total, current=len(chunks_data)))

    print("=" * 50)
    if not expected_total:
        return print(tr(lang, "no_qr"))

    # 检查缺失块和校验失败块
    missing_chunks = [i for i in range(1, expected_total + 1) if i not in chunks_data]
    crc_failed_chunks = []
    
    if has_crc32:
        # 进行CRC32校验
        valid_chunks = 0
        for idx in chunks_data:
            crc32, data = chunks_data[idx]
            if _verify_crc32(data, crc32):
                valid_chunks += 1
            else:
                crc_failed_chunks.append(idx)
        
        print(tr(lang, "verification_summary", valid_count=valid_chunks, corrupted_count=len(crc_failed_chunks)))
        
        if crc_failed_chunks:
            print(tr(lang, "crc_check_failed", chunk_ids=crc_failed_chunks))
        else:
            print(tr(lang, "crc_check_passed"))
    
    # 统计总损坏块数
    total_corrupted = len(missing_chunks) + len(crc_failed_chunks)
    
    if missing_chunks:
        print(tr(lang, "missing_chunks", missing_chunks=missing_chunks))
    
    print(tr(lang, "total_corrupted", corrupted_count=total_corrupted))
    
    # 如果有损坏且启用了CRC32，尝试Reed-Solomon纠错
    if has_crc32 and total_corrupted > 0:
        # 检查是否在纠错能力范围内
        # 假设冗余块数为总数的5%（与编码端一致）
        redundancy_blocks = max(2, int(expected_total * 0.05))
        
        if total_corrupted <= redundancy_blocks:
            print(tr(lang, "rs_recovery_started"))
            
            # 构建完整的块字典用于纠错
            full_chunks = {}
            for idx in range(1, expected_total + 1):
                if idx in chunks_data:
                    crc32, data = chunks_data[idx]
                    # 如果CRC32校验失败，标记为None表示损坏
                    if idx in crc_failed_chunks:
                        full_chunks[idx] = None
                    else:
                        full_chunks[idx] = data
                else:
                    full_chunks[idx] = None  # 缺失块
            
            # 计算原始数据块数量
            original_count = expected_total - redundancy_blocks
            
            # 使用Reed-Solomon解码
            try:
                recovered_chunks = _reed_solomon_decode(
                    {idx: data for idx, data in full_chunks.items() if data is not None},
                    redundancy_blocks,
                    original_count
                )
                
                # 统计恢复的块
                recovered_count = 0
                for idx in range(1, original_count + 1):
                    if idx not in chunks_data or idx in crc_failed_chunks:
                        if idx in recovered_chunks:
                            # 验证恢复的块
                            recovered_data = recovered_chunks[idx]
                            recovered_crc32 = _calculate_crc32(recovered_data)
                            
                            # 检查是否有期望的CRC32（如果之前有校验失败）
                            if idx in crc_failed_chunks:
                                expected_crc32 = chunks_data[idx][0]
                                if recovered_crc32 == expected_crc32:
                                    chunks_data[idx] = (recovered_crc32, recovered_data)
                                    recovered_count += 1
                            elif idx in missing_chunks:
                                chunks_data[idx] = (recovered_crc32, recovered_data)
                                recovered_count += 1
                
                if recovered_count > 0:
                    print(tr(lang, "rs_recovery_success", recovered_count=recovered_count))
                    
                    # 验证恢复后的数据
                    new_crc_failed = []
                    for idx in range(1, original_count + 1):
                        if idx in chunks_data:
                            crc32, data = chunks_data[idx]
                            if not _verify_crc32(data, crc32):
                                new_crc_failed.append(idx)
                    
                    if not new_crc_failed:
                        print(tr(lang, "rs_verification_passed"))
                    else:
                        print(tr(lang, "rs_verification_failed", chunk_ids=new_crc_failed))
                else:
                    print(tr(lang, "rs_recovery_failed", max_recoverable=redundancy_blocks))
                    
            except Exception as e:
                print(tr(lang, "scan_error", error=f"Reed-Solomon纠错失败: {e}"))
        else:
            print(tr(lang, "rs_recovery_failed", max_recoverable=redundancy_blocks))
        
        # 重新统计缺失块
        missing_chunks = [i for i in range(1, expected_total + 1) if i not in chunks_data]
        crc_failed_chunks = []
        for idx in chunks_data:
            crc32, data = chunks_data[idx]
            if not _verify_crc32(data, crc32):
                crc_failed_chunks.append(idx)
    
    # 检查是否所有块都已恢复
    all_recovered = len(missing_chunks) == 0 and len(crc_failed_chunks) == 0
    
    if not all_recovered:
        unrecoverable_count = len(missing_chunks) + len(crc_failed_chunks)
        unrecoverable_ids = sorted(missing_chunks + crc_failed_chunks)
        print(tr(lang, "corrupted_blocks_tip", unrecoverable_count=unrecoverable_count, chunk_ids=unrecoverable_ids))
        return
    
    # 提取数据
    original_text = "".join([chunks_data[i][1] for i in range(1, expected_total + 1)])

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
