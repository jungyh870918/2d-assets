"""Asset catalog scanner.

01_SOURCE/<domain>/<pack>/ 을 읽기 전용으로 훑어서 02_CATALOG/<pack>.json 을 만든다.

추론은 전부 경로 + 파일명 기반이다. 확신이 없으면 값을 억지로 정하지 않고
"unknown" 을 넣고 confidence 를 낮춘다. 거대한 ontology 를 만들지 않는다 —
아래 BODY_PART_VOCAB 한 장이 전부이고, 새 팩에서 안 맞으면 여기에 단어만 추가한다.

카탈로그는 타임스탬프를 담지 않는다. 같은 소스 = 같은 카탈로그 바이트여야
validator 가 소스 변조를 hash 로 잡을 수 있기 때문이다.
"""

import hashlib
import json
import os
import re

from . import TOOL_VERSION, paths

SCHEMA = "ap2d.catalog/1"

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp"}
SOURCE_EXTS = {".psd", ".psb", ".svg", ".ai", ".aseprite", ".ase", ".kra", ".xcf"}
TEXT_EXTS = {".txt", ".md", ".json", ".xml", ".url", ".rtf", ".csv"}

# 카테고리 어휘. key 는 정규화된 디렉터리/파일 토큰, value 는 정규 카테고리.
BODY_PART_VOCAB = {
    "body": "body", "bodies": "body", "torso": "body", "chest": "body",
    "head": "head", "heads": "head", "face": "head", "faces": "head",
    "hair": "hair", "hairs": "hair", "hairstyle": "hair",
    "eye": "eyes", "eyes": "eyes",
    "mouth": "mouth", "mouths": "mouth",
    "nose": "nose", "noses": "nose",
    "ear": "ear", "ears": "ear",
    "horn": "horn", "horns": "horn",
    "hand": "hand", "hands": "hand", "arm": "hand", "arms": "hand",
    "foot": "foot", "feet": "foot", "leg": "foot", "legs": "foot",
    "shoe": "foot", "shoes": "foot",
    "wing": "wing", "wings": "wing",
    "tail": "tail", "tails": "tail",
    "weapon": "weapon", "weapons": "weapon",
    "hat": "hat", "hats": "hat", "helmet": "hat", "helmets": "hat",
    "backpack": "backpack", "backpacks": "backpack", "bag": "backpack",
    "outfit": "outfit", "outfits": "outfit", "cloth": "outfit", "clothes": "outfit",
}

# asset kind 어휘. BODY_PART_VOCAB 과 **의도적으로 분리**한다.
# 여기에 chair/desk/wall/lamp 같은 단어를 넣지 않는다. 그건 카테고리 어휘가 아니라
# 개별 팩의 semantic tag 이고, 파일명이 실제로 그렇게 말해줄 때만 tags 로 들어간다.
# 이 표는 "이 파일이 무엇인지"의 큰 갈래만 가른다.
KIND_VOCAB = {
    "character": "character", "characters": "character", "char": "character",
    "chars": "character", "actor": "character", "actors": "character",
    "tileset": "tileset", "tilesets": "tileset", "tile": "tileset",
    "tiles": "tileset", "interior": "tileset", "interiors": "tileset",
    "exterior": "tileset", "exteriors": "tileset", "room": "tileset",
    "prop": "prop", "props": "prop", "object": "prop", "objects": "prop",
    "furniture": "prop",
}

# 이 갈래는 "카테고리"가 아니다. category 는 계속 BODY_PART_VOCAB 만 채운다.
# 그래야 environment 팩 단어가 character classifier 를 오염시키지 않는다.

SIDE_TOKENS = {"left": "left", "l": "left", "right": "right", "r": "right"}

# 파일명/폴더명에 박힌 타일 크기 선언: _16x16, /32x32/, 48x48
TILE_TOKEN_RE = re.compile(r"(?<![0-9a-zA-Z])(\d{1,4})x(\d{1,4})(?![0-9a-zA-Z])")

# tags 에서 걸러낼 잡음 토큰
TAG_STOPWORDS = frozenset((
    "free", "png", "new", "v", "ver", "version", "final", "copy",
))

DIRECTION_TOKENS = {
    "north": "north", "up": "north", "back": "north", "n": "north",
    "south": "south", "down": "south", "front": "south", "s": "south",
    "east": "east", "e": "east",
    "west": "west", "w": "west",
    "side": "side", "left": "west", "right": "east",
}

# <anim>_<frame>.png / <anim>-<frame>.png
FRAME_RE = re.compile(r"^(?P<anim>.+?)[ _\-](?P<frame>\d+)$")
# 후행 숫자로 끝나는 변형 이름: body1, footL1, eyes07
VARIANT_RE = re.compile(r"^(?P<stem>.*?)(?P<index>\d+)$")

_TOKEN_SPLIT = re.compile(r"[^A-Za-z0-9]+")


