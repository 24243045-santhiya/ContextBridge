"""Image validation, normalisation and (only when reliable) region highlighting."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw, UnidentifiedImageError

MAX_BYTES = 15 * 1024 * 1024
MAX_SIDE = 1600
ALLOWED_EXT = {".png", ".jpg", ".jpeg", ".webp"}


def load_image(data: bytes, name: str = "image") -> bytes:
    """Validate and return normalised PNG bytes. Raises ValueError with a friendly message."""
    if not data:
        raise ValueError("The image is empty.")
    if len(data) > MAX_BYTES:
        raise ValueError("The image is larger than 15 MB. Please upload a smaller screenshot.")
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext and ext not in ALLOWED_EXT:
        raise ValueError(f"Unsupported file type '{ext}'. Use PNG, JPG or WEBP.")
    try:
        Image.open(io.BytesIO(data)).verify()
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValueError("That file is not a readable image.") from None
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


def valid_box(box) -> bool:
    try:
        x, y, w, h = [float(v) for v in box]
    except (TypeError, ValueError):
        return False
    return 0 <= x <= 1 and 0 <= y <= 1 and w >= 0.01 and h >= 0.01 and x + w <= 1.02 and y + h <= 1.02


def annotate(data: bytes, box) -> tuple[bytes, bool]:
    """Draw the highlight if (and only if) the box is valid. Returns (png, drawn)."""
    if not valid_box(box):
        return data, False
    img = Image.open(io.BytesIO(data)).convert("RGBA")
    W, H = img.size
    x, y, w, h = [float(v) for v in box]
    rect = [x * W, y * H, (x + w) * W, (y + h) * H]
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rectangle(rect, fill=(251, 191, 36, 45), outline=(251, 191, 36, 255), width=max(3, W // 300))
    out = Image.alpha_composite(img, layer).convert("RGB")
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue(), True
