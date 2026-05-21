from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps


ICON_SIZES = [(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48), (64, 64), (128, 128), (256, 256)]


def build_icon(src: Path, dst: Path, base_size: int = 256, content_size: int = 248) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)

    image = Image.open(src).convert("RGBA")

    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    if bbox:
        image = image.crop(bbox)

    if image.width != image.height:
        side = min(image.width, image.height)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side))

    fitted = ImageOps.fit(image, (content_size, content_size), method=Image.Resampling.LANCZOS)
    fitted = fitted.filter(ImageFilter.UnsharpMask(radius=1.0, percent=180, threshold=2))

    canvas = Image.new("RGBA", (base_size, base_size), (0, 0, 0, 0))
    canvas.paste(
        fitted,
        ((base_size - fitted.width) // 2, (base_size - fitted.height) // 2),
        fitted,
    )
    canvas.save(dst, format="ICO", sizes=ICON_SIZES)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate multi-size ICO files from PNG sources.")
    parser.add_argument("--light-src", required=True)
    parser.add_argument("--dark-src", required=True)
    parser.add_argument("--light-dst", required=True)
    parser.add_argument("--dark-dst", required=True)
    parser.add_argument("--base-size", type=int, default=256)
    parser.add_argument("--content-size", type=int, default=248)
    args = parser.parse_args()

    build_icon(Path(args.light_src), Path(args.light_dst), args.base_size, args.content_size)
    build_icon(Path(args.dark_src), Path(args.dark_dst), args.base_size, args.content_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
