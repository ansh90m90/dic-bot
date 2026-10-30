"""Pillow-powered 880x500 Discord Dark Occult profile card generator."""
from __future__ import annotations

import io
import math
from typing import Optional, Dict, Any

from PIL import Image, ImageDraw, ImageFont

from data import pathways

# Discord Dark Occult Color Palette
COLOR_BG_OUTER = (17, 18, 20)        # #111214
COLOR_BG_CARD = (30, 31, 34)         # #1E1F22
COLOR_PANEL = (43, 45, 49)           # #2B2D31
COLOR_PANEL_ALT = (49, 51, 56)       # #313338
COLOR_BORDER = (56, 58, 64)          # #383A40
COLOR_TEXT_PRIMARY = (242, 243, 245) # #F2F3F5
COLOR_TEXT_MUTED = (148, 155, 164)   # #949BA4
COLOR_TEXT_GOLD = (240, 180, 41)     # #F0B229
COLOR_TAROT = (179, 159, 224)        # #B39FE0

# Progress bar gradient colors
COLOR_BAR_BG = (35, 36, 40)
COLOR_DIGESTION = (156, 92, 219)     # Mystic Violet
COLOR_SANITY = (56, 178, 172)        # Calming Teal
COLOR_CORRUPTION = (229, 62, 62)     # Eldritch Crimson

# Cosmic Group Hex to RGB
GROUP_COLORS_RGB: Dict[str, tuple[int, int, int]] = {
    "Lord of the Mysteries": (123, 116, 184),
    "God Almighty": (217, 180, 74),
    "Eternal Darkness": (78, 78, 106),
    "Calamity of Destruction": (196, 61, 73),
    "Demon of Knowledge": (78, 154, 120),
    "Father of Devils": (138, 58, 80),
    "Goddess of Origin": (201, 140, 182),
    "Anarchy": (168, 136, 72),
    "Key of Light": (179, 159, 224),
}


