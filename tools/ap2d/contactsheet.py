"""Contact sheet — 20개 결과를 한 장에 늘어놓아 'variation 이 실제로 다르게 보이는가'를
사람이 10초 안에 판단하게 만드는 것이 목적이다.

각 칸에 seed / archetype / 주요 파츠 조합 / 팔레트를 같이 찍는다.
"""

import json
import os

from PIL import Image, ImageDraw, ImageFont

from . import paths

BG = (250, 250, 251, 255)
CARD = (255, 255, 255, 255)
BORDER = (222, 224, 228, 255)
INK = (24, 26, 30, 255)
MUTED = (108, 114, 124, 255)
ACCENT = (188, 76, 60, 255)

FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)

def label_slots(definitions, rule=None, limit=8):
    """라벨에 찍을 슬롯을 **데이터에서** 고른다.

    예전에는 CC0 팩 실측값(head/eyes/mouth/…)을 상수로 박아두었다. 팩이 바뀌면
    라벨이 전부 비는 코드였다. 이제는 이 집단 안에서 **실제로 값이 갈리는** 슬롯만
    고른다 — 그게 정확히 사람이 보고 싶어 하는 정보이기도 하다.
    (전 캐릭터가 같은 값인 body/hand/foot 은 자동으로 빠진다.)

    순서는 규칙의 layer_order 를 따르고, 없으면 이름순.
    """
    values = {}
    for definition in definitions:
        for slot, value in (definition.get("parts") or {}).items():
            values.setdefault(slot, set()).add(value)
    varying = [slot for slot, vals in values.items() if len(vals) > 1]

    order = (rule or {}).get("layer_order") or []
    rank = {slot: i for i, slot in enumerate(order)}
    varying.sort(key=lambda s: (rank.get(s, len(rank)), s))
    return varying[:limit]


def short_name(slot):
    """슬롯 이름을 라벨용으로 줄인다. 팩마다 슬롯 이름이 다르므로 규칙으로 만든다."""
    tokens = [t for t in slot.replace("-", "_").split("_") if t]
    if not tokens:
        return slot[:2]
    head = tokens[0]
    abbrev = head[0] + (head[1] if len(head) > 1 else "")
    if len(tokens) > 1:
        abbrev += tokens[1][0]
    return abbrev


def _font(size, bold=True):
    order = FONT_CANDIDATES if bold else FONT_CANDIDATES[1:] + FONT_CANDIDATES[:1]
    for path in order:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def load_characters(profile_dir):
    """<profile>/<seed>/character.json 을 seed 순으로 읽는다."""
    out = []
    for name in sorted(os.listdir(profile_dir), key=lambda n: (len(n), n)):
        cdir = os.path.join(profile_dir, name)
        cpath = os.path.join(cdir, "character.json")
        if not os.path.isfile(cpath):
            continue
        with open(cpath, "r", encoding="utf-8") as fh:
            out.append((cdir, json.load(fh)))
    return out


def _trim_value(slot, value):
    """'eyes4' -> '4'. 슬롯 이름과 겹치는 접두어를 떼서 라벨을 짧게 만든다.

    팩별 접두어 목록을 박아두지 않고, 슬롯 이름 토큰과 겹치는 부분만 떼어낸다.
    """
    trimmed = value
    candidates = [slot, slot.replace("_", "")]
    candidates += [t for t in slot.split("_") if len(t) > 1]
    for prefix in sorted(candidates, key=len, reverse=True):
        if len(trimmed) > len(prefix) and trimmed.lower().startswith(prefix.lower()):
            trimmed = trimmed[len(prefix):]
            break
    return trimmed.lstrip("_-")


def _part_label(definition, slots):
    bits = []
    for slot in slots:
        value = (definition.get("parts") or {}).get(slot)
        if not value:
            continue
        bits.append("%s%s" % (short_name(slot), _trim_value(slot, value) or "1"))
    return " ".join(bits)


