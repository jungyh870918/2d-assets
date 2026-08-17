"""레이어 합성 — **modular composition 전용 엔진이다.**

## 입력 계약

이 모듈은 `generation_mode == "modular_composition"` 인 팩만 받는다.
즉 다음이 모두 참인 팩:

  - `parts_separable: yes`  — 조합할 파츠가 개별 파일로 존재한다
  - `pre_aligned: yes`      — 파츠가 같은 캔버스에 사전 정렬돼 있다
  - `animation_compatible: yes`

그 외의 팩은 `require_modular()` 가 `UnsupportedModeError` 로 즉시 막는다.
**이미 합성된 시트를 여기에 통과시키기 위한 예외 코드를 넣지 않는다.**
completed sheet 렌더러가 필요하면 별도 모듈이어야 한다. 두 종류를 한 엔진에
욱여넣으면 양쪽 다 애매해진다.

## animation_bbox 의존성

`animation_box()` 는 `pack.animation_bbox` 를 요구한다. 이 필드는 character_part
프레임들의 content bbox 합집합이라 파츠가 없는 팩에는 존재하지 않는다.
이건 CC0 팩 전용 가정이 아니라 **pre-aligned 합성 자체의 요구사항**이다 —
전 파츠가 공유하는 캔버스에서 실제 내용이 있는 사각형을 알아야 자를 수 있다.
따라서 위 입력 계약(`pre_aligned: yes`)과 정확히 같은 조건이고, 계약을 통과한
팩에서는 항상 존재한다. 계약 위반은 곁가지 KeyError 가 아니라 위에서 걸린다.
"""

import functools
import os

from PIL import Image

from . import paths, palette


MODULAR_MODE = "modular_composition"


class ComposeError(RuntimeError):
    pass


class UnsupportedModeError(ComposeError):
    """이 팩은 modular composition 엔진의 입력이 아니다.

    버그가 아니라 팩의 성질이므로, 호출한 쪽이 SKIPPED 로 다룰 수 있게
    mode 와 reason 을 들고 있는다.
    """

    def __init__(self, pack, capabilities):
        self.pack = pack
        self.capabilities = capabilities or {}
        self.mode = self.capabilities.get("generation_mode", "unknown")
        self.reason = self.capabilities.get("reason", "unknown")
        super(UnsupportedModeError, self).__init__(
            "compose 는 modular composition 전용이다. %s 는 generation_mode=%s "
            "(reason=%s) 라 입력이 될 수 없다. parts_separable=%s pre_aligned=%s"
            % (pack, self.mode, self.reason,
               self.capabilities.get("parts_separable"),
               self.capabilities.get("pre_aligned")))


def require_modular(catalog):
    """compose 계약 검사. 계약을 만족하면 capabilities 를 돌려준다."""
    caps = catalog["pack"].get("capabilities", {})
    if caps.get("generation_mode") != MODULAR_MODE:
        raise UnsupportedModeError(catalog["pack"]["name"], caps)
    return caps


@functools.lru_cache(maxsize=256)
def _load_cropped(abs_path, box):
    with Image.open(abs_path) as im:
        return im.convert("RGBA").crop(box)


def load_layer(rel_path, box):
    abs_path = paths.abspath(rel_path)
    if not os.path.isfile(abs_path):
        raise ComposeError("소스 에셋이 없다: %s" % rel_path)
    return _load_cropped(abs_path, tuple(box))


def visual_layers(catalog, category, part_name):
    """한 logical item 이 만드는 render layer 목록.

    보통은 1개다. LPC 의 땋은 머리처럼 **하나의 선택이 앞/뒤 두 레이어**를 만드는
    자산이 있어서, 이 함수가 그 차이를 흡수한다.
    반환: [(layer_index, z_pos)] — 선언 순서 그대로.
    """
    parts = catalog["parts"].get(category)
    if not parts or part_name not in parts:
        raise ComposeError("카탈로그에 %s/%s 가 없다" % (category, part_name))
    part = parts[part_name]
    out = [(0, part.get("z_pos"))]
    for layer in part.get("visual_layers") or []:
        out.append((layer["index"], layer.get("z_pos")))
    return out


def animation_info(catalog, category, part_name, animation, layer_index=0):
    parts = catalog["parts"].get(category)
    if not parts or part_name not in parts:
        raise ComposeError("카탈로그에 %s/%s 가 없다" % (category, part_name))
    part = parts[part_name]
    animations = part["animations"]
    if layer_index:
        found = None
        for layer in part.get("visual_layers") or []:
            if layer["index"] == layer_index:
                found = layer
                break
        if found is None:
            raise ComposeError("%s/%s 에 visual layer %d 가 없다"
                               % (category, part_name, layer_index))
        animations = found["animations"]
    info = animations.get(animation)
    if info is None:
        raise ComposeError("%s/%s 에 animation %r 이 없다"
                           % (category, part_name, animation))
    return info


def supports(catalog, category, part_name, animation, layer_index=0):
    """이 파츠(레이어)가 그 애니메이션을 지원하는가. 예외 없이 참/거짓만."""
    try:
        animation_info(catalog, category, part_name, animation, layer_index)
        return True
    except ComposeError:
        return False