def _tokens(name):
    """'Left feet' -> ['left','feet'],  'footL1' -> ['foot','l','1']"""
    out = []
    for chunk in _TOKEN_SPLIT.split(name):
        if not chunk:
            continue
        # camelCase / 숫자 경계에서 한 번 더 쪼갠다
        for piece in re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]*|[a-z]+|\d+", chunk):
            out.append(piece.lower())
    return out


def _lookup_vocab(tok):
    if tok in BODY_PART_VOCAB:
        return BODY_PART_VOCAB[tok]
    # 어휘에 없으면 단수화만 시도해 본다 (약한 추론)
    if len(tok) > 3 and tok.endswith("s") and tok[:-1] in BODY_PART_VOCAB:
        return BODY_PART_VOCAB[tok[:-1]]
    return None


def _classify_category(tokens):
    """토큰 목록에서 카테고리와 confidence.

    'Left feet' 처럼 토큰이 전부 (카테고리어 | 좌우어 | 숫자) 인 경우만 strict 로 본다.
    'with hands' / 'Character Hats' 처럼 정체불명 토큰이 섞이면 어휘가 하나 걸려도
    confidence 를 낮춘다 — 완성 캐릭터 폴더가 파츠로 오분류되는 걸 막는 지점이다.
    """
    hit = None
    extras = 0
    for tok in tokens:
        found = _lookup_vocab(tok)
        if found and hit is None:
            hit = found
        elif found:
            pass  # 같은 이름이 반복되는 건 무시
        elif tok in SIDE_TOKENS or tok.isdigit():
            pass
        else:
            extras += 1
    if hit is None:
        return "unknown", 0.0
    return hit, (1.0 if extras == 0 else 0.4)


def _classify_kind_hint(path):
    """경로에서 asset kind 힌트. BODY_PART_VOCAB 과 완전히 독립이다.

    **깊은 조각부터** 본다. 파일명이 상위 폴더명보다 그 파일을 잘 설명하기 때문이다.
    'Old/mv/Character_2_16x16.png' 에서 'Old' 가 아니라 'Character' 가 이겨야 한다.
    """
    segments = TILE_TOKEN_RE.sub(" ", path).split("/")
    for segment in reversed(segments):
        for tok in _tokens(os.path.splitext(segment)[0]):
            if tok in KIND_VOCAB:
                return KIND_VOCAB[tok]
    return None


def _tile_size(pack_path):
    """경로에 선언된 타일 크기. 파일명이 폴더명보다 우선한다.

    Modern Interiors 처럼 팩이 스스로 타일 크기를 말해주는 경우가 있다
    (`Interiors_free_16x16.png`). 이건 추측이 아니라 팩이 적어둔 사실이다.
    """
    segments = pack_path.split("/")
    for segment in reversed(segments):
        matches = TILE_TOKEN_RE.findall(segment)
        if matches:
            w, h = matches[-1]
            return [int(w), int(h)]
    return None


def _scale_group_key(pack_path):
    """타일 크기 토큰을 지운 경로. 같은 내용의 배율본끼리 묶이는 키다."""
    return TILE_TOKEN_RE.sub("*", pack_path)


def _path_tags(pack_path):
    """경로에서 뽑은 원시 토큰. **의미 분류가 아니라 색인용이다.**

    파일명이 'chair' 라고 적혀 있으면 chair 가 들어가지만, 그렇다고 이 파일이
    의자라고 파이프라인이 단정하지는 않는다. 규칙 작성자가 검색할 수 있게만 해둔다.
    """
    stem = os.path.splitext(pack_path)[0]
    tags = []
    for tok in _tokens(TILE_TOKEN_RE.sub(" ", stem)):
        if tok.isdigit() or len(tok) < 2 or tok in TAG_STOPWORDS:
            continue
        if tok not in tags:
            tags.append(tok)
    return tags


def _classify_side(tokens):
    """신체/파츠의 좌우. **이동 방향의 좌우가 아니다.**

    'Left feet' 의 left 는 side 지만 'StrafeLeft' 의 Left 는 이동 방향이다.
    둘을 구분하는 근거는 같은 이름 안에 신체 파츠 어휘가 함께 있는지다.
    파츠 어휘가 없으면 그 left/right 는 side 가 아니다 — direction 쪽 의미다.
    """
    side = None
    for tok in tokens:
        if tok in SIDE_TOKENS:
            side = SIDE_TOKENS[tok]
            break
    if side is None:
        return "unknown", 0.0
    category, category_conf = _classify_category(tokens)
    if category == "unknown" or category_conf < 1.0:
        return "unknown", 0.0
    return side, 0.9


def _classify_direction(tokens):
    """방향(캐릭터가 바라보는 쪽). 이 어휘는 side 와 겹치므로 명시적 방향어만 신뢰한다."""
    strong = {"north", "south", "east", "west", "up", "down", "front", "back", "side"}
    for tok in tokens:
        if tok in strong:
            return DIRECTION_TOKENS[tok], 0.8
    return "unknown", 0.0


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


_sha256 = sha256_file   # 내부 호출 호환


