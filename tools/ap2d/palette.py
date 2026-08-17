"""팔레트 로딩 + recolor.

03_PALETTES/*.json 구조는 _example_korean_90s.json 과 동일하다:
    { name, description, keys[5], ramps: [ {id, group?, colors[5]} ] }

recolor 는 multiply tint 다. 이 팩의 파츠가 흰/회색(하이라이트 239, 그림자 167,
외곽선 0) 으로만 그려져 있어서, 색을 곱하면
  - 검은 외곽선은 0 이라 그대로 검게 남고
  - 하이라이트/그림자 단계와 안티에일리어싱 그라데이션은 그대로 유지된다.
팔레트 램프의 stop 하나를 tint 색으로 뽑아 쓴다.
"""

import json
import os
import re

from PIL import Image, ImageChops

from . import paths

HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{6})$")


class PaletteError(ValueError):
    pass


def load(path):
    with open(paths.abspath(path), "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if "ramps" not in data or not data["ramps"]:
        raise PaletteError("%s: ramps 가 비어 있다" % path)
    for ramp in data["ramps"]:
        if "id" not in ramp or "colors" not in ramp:
            raise PaletteError("%s: ramp 에 id/colors 가 없다: %r" % (path, ramp))
        for color in ramp["colors"]:
            if not HEX_RE.match(color):
                raise PaletteError("%s: ramp %s 의 색상값이 #RRGGBB 가 아니다: %r"
                                   % (path, ramp["id"], color))
    data["_path"] = paths.rel(paths.abspath(path))
    data["_by_id"] = {r["id"]: r for r in data["ramps"]}
    if len(data["_by_id"]) != len(data["ramps"]):
        raise PaletteError("%s: 중복된 ramp id 가 있다" % path)
    return data


def ramp_ids(pal, group=None):
    """램프 id 목록. 정렬 없이 파일 순서를 유지한다 (규칙 파일이 순서를 통제)."""
    return [r["id"] for r in pal["ramps"] if group is None or r.get("group") == group]


def tint_color(pal, ramp_id, index):
    ramp = pal["_by_id"].get(ramp_id)
    if ramp is None:
        raise PaletteError("%s 에 ramp %r 가 없다" % (pal.get("name"), ramp_id))
    colors = ramp["colors"]
    if not 0 <= index < len(colors):
        raise PaletteError("ramp %s 의 tint_index %d 가 범위를 벗어남 (0..%d)"
                           % (ramp_id, index, len(colors) - 1))
    return hex_to_rgb(colors[index])


def hex_to_rgb(value):
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def rgb_to_hex(rgb):
    return "#%02X%02X%02X" % tuple(rgb)


def multiply_tint(image, rgb):
    """RGBA 이미지에 색을 곱한다. 알파는 그대로 둔다."""
    if image.mode != "RGBA":
        image = image.convert("RGBA")
    rgb_band = image.convert("RGB")
    solid = Image.new("RGB", image.size, tuple(rgb))
    tinted = ImageChops.multiply(rgb_band, solid)
    tinted.putalpha(image.getchannel("A"))
    return tinted