def _get_font(size: int, bold: bool = False) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """Attempt to load standard Linux system fonts or fall back to default."""
    font_names = (
        ["DejaVuSans-Bold.ttf", "FreeSansBold.ttf", "LiberationSans-Bold.ttf"]
        if bold
        else ["DejaVuSans.ttf", "FreeSans.ttf", "LiberationSans.ttf"]
    )
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def _draw_rounded_rect(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    radius: int,
    fill: Optional[tuple[int, int, int]] = None,
    outline: Optional[tuple[int, int, int]] = None,
    width: int = 1,
) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _draw_progress_bar(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    w: int,
    h: int,
    percent: float,
    fill_color: tuple[int, int, int],
) -> None:
    # Background slot
    _draw_rounded_rect(draw, (x, y, x + w, y + h), radius=h // 2, fill=COLOR_BAR_BG)
    # Filled portion
    fill_w = max(0, min(w, int(w * (percent / 100.0))))
    if fill_w > h:
        _draw_rounded_rect(
            draw, (x, y, x + fill_w, y + h), radius=h // 2, fill=fill_color
        )
    elif fill_w > 0:
        draw.rectangle((x, y, x + fill_w, y + h), fill=fill_color)


def _draw_sacred_geometry_ring(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    radius: int,
    color: tuple[int, int, int],
) -> None:
    """Draw a sacred-geometry concentric circle and radial tick frame."""
    # Outer ring
    draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=color, width=2)
    # Inner subtle ring
    inner_r = radius - 6
    draw.ellipse(
        (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
        outline=(color[0] // 2, color[1] // 2, color[2] // 2),
        width=1,
    )
    # 12 cardinal and astrological tick marks
    for i in range(12):
        angle = math.radians(i * 30)
        x1 = cx + int((radius - 2) * math.cos(angle))
        y1 = cy + int((radius - 2) * math.sin(angle))
        x2 = cx + int((radius + 6) * math.cos(angle))
        y2 = cy + int((radius + 6) * math.sin(angle))
        draw.line((x1, y1, x2, y2), fill=color, width=2)


def render_profile_card(
    user_data: Dict[str, Any],
    display_name: str,
    avatar_bytes: Optional[bytes] = None,
    tarot_card: Optional[str] = None,
) -> io.BytesIO:
    """Render an 880x500 Discord Dark Occult profile card."""
    width, height = 880, 500
    image = Image.new("RGBA", (width, height), COLOR_BG_OUTER)
    draw = ImageDraw.Draw(image)

    # Main Card Container
    _draw_rounded_rect(
        draw,
        (16, 16, width - 16, height - 16),
        radius=14,
        fill=COLOR_BG_CARD,
        outline=COLOR_BORDER,
        width=1,
    )

    pathway_key = user_data.get("pathway") or "fool"
    seq = int(user_data.get("sequence") if user_data.get("sequence") is not None else 9)
    p_data = pathways.get_pathway(pathway_key) or {}
    pathway_name = p_data.get("name", "Unknown")
    above_seq = p_data.get("above", "Spirit World")
    seq_title = pathways.sequence_name(pathway_key, seq)
    rank = pathways.rank_title(seq)

    group_color = GROUP_COLORS_RGB.get(above_seq, (150, 150, 170))

    # Fonts
    font_title = _get_font(22, bold=True)
    font_sub = _get_font(14, bold=False)
    font_bold = _get_font(13, bold=True)
    font_small = _get_font(11, bold=False)
    font_stat = _get_font(18, bold=True)

    # 1. Avatar (Left side: cx=130, cy=140, r=60 -> 120x120)
    avatar_cx, avatar_cy, avatar_r = 130, 135, 58
    if avatar_bytes:
        try:
            av_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            av_img = av_img.resize((avatar_r * 2, avatar_r * 2), Image.Resampling.LANCZOS)
            mask = Image.new("L", (avatar_r * 2, avatar_r * 2), 0)
            mask_draw = ImageDraw.Draw(mask)
            mask_draw.ellipse((0, 0, avatar_r * 2, avatar_r * 2), fill=255)
            image.paste(av_img, (avatar_cx - avatar_r, avatar_cy - avatar_r), mask)
        except Exception:
            # Fallback circle if image parsing fails
            draw.ellipse(
                (avatar_cx - avatar_r, avatar_cy - avatar_r, avatar_cx + avatar_r, avatar_cy + avatar_r),
                fill=COLOR_PANEL,
            )
    else:
        draw.ellipse(
            (avatar_cx - avatar_r, avatar_cy - avatar_r, avatar_cx + avatar_r, avatar_cy + avatar_r),
            fill=COLOR_PANEL,
        )

    # Sacred geometry ring around avatar
    _draw_sacred_geometry_ring(draw, avatar_cx, avatar_cy, avatar_r + 5, group_color)

    # Sequence Badge underneath avatar
    badge_text = f"SEQ {seq} · {seq_title.upper()}"
    badge_y = avatar_cy + avatar_r + 20
    _draw_rounded_rect(
        draw,
        (35, badge_y, 225, badge_y + 26),
        radius=6,
        fill=COLOR_PANEL,
        outline=group_color,
        width=1,
    )
    draw.text((130, badge_y + 13), badge_text, fill=COLOR_TEXT_PRIMARY, font=font_small, anchor="mm")

    # Tarot Seat Pill
    seat_text = f"Seat: {tarot_card}" if tarot_card else "Seat: Unseated Mortal"
    draw.text((130, badge_y + 40), seat_text, fill=COLOR_TAROT, font=font_small, anchor="mm")

    # 2. Right Dossier / Header
    header_x = 255
    # Name
    clean_name = display_name[:24]
    draw.text((header_x, 40), clean_name, fill=COLOR_TEXT_PRIMARY, font=font_title)
    # Pathway & Rank
    draw.text(
        (header_x, 70),
        f"Path of {pathway_name}  ·  Sequence {seq} ({rank})",
        fill=group_color,
        font=font_bold,
    )
    # Above the Sequences
    draw.text(
        (header_x, 92),
        f"Above the Sequences: {above_seq}",
        fill=COLOR_TEXT_MUTED,
        font=font_sub,
    )

    # 3. Dynamic Progress Bars
    bar_x = header_x
    bar_w = 575
    bar_h = 14

    digestion = float(user_data.get("digestion") or 0.0)
    sanity = float(user_data.get("sanity") or 100.0)
    corruption = float(user_data.get("corruption") or 0.0)

    # Digestion Bar
    draw.text((bar_x, 126), f"Digestion: {digestion:.1f}% / 100%", fill=COLOR_TEXT_PRIMARY, font=font_small)
    _draw_progress_bar(draw, bar_x, 142, bar_w, bar_h, digestion, COLOR_DIGESTION)

    # Sanity Bar
    draw.text((bar_x, 168), f"Sanity: {sanity:.1f}%", fill=COLOR_TEXT_PRIMARY, font=font_small)
    _draw_progress_bar(draw, bar_x, 184, bar_w, bar_h, sanity, COLOR_SANITY)

    # Corruption Bar
    draw.text((bar_x, 210), f"Corruption: {corruption:.1f}%", fill=COLOR_TEXT_PRIMARY, font=font_small)
    _draw_progress_bar(draw, bar_x, 226, bar_w, bar_h, corruption, COLOR_CORRUPTION)

    # 4. 4-Card Grid (Y: 265 to 370)
    grid_y = 265
    grid_h = 80
    card_w = 188
    spacing = 15

    gold = int(user_data.get("gold") or 0)
    tarot_coins = int(user_data.get("tarot_coins") or 0)
    active_days = int(user_data.get("active_days") or 0)
    vc_mins = int(user_data.get("vc_minutes") or 0)
    vc_hours = vc_mins / 60.0

    cards_data = [
        ("GOLD POUNDS", f"{gold:,} G", COLOR_TEXT_GOLD),
        ("TAROT COINS", f"{tarot_coins:,} TC", COLOR_TAROT),
        ("ACTIVE DAYS", f"{active_days} Days", COLOR_TEXT_PRIMARY),
        ("VOICE TIME", f"{vc_hours:.1f} hrs", (114, 137, 218)),
    ]

    for i, (label, val, val_color) in enumerate(cards_data):
        cx = 40 + i * (card_w + spacing)
        _draw_rounded_rect(
            draw,
            (cx, grid_y, cx + card_w, grid_y + grid_h),
            radius=8,
            fill=COLOR_PANEL,
            outline=COLOR_BORDER,
            width=1,
        )
        draw.text((cx + 14, grid_y + 12), label, fill=COLOR_TEXT_MUTED, font=font_small)
        draw.text((cx + 14, grid_y + 36), val, fill=val_color, font=font_stat)

    # 5. Bottom Ribbon: Next Ascension Requirements (Y: 365 to 468)
    ribbon_y = 365
    _draw_rounded_rect(
        draw,
        (40, ribbon_y, width - 40, ribbon_y + 100),
        radius=8,
        fill=COLOR_PANEL_ALT,
        outline=COLOR_BORDER,
        width=1,
    )

    if seq > 0:
        target_seq = seq - 1
        req = pathways.advancement_requirements(target_seq)
        target_title = pathways.sequence_name(pathway_key, target_seq)
        est_time = pathways.estimated_ascension_time(seq, digestion)

        draw.text(
            (56, ribbon_y + 12),
            f"✦ NEXT: Seq {target_seq} {target_title}  ·  Est. Time: {est_time}",
            fill=COLOR_TEXT_GOLD,
            font=font_bold,
        )

        char_text = f"{req.get('characteristics', 1)}× Seq {target_seq} Char"
        ing_parts = [f"{count} {r.title()}" for r, count in req.get("ingredients", {}).items()]
        ing_text = " + ".join(ing_parts) if ing_parts else "None"

        req_line1 = (
            f"Needs: 100% Digestion · {req.get('gold', 0):,} Gold · {req.get('tarot', 0)} Tarot Coins · "
            f"1× Formula · {char_text}"
        )
        req_line2 = (
            f"Ingredients: {ing_text} | Min Days: {req.get('min_active_days', 0)} | "
            f"Sanity ≥ {req.get('min_sanity', 0):.0f}% | Corruption ≤ {req.get('max_corruption', 100):.0f}%"
        )
        trial = req.get("trial")
        hazard = req.get("hazard_percent", 0.0)
        req_line3 = f"Trial: {trial.title() if trial else 'None'} | Backlash Hazard: {hazard:.0f}%"

        draw.text((56, ribbon_y + 35), req_line1, fill=COLOR_TEXT_PRIMARY, font=font_small)
        draw.text((56, ribbon_y + 54), req_line2, fill=COLOR_TEXT_MUTED, font=font_small)
        draw.text((56, ribbon_y + 73), req_line3, fill=COLOR_TEXT_MUTED, font=font_small)
    else:
        draw.text(
            (56, ribbon_y + 38),
            "✦ THE APEX REACHED: You sit upon the Divine Throne as Sequence 0 True God.",
            fill=COLOR_TEXT_GOLD,
            font=font_title,
        )

    # Save to buffer
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    buf.seek(0)
    return buf