def _file_type(ext):
    if ext in IMAGE_EXTS:
        return "image"
    if ext in SOURCE_EXTS:
        return "layered_source"
    if ext in TEXT_EXTS:
        return "text"
    return "other"


def _analyze_image(path):
    """치수 / 알파 / 내용 bbox. Pillow 없이 스캔하고 싶을 수 있으므로 실패는 흡수한다."""
    from PIL import Image

    with Image.open(path) as im:
        size = list(im.size)
        mode = im.mode
        has_alpha = mode in ("RGBA", "LA", "PA") or "transparency" in im.info
        bbox = None
        if has_alpha:
            rgba = im.convert("RGBA")
            bb = rgba.getbbox()
            bbox = list(bb) if bb else None
        else:
            bbox = [0, 0, size[0], size[1]]
    return {"dimensions": size, "mode": mode, "has_alpha": bool(has_alpha),
            "content_bbox": bbox}


def scan_file(abs_path, pack_root, pack_name):
    """파일 하나를 카탈로그 엔트리로."""
    relpath = os.path.relpath(abs_path, pack_root).replace(os.sep, "/")
    segments = relpath.split("/")
    filename = segments[-1]
    stem, ext = os.path.splitext(filename)
    ext = ext.lower()
    ftype = _file_type(ext)

    entry = {
        "pack": pack_name,
        "path": paths.rel(abs_path),
        "pack_path": relpath,
        "file_type": ftype,
        "bytes": os.path.getsize(abs_path),
        "sha256": _sha256(abs_path),
    }

    # ── 애니메이션 / 프레임 ────────────────────────────────────────────────
    m = FRAME_RE.match(stem)
    if m:
        animation, anim_conf = m.group("anim"), 0.9
        frame, frame_conf = int(m.group("frame")), 0.9
    else:
        animation, anim_conf = "unknown", 0.0
        frame, frame_conf = None, 0.0

    # ── part / category ──────────────────────────────────────────────────
    # 프레임 파일이면 부모 디렉터리가 part, 그 위가 category 라고 본다.
    # 아니면 파일 stem 이 part, 부모 디렉터리가 category.
    if m and len(segments) >= 2:
        part, part_conf = segments[-2], 0.9
        cat_source = segments[-3] if len(segments) >= 3 else segments[-2]
    else:
        part, part_conf = stem, 0.5
        cat_source = segments[-2] if len(segments) >= 2 else "unknown"

    cat_tokens = _tokens(cat_source)
    category, cat_conf = _classify_category(cat_tokens)
    if cat_conf < 1.0:
        # 부모 디렉터리로 확정하지 못하면 part 이름 자체를 본다.
        # 단 'body1' / 'footL1' 처럼 <어휘><좌우?><번호> 형태일 때만 인정한다.
        # 'with hands' 같은 완성본 폴더가 파츠로 새는 걸 여기서 막는다.
        vm = VARIANT_RE.match(part.strip())
        if vm:
            stem_cat, stem_conf = _classify_category(_tokens(vm.group("stem")))
            if stem_conf >= 1.0:
                category, cat_conf = stem_cat, 0.8

    side, side_conf = _classify_side(cat_tokens)
    if side == "unknown":
        side, side_conf = _classify_side(_tokens(part))

    direction, dir_conf = _classify_direction(cat_tokens + _tokens(part))

    tile_size = _tile_size(relpath)

    entry["inferred"] = {
        "group": segments[0] if len(segments) > 1 else "",
        "category": category,
        "subcategory": "/".join(segments[:-1]),
        "part": part,
        "animation": animation,
        "frame": frame,
        "direction": direction,
        "side": side,
        "tile_size": tile_size,
        # animation 을 어디서 읽었는지. sequence 파일과 animation sheet 를 구분한다.
        #   frame_sequence : walk_0.png / walk_1.png  (프레임 번호가 있음)
        #   sheet_name     : Walk.png                 (파일 하나가 애니메이션 하나)
        #   unknown        : 근거 없음
        "animation_source": "frame_sequence" if m else "unknown",
        # kind_hint 은 팩 공통 접두 폴더를 걷어낸 뒤에야 정할 수 있다 (_finalize_kinds).
        "kind_hint": None,
        # asset_kind / packaging 은 파일 하나만 봐서는 정할 수 없다.
        # 프레임 시퀀스인지 아닌지는 형제 파일들을 봐야 알 수 있어서 scan_pack 의
        # 두 번째 패스(_finalize_kinds)에서 채운다.
        "asset_kind": "unknown",
        "packaging": "unknown",
    }
    entry["confidence"] = {
        "category": cat_conf,
        "part": part_conf,
        "animation": anim_conf,
        "frame": frame_conf,
        "direction": dir_conf,
        "side": side_conf,
        "asset_kind": 0.0,
    }
    entry["tags"] = _path_tags(relpath)

    if ftype == "image":
        try:
            entry["image"] = _analyze_image(abs_path)
        except Exception as exc:  # 깨진 이미지도 카탈로그에는 남긴다
            entry["image"] = {"error": "%s: %s" % (type(exc).__name__, exc)}

    return entry