def frame_path(catalog, category, part_name, animation, frame_index):
    """(category, part, animation, frame) -> 소스 파일 경로.

    프레임 하나가 파일 하나인 팩에서만 의미가 있다. 시트 기반 팩은 파일이 아니라
    시트 안의 셀을 가리키므로 resolve_layer() 를 쓴다.
    """
    info = animation_info(catalog, category, part_name, animation)
    files = info.get("files")
    if files is None:
        raise ComposeError("%s/%s/%s 는 시트 기반이라 프레임 파일 경로가 없다"
                           % (category, part_name, animation))
    if not 0 <= frame_index < len(files):
        raise ComposeError("%s/%s/%s 프레임 %d 가 범위를 벗어남 (0..%d)"
                           % (category, part_name, animation, frame_index, len(files) - 1))
    return files[frame_index]


# ── 레이어 resolve: 물리 배치를 논리 좌표에서 떼어내는 지점 ──────────────────
#
# compose 가 최종적으로 필요로 하는 것은 셋뿐이다: 잘린 이미지 / 캔버스 / z-order.
# 물리적으로 그 이미지를 어디서 가져오는지는 팩마다 다르다.
#
#   frame-per-file (CC0) : 파일 하나를 열어 애니메이션 bbox 로 자른다
#   sheet-cell (LPC)     : 시트 하나를 열어 (direction, frame) 셀로 자른다
#
# 어느 쪽이든 아래 compose_frame() 의 alpha-over 루프는 **같은 코드**를 탄다.
# 한쪽을 다른 쪽 구조에 맞추지 않는다.

def is_sheet_based(info):
    return "cell" in info


def layer_canvas(catalog, category, part_name, animation, layer_index=0):
    """이 레이어가 합성될 캔버스 크기 (width, height)."""
    info = animation_info(catalog, category, part_name, animation, layer_index)
    if is_sheet_based(info):
        cell = info["cell"]
        return (cell["width"], cell["height"])
    box = animation_box(catalog, animation)
    return (box[2] - box[0], box[3] - box[1])


def directions_for(catalog, category, part_name, animation, layer_index=0):
    """이 애니메이션이 갖는 방향 목록. 방향 개념이 없으면 빈 리스트."""
    info = animation_info(catalog, category, part_name, animation, layer_index)
    return list(info.get("directions") or [])


def resolve_layer(catalog, category, part_name, animation, frame_index,
                  direction=None, box=None, layer_index=0):
    """논리 좌표 (slot, asset, layer, animation, direction, frame) -> 잘린 RGBA 이미지."""
    info = animation_info(catalog, category, part_name, animation, layer_index)
    if is_sheet_based(info):
        return _resolve_cell(info, category, part_name, animation,
                             frame_index, direction)
    path = frame_path(catalog, category, part_name, animation, frame_index)
    crop = tuple(box) if box else animation_box(catalog, animation)
    return load_layer(path, crop), path


def _resolve_cell(info, category, part_name, animation, frame_index, direction):
    cell = info["cell"]
    directions = list(info.get("directions") or [])
    if directions:
        if direction is None:
            raise ComposeError(
                "%s/%s/%s 는 방향이 %d개다. direction 을 지정해야 한다 (%s)"
                % (category, part_name, animation, len(directions),
                   ", ".join(directions)))
        if direction not in directions:
            raise ComposeError("%s/%s/%s 에 방향 %r 이 없다 (있는 것: %s)"
                               % (category, part_name, animation, direction,
                                  ", ".join(directions)))
        row = directions.index(direction)
    else:
        row = 0
    if not 0 <= frame_index < info["frame_count"]:
        raise ComposeError("%s/%s/%s 프레임 %d 가 범위를 벗어남 (0..%d)"
                           % (category, part_name, animation, frame_index,
                              info["frame_count"] - 1))
    x0 = frame_index * cell["width"]
    y0 = row * cell["height"]
    crop = (x0, y0, x0 + cell["width"], y0 + cell["height"])
    return load_layer(info["sheet"], crop), info["sheet"]


def animation_box(catalog, animation):
    box = catalog["pack"].get("animation_bbox", {}).get(animation)
    if box is None:
        box = catalog["pack"].get("content_bbox")
    if box is None:
        raise ComposeError("카탈로그에 %r 의 bbox 정보가 없다" % animation)
    return tuple(box)


def union_box(catalog, animations):
    """여러 애니메이션이 공유할 하나의 crop 사각형.

    애니메이션마다 제 bbox 로 자르면 셀 크기와 원점이 달라져서, Unity 에서
    idle -> walk 로 넘어갈 때 캐릭터 크기가 변하고 발 위치가 튄다.
    시트로 내보내는 애니메이션들은 반드시 같은 사각형으로 잘라야 한다.
    """
    acc = None
    for anim in animations:
        box = animation_box(catalog, anim)
        acc = list(box) if acc is None else [
            min(acc[0], box[0]), min(acc[1], box[1]),
            max(acc[2], box[2]), max(acc[3], box[3]),
        ]
    if acc is None:
        raise ComposeError("애니메이션 목록이 비어 있다")
    return tuple(acc)