def build_direction_sheet(profile_dir, out_path, animation="walk", seed=None,
                          scale=3, title=None):
    """캐릭터 하나의 한 애니메이션을 **방향별로 한 줄씩** 쌓아 보여준다.

    좌표가 맞아도 hair/torso/feet 가 실제로 어긋나는 문제는 숫자로는 안 보인다.
    방향을 나란히 놓으면 사람이 바로 발견한다.

    방향 축이 없는 팩에서는 만들 것이 없으므로 None 을 돌려준다.
    """
    items = load_characters(profile_dir)
    if not items:
        raise RuntimeError("캐릭터가 없다: %s" % paths.rel(profile_dir))
    if seed is not None:
        items = [(d, c) for d, c in items if c.get("seed") == seed] or items
    cdir, definition = items[0]

    rows = []
    for key, info in sorted((definition.get("outputs", {}).get("sheets") or {}).items()):
        if info.get("animation", key) != animation or not info.get("direction"):
            continue
        path = os.path.join(cdir, info["file"])
        if os.path.isfile(path):
            with Image.open(path) as im:
                rows.append((info["direction"], im.convert("RGBA")))
    if not rows:
        return None

    f_dir = _font(13, bold=True)
    f_head = _font(20, bold=True)
    label_w = 62
    pad = 10
    head_h = 34 if title else 0
    row_w = max(im.width for _d, im in rows) * scale
    row_h = max(im.height for _d, im in rows) * scale
    width = label_w + row_w + pad * 2
    height = head_h + len(rows) * (row_h + pad) + pad

    sheet = Image.new("RGBA", (width, height), BG)
    draw = ImageDraw.Draw(sheet)
    if title:
        draw.text((pad, 8), title, font=f_head, fill=INK)

    y = head_h + pad
    for direction, im in rows:
        # 정수배 NEAREST — 픽셀아트가 뭉개지면 어긋남을 못 본다
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        sheet.alpha_composite(big, (label_w, y))
        draw.text((pad, y + row_h // 2 - 7), direction, font=f_dir, fill=MUTED)
        y += row_h + pad

    paths.ensure_dir(os.path.dirname(out_path))
    sheet.convert("RGB").save(paths.assert_writable(out_path))
    return out_path, [d for d, _im in rows], definition.get("seed")


def build_animation_strip(profile_dir, out_path, seed=None, animations=None,
                          direction=None, scale=3, title=None, note=None):
    """캐릭터 하나를 **애니메이션별로 한 줄씩** 쌓는다.

    애니메이션마다 지원 파츠가 다른 팩에서, 어떤 레이어가 사라지고 다시 돌아오는지
    사람이 한눈에 보게 하려는 것이다. 자동 테스트가 통과해도 구조 오류는 눈으로만
    잡히는 경우가 있다.
    """
    items = load_characters(profile_dir)
    if not items:
        raise RuntimeError("캐릭터가 없다: %s" % paths.rel(profile_dir))
    if seed is not None:
        items = [(d, c) for d, c in items if c.get("seed") == seed] or items
    cdir, definition = items[0]

    sheets = definition.get("outputs", {}).get("sheets") or {}
    rows = []
    for key in sorted(sheets):
        info = sheets[key]
        animation = info.get("animation", key)
        if animations and animation not in animations:
            continue
        if direction and info.get("direction") != direction:
            continue
        path = os.path.join(cdir, info["file"])
        if not os.path.isfile(path):
            continue
        with Image.open(path) as im:
            rows.append((animation, im.convert("RGBA")))
    if animations:
        order = {a: i for i, a in enumerate(animations)}
        rows.sort(key=lambda r: order.get(r[0], len(order)))
    if not rows:
        return None

    f_label = _font(13, bold=True)
    f_head = _font(19, bold=True)
    f_note = _font(12, bold=False)
    label_w = 64
    pad = 10
    head_h = (34 if title else 0) + (20 if note else 0)
    row_w = max(im.width for _a, im in rows) * scale
    row_h = max(im.height for _a, im in rows) * scale

    sheet = Image.new("RGBA", (label_w + row_w + pad * 2,
                               head_h + len(rows) * (row_h + pad) + pad), BG)
    draw = ImageDraw.Draw(sheet)
    if title:
        draw.text((pad, 8), title, font=f_head, fill=INK)
    if note:
        draw.text((pad, 32 if title else 8), note, font=f_note, fill=ACCENT)

    y = head_h + pad
    for animation, im in rows:
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST)
        sheet.alpha_composite(big, (label_w, y))
        draw.text((pad, y + row_h // 2 - 7), animation, font=f_label, fill=MUTED)
        y += row_h + pad

    paths.ensure_dir(os.path.dirname(out_path))
    sheet.convert("RGB").save(paths.assert_writable(out_path))
    return out_path, [a for a, _im in rows], definition.get("seed")


def _wrap(draw, text, font, width, max_lines):
    """공백 기준 줄바꿈. 마지막 줄이 넘치면 … 로 자른다."""
    if not text:
        return [""]
    lines, current = [], ""
    for word in text.split(" "):
        candidate = (current + " " + word).strip()
        if current and draw.textlength(candidate, font=font) > width:
            lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
        else:
            current = candidate
    if len(lines) < max_lines and current:
        lines.append(current)
    if not lines:
        return [""]
    while draw.textlength(lines[-1] + "…", font=font) > width and len(lines[-1]) > 1:
        lines[-1] = lines[-1][:-1]
    return lines


def build(profile_dir, out_path, columns=5, cell=300, title=None, rule=None):
    items = load_characters(profile_dir)
    if not items:
        raise RuntimeError("캐릭터가 없다: %s" % paths.rel(profile_dir))
    slots = label_slots([d for _dir, d in items], rule)

    f_seed = _font(20, bold=True)
    f_arch = _font(14, bold=True)
    f_meta = _font(12, bold=False)

    pad = 12
    text_h = 62
    img_h = cell - text_h
    rows = (len(items) + columns - 1) // columns
    title_h = 58 if title else 0

    width = columns * cell + pad * (columns + 1)
    height = title_h + rows * cell + pad * (rows + 1)
    sheet = Image.new("RGBA", (width, height), BG)
    draw = ImageDraw.Draw(sheet)

    if title:
        draw.text((pad + 4, 16), title, font=_font(24, bold=True), fill=INK)
        draw.text((pad + 4, 42), "%d variations · %s"
                  % (len(items), os.path.basename(profile_dir)),
                  font=f_meta, fill=MUTED)

    for i, (cdir, definition) in enumerate(items):
        col, row = i % columns, i // columns
        x = pad + col * (cell + pad)
        y = title_h + pad + row * (cell + pad)

        draw.rounded_rectangle([x, y, x + cell, y + cell], radius=8,
                               fill=CARD, outline=BORDER, width=1)

        preview = os.path.join(cdir, definition.get("outputs", {})
                               .get("preview", {}).get("file", "preview.png"))
        if os.path.isfile(preview):
            with Image.open(preview) as im:
                thumb = im.convert("RGBA")
            scale = min((cell - 24) / float(thumb.width),
                        (img_h - 12) / float(thumb.height))
            if scale < 1.0:
                thumb = thumb.resize((max(1, int(thumb.width * scale)),
                                      max(1, int(thumb.height * scale))),
                                     Image.LANCZOS)
            elif scale >= 2.0:
                # 64px 픽셀아트 같은 작은 프리뷰는 확대해야 보인다.
                # 정수배 + NEAREST 라야 픽셀이 뭉개지지 않는다.
                factor = int(scale)
                thumb = thumb.resize((thumb.width * factor, thumb.height * factor),
                                     Image.NEAREST)
            sheet.alpha_composite(
                thumb,
                (x + (cell - thumb.width) // 2,
                 y + 8 + max(0, (img_h - 12 - thumb.height) // 2)))
        else:
            draw.text((x + 12, y + 12), "preview 없음", font=f_meta, fill=ACCENT)

        ty = y + img_h
        draw.line([x + 10, ty, x + cell - 10, ty], fill=BORDER, width=1)
        draw.text((x + 12, ty + 6), "seed %d" % definition["seed"],
                  font=f_seed, fill=INK)
        arch = definition.get("archetype", "")
        aw = draw.textlength(arch, font=f_arch)
        draw.text((x + cell - 12 - aw, ty + 11), arch, font=f_arch, fill=ACCENT)
        # 라벨은 칸 폭에 맞춰 접는다. 슬롯 이름이 긴 팩에서 잘려나가면 안 된다.
        pal = definition.get("palette", {}).get("groups", {})
        text_lines = _wrap(draw, _part_label(definition, slots), f_meta, cell - 24, 2)
        palette_line = " · ".join(pal[k] for k in sorted(pal))
        if palette_line:
            text_lines = text_lines[:1] + [palette_line]
        for i, line in enumerate(text_lines[:2]):
            draw.text((x + 12, ty + 29 + i * 16), line, font=f_meta, fill=MUTED)

    paths.ensure_dir(os.path.dirname(out_path))
    sheet.convert("RGB").save(paths.assert_writable(out_path))
    return out_path, len(items)