# ── 두 번째 패스: 형제 파일을 봐야 알 수 있는 것들 ──────────────────────────

def _validate_sequences(entries):
    """프레임 시퀀스인 척하는 파일을 걸러낸다.

    `Old/Tileset_16x16_1.png` 의 `_1` 은 프레임 번호가 아니라 타일셋 번호다.
    파일 하나만 보면 `walk_1.png` 와 구분되지 않는다. 구분되는 지점은 형제들이다:
    진짜 애니메이션은 0 또는 1부터 **빠짐없이 이어지는** 번호를 2장 이상 갖는다.
    Tileset 은 {1,2,3,9,16} 처럼 구멍이 뚫려 있다.

    시퀀스가 아니면 animation/frame 을 되돌리고 번호는 variant_index 로 남긴다.
    """
    groups = {}
    for entry in entries:
        inf = entry["inferred"]
        if inf["frame"] is None:
            continue
        key = (inf["subcategory"], inf["animation"])
        groups.setdefault(key, []).append(entry)

    demoted = []
    for key, members in groups.items():
        frames = sorted(e["inferred"]["frame"] for e in members)
        contiguous = (
            len(frames) >= 2
            and frames[0] in (0, 1)
            and frames == list(range(frames[0], frames[0] + len(frames)))
        )
        if contiguous:
            continue
        for entry in members:
            inf = entry["inferred"]
            inf["variant_index"] = inf["frame"]
            inf["animation"] = "unknown"
            inf["frame"] = None
            inf["animation_source"] = "unknown"
            entry["confidence"]["animation"] = 0.0
            entry["confidence"]["frame"] = 0.0
            demoted.append(entry)
    return demoted


def _promote_animation_sheets(entries, domain):
    """파일 하나가 애니메이션 하나인 팩을 인식한다 (`Walk.png`, `Attack1.png`).

    모든 PNG 파일명을 애니메이션으로 보면 안 된다. 다음 **증명된 맥락**이 모두
    갖춰졌을 때만 후보로 올린다:

      - 저장소가 이 팩을 `01_SOURCE/characters/` 에 두었다 (사람이 선언한 사실)
      - 조합 가능한 character_part 가 하나도 없다 (완성본 팩이라는 뜻)
      - 이미지가 2장 이상이고 전부 같은 캔버스다
      - 프레임 번호가 붙은 파일이 하나도 없다 (sequence 팩이 아니다)

    하나라도 어긋나면 unknown 을 유지한다. 이 판정은 **팩 단위**다 — 파일마다
    따로 추측하지 않는다. CC0 팩은 character_part 가 있으므로 애초에 들어오지 않는다.
    """
    if domain != "characters":
        return []
    images = [e for e in entries if e["file_type"] == "image"
              and "error" not in e.get("image", {})]
    if len(images) < 2:
        return []
    if any(e["inferred"]["asset_kind"] == "character_part" for e in entries):
        return []
    if any(e["inferred"]["frame"] is not None for e in images):
        return []
    if len(set(tuple(e["image"]["dimensions"]) for e in images)) != 1:
        return []

    promoted = []
    for entry in images:
        inf = entry["inferred"]
        stem = os.path.splitext(os.path.basename(entry["pack_path"]))[0]
        inf["animation"] = stem
        inf["animation_source"] = "sheet_name"
        inf["asset_kind"] = "composed_character"
        entry["confidence"]["animation"] = 0.6
        entry["confidence"]["asset_kind"] = 0.6
        promoted.append(entry)
    return promoted