def frame_count(catalog, category, part_name, animation, layer_index=0):
    info = animation_info(catalog, category, part_name, animation, layer_index)
    if "frame_count" in info:
        return info["frame_count"]
    return len(info["files"])


def compose_frame(catalog, layers, animation, frame_index, size=None,
                  background=None, box=None, direction=None):
    """layers: [(slot, category, part, tint_rgb_or_None)] 를 z-order 순으로.

    **이 루프가 generic composition path 다.** CC0(프레임 파일)든 LPC(시트 셀)든
    resolve_layer() 가 잘린 이미지를 돌려주고 나면 이후는 완전히 같은 코드다.

    box 는 프레임 파일 기반 팩에서 여러 애니메이션의 정렬을 맞출 때만 쓴다.
    direction 은 방향 축이 있는 팩에서 필요하다.
    """
    if not layers:
        raise ComposeError("합성할 레이어가 없다")
    layers = [_normalize(l) for l in layers]
    # 캔버스는 이 애니메이션을 **지원하는** 레이어에서 잡는다.
    first = next((l for l in layers
                  if supports(catalog, l[1], l[2], animation, l[4])), None)
    if first is None:
        raise ComposeError("animation %r 을 지원하는 레이어가 하나도 없다" % animation)
    canvas_size = layer_canvas(catalog, first[1], first[2], animation, first[4])
    if box and not is_sheet_based(
            animation_info(catalog, first[1], first[2], animation, first[4])):
        box = tuple(box)
        canvas_size = (box[2] - box[0], box[3] - box[1])
    else:
        box = None

    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    used = []
    for slot, category, part_name, tint, layer_index in layers:
        # 이 파츠가 이 애니메이션을 지원하지 않으면 그 레이어만 건너뛴다.
        # 나머지 레이어는 그대로 합성된다 — runtime 의 hide_layer 와 같은 규칙이다.
        if not supports(catalog, category, part_name, animation, layer_index):
            continue
        layer, source = resolve_layer(catalog, category, part_name, animation,
                                      frame_index, direction=direction, box=box,
                                      layer_index=layer_index)
        if layer.size != canvas.size:
            raise ComposeError(
                "레이어 캔버스 불일치: %s/%s %s vs %s — 같은 좌표로 겹칠 수 없다"
                % (category, part_name, layer.size, canvas.size))
        if tint is not None:
            layer = palette.multiply_tint(layer, tint)
        canvas.alpha_composite(layer)
        used.append(source)

    if size:
        canvas = _fit(canvas, size)
    if background:
        flat = Image.new("RGBA", canvas.size, background)
        flat.alpha_composite(canvas)
        canvas = flat
    return canvas, used


def _fit(image, size):
    """가로세로 비율을 유지한 채 size x size 상자 안에 들어가게 축소."""
    w, h = image.size
    scale = min(size / float(w), size / float(h))
    if scale >= 1.0:
        return image
    return image.resize((max(1, int(round(w * scale))), max(1, int(round(h * scale)))),
                        Image.LANCZOS)


def _normalize(entry):
    """레이어 튜플을 (slot, category, part, tint, layer_index) 5원소로 맞춘다.

    기존 호출부는 4원소를 넘긴다. multi-layer 자산이 생기면서 5번째가 필요해졌고,
    기본값 0 을 넣어 기존 호출을 그대로 둔다.
    """
    if len(entry) == 5:
        return tuple(entry)
    slot, category, part_name, tint = entry
    return (slot, category, part_name, tint, 0)


def compose_sheet(catalog, layers, animation, size=None, background=None,
                  box=None, direction=None):
    """애니메이션 전 프레임을 가로로 이어붙인 스프라이트 시트.

    box 는 같이 내보내는 애니메이션들이 공유하는 사각형이어야 한다 (union_box).
    direction 은 방향 축이 있는 팩에서 어느 방향을 구울지 정한다.
    """
    norm = [_normalize(l) for l in layers]
    ref = next((l for l in norm if supports(catalog, l[1], l[2], animation, l[4])), None)
    if ref is None:
        raise ComposeError("animation %r 을 지원하는 레이어가 하나도 없다" % animation)
    count = frame_count(catalog, ref[1], ref[2], animation, ref[4])
    frames = []
    used = set()
    for i in range(count):
        img, paths_used = compose_frame(catalog, layers, animation, i, size=size,
                                        box=box, direction=direction)
        frames.append(img)
        used.update(paths_used)
    cell_w = max(f.width for f in frames)
    cell_h = max(f.height for f in frames)
    sheet = Image.new("RGBA", (cell_w * count, cell_h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        # 프레임은 이미 정렬된 bbox 기준이라 셀 안에서 왼쪽 위에 붙여도 흔들리지 않는다.
        sheet.alpha_composite(f, (i * cell_w, 0))
    if background:
        flat = Image.new("RGBA", sheet.size, background)
        flat.alpha_composite(sheet)
        sheet = flat
    return sheet, sorted(used), {"frame_count": count,
                                 "cell_size": [cell_w, cell_h]}


def clear_cache():
    _load_cropped.cache_clear()
