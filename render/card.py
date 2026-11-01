"""Pillow renderer for the welcome card and avatar thumbnail."""

from __future__ import annotations

import io
import os
from typing import Mapping

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import settings as settings_store

W, H = 1024, 384
SS = 2
FONT_DIR = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

CARD_RADIUS = 26
CX, CY, R = 176, 192, 112

HEADLINE = (234, 240, 255)
MUTED = (150, 165, 196)
SUBTLE = (116, 132, 164)


def _font(px: float, *, bold: bool = True, emoji: bool = False) -> ImageFont.FreeTypeFont:
    name = "seguiemj.ttf" if emoji else ("segoeuib.ttf" if bold else "segoeui.ttf")
    return ImageFont.truetype(os.path.join(FONT_DIR, name), max(8, int(px * SS)))


def _is_emoji(ch: str) -> bool:
    cp = ord(ch)
    return 0x1F000 <= cp <= 0x1FAFF or 0x2600 <= cp <= 0x27BF or 0xFE00 <= cp <= 0xFE0F


def _hex(value: str) -> tuple[int, int, int]:
    return settings_store.color_rgb(value)


def _mix(a, b, t: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _background(w: int, h: int, theme: Mapping[str, str]) -> Image.Image:
    """Vertical gradient in the theme colours with an accent bloom behind the avatar."""
    top, bottom = _hex(theme["card_top"]), _hex(theme["card_bottom"])
    small = Image.new("RGB", (24, 24))
    px = small.load()
    for y in range(24):
        color = _mix(top, bottom, y / 23)
        for x in range(24):
            px[x, y] = color
    bg = small.resize((w, h), Image.BICUBIC).convert("RGBA")

    accent = _hex(theme["accent"])
    bloom = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(bloom).ellipse(
        [(CX - R - 70) * SS, (CY - R - 70) * SS, (CX + R + 70) * SS, (CY + R + 70) * SS],
        fill=(*accent, 42),
    )
    bloom = bloom.filter(ImageFilter.GaussianBlur(80 * SS))
    return Image.alpha_composite(bg, bloom)


def _initials_avatar(name: str, size: int, accent: tuple[int, int, int]) -> Image.Image:
    """Fallback avatar: accent gradient circle with the member's initials."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    grad = Image.new("RGBA", (32, 32))
    px = grad.load()
    light, dark = _mix(accent, (255, 255, 255), 0.35), _mix(accent, (8, 12, 26), 0.55)
    for y in range(32):
        for x in range(32):
            t = (x + y) / 62
            px[x, y] = (*_mix(light, dark, t), 255)
    grad = grad.resize((size, size), Image.BICUBIC)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    img.paste(grad, (0, 0), mask)

    initials = "".join(part[0] for part in name.split()[:2] if part)[:2].upper() or "?"
    font = ImageFont.truetype(os.path.join(FONT_DIR, "segoeuib.ttf"), int(size * 0.38))
    ImageDraw.Draw(img).text(
        (size / 2, size / 2 + size * 0.02), initials, font=font, fill=(255, 255, 255, 255), anchor="mm"
    )
    return img


def _square(image_bytes: bytes, size: int) -> Image.Image:
    src = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    side = min(src.size)
    src = src.crop(
        (
            (src.width - side) // 2,
            (src.height - side) // 2,
            (src.width + side) // 2,
            (src.height + side) // 2,
        )
    )
    return src.resize((size, size), Image.LANCZOS)


def _circle(image: Image.Image) -> Image.Image:
    size = image.width
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size - 1, size - 1), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(image, (0, 0), mask)
    return out


def _avatar(name: str, avatar_bytes: bytes | None, size: int, accent) -> Image.Image:
    if avatar_bytes:
        return _circle(_square(avatar_bytes, size))
    return _initials_avatar(name, size, accent)


def _emoji_runs(text: str):
    runs, buf, prev = [], "", None
    for ch in text:
        flag = _is_emoji(ch)
        if prev is None or flag == prev:
            buf += ch
        else:
            runs.append((buf, prev))
            buf = ch
        prev = flag
    if buf:
        runs.append((buf, bool(prev)))
    return runs


def _draw_tracked(draw, x, baseline, text, font, fill, tracking: float) -> float:
    for ch in text:
        draw.text((x, baseline), ch, font=font, fill=fill, anchor="ls")
        x += draw.textlength(ch, font=font) + tracking * SS
    return x


def _draw_rich(draw, x, baseline, chunks, tracking: float = 0.0) -> float:
    """Draw mixed emoji/latin chunks left to right; tracking only affects latin text."""
    for text, font, fill, emoji in chunks:
        if emoji or not tracking:
            draw.text((x, baseline), text, font=font, fill=fill, anchor="ls")
            x += draw.textlength(text, font=font)
        else:
            x = _draw_tracked(draw, x, baseline, text, font, fill, tracking)
    return x


def _fit_font(draw, text: str, start_px: float, max_width: float) -> ImageFont.FreeTypeFont:
    px = start_px
    while px > 18:
        font = _font(px)
        if draw.textlength(text, font=font) <= max_width * SS:
            return font
        px -= 2
    return _font(px)


def render_card(
    *,
    username: str,
    position: int,
    goal: int,
    avatar_bytes: bytes | None,
    flags: str,
    card_title: str,
    footer: str,
    theme: Mapping[str, str],
) -> bytes:
    """Render the welcome banner and return PNG bytes."""
    accent = _hex(theme["accent"])
    border = _hex(theme["border"])
    bar_fill = _hex(theme["bar_fill"])
    bar_track = _hex(theme["bar_track"])

    w, h = W * SS, H * SS
    canvas = _background(w, h, theme)
    card_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(card_mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=CARD_RADIUS * SS, fill=255)
    card = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card.paste(canvas, (0, 0), card_mask)

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [(CX - R) * SS, (CY - R) * SS, (CX + R) * SS, (CY + R) * SS],
        outline=(*bar_fill, 70),
        width=8 * SS,
    )
    card = Image.alpha_composite(card, glow.filter(ImageFilter.GaussianBlur(14 * SS)))

    size = 2 * (R - 6) * SS
    avatar = _avatar(username, avatar_bytes, size, accent)
    card.paste(avatar, ((CX - R + 6) * SS, (CY - R + 6) * SS), avatar)

    draw = ImageDraw.Draw(card)
    draw.ellipse(
        [(CX - R) * SS, (CY - R) * SS, (CX + R) * SS, (CY + R) * SS],
        outline=(*bar_fill, 255),
        width=5 * SS,
    )
    draw.rounded_rectangle(
        [337 * SS, 56 * SS, 339 * SS, 328 * SS], radius=2 * SS, fill=_mix(border, bar_fill, 0.12)
    )

    left, right = 376, 966

    _draw_rich(draw, left * SS, 86 * SS, [(card_title, _font(21), HEADLINE, False)], tracking=3.0)

    name_font = _fit_font(draw, username, 66, right - left)
    draw.text((left * SS, 156 * SS), username, font=name_font, fill=HEADLINE, anchor="ls")

    meta = []
    if flags:
        for chunk, emoji in _emoji_runs(flags + " / "):
            meta.append((chunk, _font(22, bold=False, emoji=emoji), MUTED, emoji))
    meta.append((f"MEMBER {position}", _font(21), MUTED, False))
    _draw_rich(draw, left * SS, 200 * SS, meta, tracking=0.6)

    ratio = 0.0 if goal <= 0 else max(0.0, min(1.0, position / goal))
    draw.rounded_rectangle([left * SS, 240 * SS, right * SS, 254 * SS], radius=7 * SS, fill=bar_track)
    if ratio > 0:
        filled = left + max(14, (right - left) * ratio)
        draw.rounded_rectangle([left * SS, 240 * SS, filled * SS, 254 * SS], radius=7 * SS, fill=bar_fill)

    _draw_rich(
        draw, left * SS, 288 * SS,
        [(f"COMMUNITY GOAL   {position} / {goal}", _font(19), HEADLINE, False)],
        tracking=1.0,
    )
    draw.text(
        (right * SS, 288 * SS),
        f"{round(ratio * 100)}%",
        font=_font(21),
        fill=HEADLINE,
        anchor="rs",
    )

    _draw_rich(draw, left * SS, 330 * SS, [(footer, _font(13), SUBTLE, False)], tracking=2.6)

    draw.rounded_rectangle(
        (1 * SS, 1 * SS, w - 1 * SS, h - 1 * SS), radius=CARD_RADIUS * SS, outline=border, width=2 * SS
    )

    out = io.BytesIO()
    card.resize((W, H), Image.LANCZOS).convert("RGB").save(out, "PNG", optimize=True)
    return out.getvalue()


def render_avatar(avatar_bytes: bytes | None, name: str, theme: Mapping[str, str], size: int = 256) -> bytes:
    """Square avatar used as the message thumbnail (falls back to initials)."""
    image = _square(avatar_bytes, size) if avatar_bytes else _initials_avatar(name, size, _hex(theme["accent"]))
    out = io.BytesIO()
    image.save(out, "PNG", optimize=True)
    return out.getvalue()