def _grid_of(entry):
    """이미지가 선언된 타일 크기의 격자에 정합하는가. (cols, rows) 또는 None."""
    inf = entry["inferred"]
    tile = inf.get("tile_size")
    image = entry.get("image") or {}
    dims = image.get("dimensions")
    if not tile or not dims or "error" in image:
        return None
    if tile[0] <= 0 or tile[1] <= 0:
        return None
    if dims[0] % tile[0] or dims[1] % tile[1]:
        return None
    return (dims[0] // tile[0], dims[1] // tile[1])


def _common_prefix_segments(entries):
    """모든 파일이 공유하는 선두 디렉터리 조각.

    zip 이 팩 전체를 폴더 하나로 감싸는 일이 흔하고, 그 폴더 이름이 분류를 망친다.
    CC0 팩의 래퍼 폴더 이름은 'Free 2D Animated Vector Game Character Sprites' 라서,
    걷어내지 않으면 팩 안의 **모든** 파일이 'character' 힌트를 얻는다.
    전 파일이 공유하는 디렉터리는 파일들을 구분해주지 못하므로 분류에서 제외한다.
    """
    # 팩 루트에 바로 놓인 파일(SOURCE.md 등)은 공통 접두 계산에서 뺀다.
    # 얘들 때문에 공통 깊이가 0 이 되면 래퍼 폴더를 못 걷어낸다.
    dir_lists = [d for d in (e["pack_path"].split("/")[:-1] for e in entries) if d]
    if not dir_lists:
        return 0
    depth = 0
    while True:
        if any(depth >= len(d) for d in dir_lists):
            break
        first = dir_lists[0][depth]
        if any(d[depth] != first for d in dir_lists):
            break
        depth += 1
    return depth


def _finalize_kinds(entries):
    """asset_kind + packaging 확정. 순서가 곧 우선순위다."""
    _validate_sequences(entries)

    skip = _common_prefix_segments(entries)
    for entry in entries:
        inf = entry["inferred"]
        ftype = entry["file_type"]

        # 팩 공통 접두 폴더를 걷어낸 경로에서만 kind 힌트를 읽는다.
        distinctive = "/".join(entry["pack_path"].split("/")[skip:])
        inf["kind_hint"] = _classify_kind_hint(distinctive)

        if ftype in ("text", "other"):
            inf["asset_kind"] = "source_document"
            inf["packaging"] = "individual"
            entry["confidence"]["asset_kind"] = 1.0
            continue
        if ftype == "layered_source":
            inf["asset_kind"] = "source_document"
            inf["packaging"] = "individual"
            entry["confidence"]["asset_kind"] = 1.0
            continue

        grid = _grid_of(entry)
        if grid:
            inf["grid"] = {"columns": grid[0], "rows": grid[1],
                           "cells": grid[0] * grid[1]}
        multi_cell = bool(grid) and grid[0] * grid[1] > 1

        # packaging: sheet / sequence / individual
        if inf["frame"] is not None:
            inf["packaging"] = "sequence"
        elif multi_cell:
            inf["packaging"] = "sheet"
        else:
            inf["packaging"] = "individual"

        confident_category = (inf["category"] != "unknown"
                              and entry["confidence"]["category"] >= 0.8)

        # asset_kind 우선순위.
        # character 판정을 tileset 격자 판정보다 먼저 한다. Modern Interiors 의
        # Adam_run_16x16.png 도 16px 격자라서, 순서를 뒤집으면 캐릭터 시트가
        # environment_tile 로 넘어간다.
        if confident_category and inf["frame"] is not None:
            kind, conf = "character_part", 1.0
        elif inf["kind_hint"] == "character":
            kind, conf = "composed_character", 0.9
        elif inf["kind_hint"] == "tileset" and multi_cell:
            kind, conf = "environment_tile", 0.9
        elif inf["kind_hint"] == "prop":
            kind, conf = "prop", 0.8
        elif confident_category:
            # 파츠 어휘는 확실한데 시퀀스가 아니다 = 단품 오브젝트 이미지
            kind, conf = "prop", 0.7
        elif inf["frame"] is not None:
            kind, conf = "animation_frame", 0.6
        elif multi_cell:
            # 격자인 건 증명됐지만 무엇의 격자인지는 모른다. 추측하지 않는다.
            kind, conf = "spritesheet", 0.6
        else:
            kind, conf = "unknown", 0.0

        inf["asset_kind"] = kind
        entry["confidence"]["asset_kind"] = conf


def _mark_scale_variants(entries):
    """같은 내용의 배율본 후보를 표시한다.

    파일명의 타일 크기 토큰만 지우면 같은 경로가 되고, 치수 비율이 타일 비율과
    정확히 일치하면 배율본으로 볼 만하다. 이건 **후보**다 — 픽셀을 비교한 게
    아니므로 내용이 같다고 증명한 것은 아니다. 그 이상은 image fingerprint
    subsystem 이 필요하고, 이번 범위 밖이다.
    """
    groups = {}
    for entry in entries:
        if entry["file_type"] != "image":
            continue
        if not entry["inferred"].get("tile_size"):
            continue
        groups.setdefault(_scale_group_key(entry["pack_path"]), []).append(entry)

    found = {}
    for key, members in groups.items():
        if len(members) < 2:
            continue
        ok = []
        base = min(members, key=lambda e: e["inferred"]["tile_size"][0])
        base_tile = base["inferred"]["tile_size"][0]
        base_dims = (base.get("image") or {}).get("dimensions")
        if not base_dims:
            continue
        for entry in members:
            tile = entry["inferred"]["tile_size"][0]
            dims = (entry.get("image") or {}).get("dimensions")
            if not dims or base_tile <= 0:
                continue
            ratio = tile / float(base_tile)
            if (abs(dims[0] - base_dims[0] * ratio) < 1e-6
                    and abs(dims[1] - base_dims[1] * ratio) < 1e-6):
                ok.append(entry)
        if len(ok) < 2:
            continue
        for entry in ok:
            entry["inferred"]["scale_group"] = key
            entry["inferred"]["scale_variant_candidate"] = True
        found[key] = sorted(e["pack_path"] for e in ok)
    return found


def scan_pack(pack_root, pack_name=None, adapter=None):
    """팩 폴더 전체를 스캔해 카탈로그 dict 를 만든다. 01_SOURCE 에 쓰지 않는다.

    adapter 를 주면 경로 추론 대신 팩이 제공하는 권위 metadata 로 카탈로그를 만든다.
    팩이 스스로 슬롯/z-order/애니메이션을 선언하는 경우(LPC)에 쓴다.
    adapter 지식은 ap2d/packs/ 안에만 있고 이 함수는 위임만 한다.
    """
    pack_root = os.path.abspath(pack_root)
    if not os.path.isdir(pack_root):
        raise FileNotFoundError("팩 폴더가 없다: %s" % pack_root)
    pack_name = pack_name or os.path.basename(pack_root)

    if adapter:
        from . import packs
        return packs.get(adapter).build_catalog(pack_root, pack_name)

    entries = []
    for dirpath, dirnames, filenames in os.walk(pack_root):
        dirnames.sort()
        for name in sorted(filenames):
            if name in (".DS_Store", "Thumbs.db") or name.startswith("._"):
                continue
            entries.append(scan_file(os.path.join(dirpath, name), pack_root, pack_name))

    # 두 번째 패스: 형제 파일을 봐야 알 수 있는 것들 (시퀀스 검증, asset_kind, 배율본)
    _finalize_kinds(entries)
    domain = pack_domain(pack_root)
    _promote_animation_sheets(entries, domain)
    scale_groups = _mark_scale_variants(entries)

    parts = build_part_index(entries)
    return {
        "schema": SCHEMA,
        "tool_version": TOOL_VERSION,
        "pack": _pack_summary(pack_name, pack_root, entries, scale_groups,
                              parts, domain),
        "parts": parts,
        "entries": entries,
    }


def pack_domain(pack_root):
    """`01_SOURCE/<domain>/<pack>/` 의 domain. 저장소 규약이 선언한 사실이다.

    벤더의 파일명에서 추론한 값이 아니라 사람이 팩을 어디에 두었는지이므로,
    분류의 근거로 써도 추측이 아니다 (naming-convention.md).
    """
    rel = paths.rel(pack_root).split("/")
    if len(rel) >= 3 and rel[0] == "01_SOURCE":
        return rel[1]
    return "unknown"


# ── generation capability ──────────────────────────────────────────────────
# 지금까지 generator 는 pre_aligned / 동일 canvas / 동일 크기를 **암묵적으로** 전제했다.
# CC0 팩 하나만 볼 때는 드러나지 않던 전제다. 여기서 명시적으로 계산한다.
# 값은 라이선스 capability 와 같은 3상태다 — 증명 못 하면 "no" 가 아니라 "unknown".

YES, NO, UNKNOWN = "yes", "no", "unknown"


def _direction_axis(entries):
    """방향 축의 상태. 스키마에는 자리가 있고, 증명 못 하면 값이 unknown 이다.

    encoding 이 왜 필요한가: HD Survivor 는 방향 8개를 **시트의 행**에 담고 있어서
    파일명만 봐서는 방향이 있는지조차 알 수 없다. "파일명에서 못 찾았다"와
    "방향이 없다"는 다른 말이므로 구분해서 기록한다.
    """
    images = [e for e in entries if e["file_type"] == "image"]
    values = sorted(set(e["inferred"]["direction"] for e in images
                        if e["inferred"]["direction"] != "unknown"))
    if values:
        return {"present": YES, "encoding": "filename", "values": values}
    return {"present": UNKNOWN, "encoding": "unknown", "values": []}


def _capabilities(entries, parts, domain="unknown"):
    """generator 가 실제로 요구하는 전제를 machine-readable 하게 계산한다."""
    images = [e for e in entries
              if e["file_type"] == "image" and "error" not in e.get("image", {})]
    part_images = [e for e in images
                   if e["inferred"]["asset_kind"] == "character_part"]
    part_total = sum(len(p) for p in parts.values())

    # parts_separable: 조합할 파츠가 실제로 존재하는가
    parts_separable = YES if part_total >= 2 else NO

    # shared_canvas: 합성 대상이 될 이미지들이 한 캔버스를 쓰는가.
    # 파츠가 있으면 파츠 기준, 없으면 전체 이미지 기준으로 본다.
    population = part_images or images
    canvases = set(tuple(e["image"]["dimensions"]) for e in population)
    shared_canvas = YES if len(canvases) == 1 else (NO if canvases else UNKNOWN)

    # pre_aligned: 파츠가 같은 캔버스에 사전 정렬되어 alpha-over 만으로 합성되는가.
    # 파츠가 없으면 정렬할 대상 자체가 없다 -> 증명 불가 -> unknown.
    if not part_images:
        pre_aligned = UNKNOWN
    else:
        pre_aligned = YES if len(set(
            tuple(e["image"]["dimensions"]) for e in part_images)) == 1 else NO

    # shared_origin: 파츠가 같은 캔버스에 사전 정렬돼 있으면 원점도 공유한다.
    # 그 외에는 팩이 원점을 선언하지 않는 한 증명할 수 없다.
    shared_origin = YES if pre_aligned == YES else UNKNOWN

    # animation_compatible: 모든 파츠가 같은 애니메이션 집합을 갖는가.
    #   yes     전부 동일
    #   partial 일부 파츠가 서브셋만 지원 (겹치는 애니메이션은 있다)
    #   no      공통 애니메이션이 아예 없다
    # partial 은 합성을 막지 않는다. 미지원 애니메이션에서 그 레이어만 숨기면 된다.
    if not parts:
        animation_compatible = UNKNOWN
    else:
        sets = []
        for cat_parts in parts.values():
            for part in cat_parts.values():
                sets.append(frozenset(part["animations"]))
        if len(set(sets)) == 1:
            animation_compatible = YES
        elif set.intersection(*[set(s) for s in sets]):
            animation_compatible = "partial"
        else:
            animation_compatible = NO

    # directional: 방향 변형이 있는가.
    # 파일명에서 방향을 못 읽었다고 "방향이 없다"고 단정하지 않는다.
    # 방향이 시트의 행으로만 들어 있는 팩이 실제로 존재한다 (HD Survivor).
    directional = YES if any(
        e["inferred"]["direction"] != "unknown" for e in images) else UNKNOWN

    # composable 은 "같은 좌표에 겹칠 수 있는가" 다. 애니메이션 커버리지는
    # 파츠별 성질이라 규칙의 animation_policy 가 다루지, 합성 가능성을 막지 않는다.
    composable = YES if (parts_separable == YES
                         and pre_aligned == YES
                         and animation_compatible in (YES, "partial")) else NO

    # generation mode — export 와 compose 가 갈라지는 지점이다.
    #   modular_composition : 파츠를 골라 합성한다 (CC0)
    #   composed_sheet      : 완성 캐릭터 시트다. 파츠 교체 불가 (HD Survivor)
    #   unsupported         : 캐릭터 생성 대상이 아니다 (Modern Interiors)
    sheet_animations = [e for e in images
                        if e["inferred"]["animation_source"] == "sheet_name"]
    if composable == YES:
        mode = "modular_composition"
    elif domain == "characters" and sheet_animations:
        mode = "composed_sheet"
    else:
        mode = "unsupported"

    # origin_policy — pivot 의 근거가 무엇인가. **자동 검출은 하지 않는다.**
    #   shared_canvas : 파츠가 같은 캔버스에 사전 정렬 -> 캔버스가 곧 원점 (CC0)
    #   unknown       : 증명하지 못했다. 사람이 잰 값을 기본값으로 넣지 않는다.
    origin_policy = "shared_canvas" if pre_aligned == YES else "unknown"

    caps = {
        "parts_separable": parts_separable,
        "shared_canvas": shared_canvas,
        "pre_aligned": pre_aligned,
        "shared_origin": shared_origin,
        "animation_compatible": animation_compatible,
        "directional": directional,
        "composable": composable,
        "generation_mode": mode,
        "origin_policy": origin_policy,
    }
    if mode != "modular_composition":
        caps["reason"] = _unsupported_reason(images, parts, mode)
    return caps


def _unsupported_reason(images, parts, mode="unsupported"):
    """왜 modular composition 이 불가능한지. 어휘를 작게 유지한다."""
    if mode == "composed_sheet":
        return "composed_sheets_only"
    if parts:
        return "incompatible_parts"
    if not images:
        return "no_images"
    kinds = {}
    for e in images:
        k = e["inferred"]["asset_kind"]
        kinds[k] = kinds.get(k, 0) + 1
    if kinds.get("prop", 0) == 0 and (kinds.get("environment_tile", 0)
                                      or kinds.get("spritesheet", 0)):
        return "atlas_only_no_individual_props"
    # 파츠가 없는데 이미지들이 한 캔버스를 공유하면 완성 시트 묶음이다
    if len(set(tuple(e["image"]["dimensions"]) for e in images)) == 1:
        return "composed_sheets_only"
    return "no_modular_parts"


def _pack_summary(pack_name, pack_root, entries, scale_groups=None, parts=None,
                  domain="unknown"):
    parts = parts if parts is not None else {}
    images = [e for e in entries if e["file_type"] == "image" and "error" not in e.get("image", {})]
    modular = [e for e in images if e["inferred"]["asset_kind"] == "character_part"]

    canvas_counts = {}
    for e in images:
        key = tuple(e["image"]["dimensions"])
        canvas_counts[key] = canvas_counts.get(key, 0) + 1

    # 합성 캔버스: modular part 들이 실제로 차지하는 영역의 합집합.
    # 파츠가 사전 정렬(pre-aligned)된 팩이면 이 사각형 하나로 전 프레임을 자를 수 있다.
    def _union(acc, bb):
        if not bb:
            return acc
        if acc is None:
            return bb[:]
        return [min(acc[0], bb[0]), min(acc[1], bb[1]),
                max(acc[2], bb[2]), max(acc[3], bb[3])]

    bbox = None
    # 애니메이션별 합집합도 따로 낸다. death/roll 처럼 크게 휘두르는 동작이 전체 bbox 를
    # 캔버스 크기까지 부풀리기 때문에, idle 프리뷰를 전체 bbox 로 자르면 캐릭터가 작아진다.
    # 애니메이션 단위로 자르면 같은 애니메이션끼리는 정렬이 유지되면서 여백만 사라진다.
    per_anim = {}
    for e in modular:
        bb = e["image"].get("content_bbox")
        bbox = _union(bbox, bb)
        anim = e["inferred"]["animation"]
        per_anim[anim] = _union(per_anim.get(anim), bb)

    canvas = None
    if modular:
        sizes = set(tuple(e["image"]["dimensions"]) for e in modular)
        canvas = list(sizes.pop()) if len(sizes) == 1 else None

    kind_counts = {}
    packaging_counts = {}
    tile_counts = {}
    for e in images:
        inf = e["inferred"]
        kind_counts[inf["asset_kind"]] = kind_counts.get(inf["asset_kind"], 0) + 1
        packaging_counts[inf["packaging"]] = packaging_counts.get(inf["packaging"], 0) + 1
        if inf.get("tile_size"):
            key = "%dx%d" % tuple(inf["tile_size"])
            tile_counts[key] = tile_counts.get(key, 0) + 1

    return {
        "name": pack_name,
        "root": paths.rel(pack_root),
        "file_count": len(entries),
        "image_count": len(images),
        "modular_part_count": len(modular),
        "domain": domain,
        # generator 가 요구하는 전제. 암묵적이던 것을 명시적으로 계산한 결과다.
        "capabilities": _capabilities(entries, parts, domain),
        "direction_axis": _direction_axis(entries),
        "asset_kinds": dict(sorted(kind_counts.items())),
        "packaging": dict(sorted(packaging_counts.items())),
        "declared_tile_sizes": dict(sorted(tile_counts.items())),
        "scale_variant_groups": dict(sorted((scale_groups or {}).items())),
        # 모든 modular part 가 같은 캔버스면 pre-aligned 로 보고 단순 alpha-over 합성이 가능하다.
        "pre_aligned": canvas is not None,
        "canvas": canvas,
        "content_bbox": bbox,
        "animation_bbox": dict(sorted(per_anim.items())),
        "canvas_histogram": sorted(
            ({"dimensions": list(k), "count": v} for k, v in canvas_counts.items()),
            key=lambda d: (-d["count"], d["dimensions"]),
        ),
    }


def build_part_index(entries):
    """generator 가 실제로 쓰는 인덱스: category -> part -> {animations, files}.

    좌표축은 **(animation, direction, frame)** 이다. 다만 방향 변형이 증명되지 않은
    팩에서는 direction 축을 만들지 않는다 — 축이 하나 늘면 규칙과 generator 가 전부
    한 단계 깊어지는데, 방향이 없는 팩에서는 그게 순수한 비용이기 때문이다.
    방향이 실제로 읽힌 파츠에만 `directions` 가 추가로 붙는다.
    """
    index = {}
    for e in entries:
        inf = e["inferred"]
        if inf["asset_kind"] != "character_part":
            continue
        cat = index.setdefault(inf["category"], {})
        part = cat.setdefault(inf["part"], {
            "category": inf["category"],
            "side": inf["side"],
            "direction": inf["direction"],
            "canvas": e["image"].get("dimensions"),
            "animations": {},
        })
        frames = part["animations"].setdefault(inf["animation"], [])
        frames.append((inf["frame"], inf["direction"], e["path"]))

    for cat in index.values():
        for part in cat.values():
            total = 0
            anims = {}
            for anim, frames in part["animations"].items():
                frames.sort(key=lambda t: (t[0] if t[0] is not None else -1))
                info = {
                    "frame_count": len(frames),
                    "files": [t[2] for t in frames],
                }
                directions = sorted(set(t[1] for t in frames if t[1] != "unknown"))
                if directions:
                    # 방향이 실제로 읽힌 경우에만 축을 만든다.
                    info["directions"] = {
                        d: {"frame_count": sum(1 for t in frames if t[1] == d),
                            "files": [t[2] for t in frames if t[1] == d]}
                        for d in directions
                    }
                anims[anim] = info
                total += len(frames)
            part["animations"] = dict(sorted(anims.items()))
            part["frame_total"] = total
    return {c: dict(sorted(p.items())) for c, p in sorted(index.items())}


def write_catalog(cat, out_path):
    paths.ensure_dir(os.path.dirname(out_path))
    with open(paths.assert_writable(out_path), "w", encoding="utf-8") as fh:
        json.dump(cat, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
    return out_path


def load_catalog(path):
    with open(paths.abspath(path), "r", encoding="utf-8") as fh:
        cat = json.load(fh)
    if cat.get("schema") != SCHEMA:
        raise ValueError("카탈로그 schema 불일치: %r (기대: %r)" % (cat.get("schema"), SCHEMA))
    return cat
