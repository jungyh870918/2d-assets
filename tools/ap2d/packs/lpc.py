"""Universal LPC Spritesheet Character Generator 팩 adapter.

**이 파일이 LPC 지식의 유일한 보관 장소다.** 다른 모듈에 LPC 분기를 만들지 않는다.

## 왜 adapter 가 필요한가

LPC 는 경로 규칙이 일정하지 않다 (깊이 3~9, 애니메이션 토큰 위치가 제각각):

    body/bodies/<bodytype>/<animation>.png
    hair/<style>/<age>/<animation>.png
    torso/<cat>/<item>/<bodytype>/<animation>/<color>.png

그래서 generic scanner 는 100% unknown 으로 떨어진다. 대신 LPC 는 권위 있는
metadata 를 직접 제공한다:

    sheet_definitions/**/*.json   슬롯(type_name) / zPos / 애니메이션 목록 /
                                  body type 별 경로 / recolor / credits
    CREDITS.csv                   파일 단위 저자·라이선스·URL

추론보다 이쪽이 정확하다. 사람이 실측해야 했던 z-order 조차 선언되어 있다.

## physical layout != logical topology

LPC 는 PNG 하나가 프레임 하나가 아니라 **(direction × frame) 시트**다.
셀 크기 64x64 는 이 팩의 상수이므로 adapter metadata 로 선언한다.
알파 간격 분석이나 자동 격자 검출을 하지 않는다.

    walk : 576x256 -> 9 frame x 4 direction
    run  : 512x256 -> 8 frame x 4 direction
    idle : 128x256 -> 2 frame x 4 direction

방향 수는 전역 상수가 아니다 (hurt/climb 는 1방향). 그래서 방향은 **애니메이션별**
topology 로 기록한다. Phase 1 은 4방향 애니메이션만 쓰지만 모델은 축을 잃지 않는다.
"""

import csv
import json
import os

from .. import TOOL_VERSION, paths

NAME = "lpc"

# ── 팩 상수 (선언값. 검출하지 않는다) ──────────────────────────────────────
CELL = 64
# LPC 표준 행 순서: up / left / down / right
DIRECTION_ROWS = ("north", "west", "south", "east")

# LPC 의 type_name -> 이 저장소의 슬롯 이름
SLOT_BY_TYPE = {
    "body": "body",
    "head": "head",
    "hair": "hair",
    "clothes": "torso",
    "legs": "legs",
    "shoes": "feet",
}

# Phase 1 이 지원하는 애니메이션과 그 표준 시트 규격.
# 규격을 명시해 두면 비표준(oversize/128px) asset 이 조용히 섞이지 않는다.
PHASE1_ANIMATIONS = {
    "idle": {"frames": 2, "directions": 4},
    "walk": {"frames": 9, "directions": 4},
    "run": {"frames": 8, "directions": 4},
}

# 라이선스 성질. 파일 단위로 판정한다.
SHARE_ALIKE_PREFIXES = ("CC-BY-SA", "OGA-SA")
COPYLEFT_PREFIXES = ("GPL",)


class LpcError(RuntimeError):
    pass


# ── 라이선스 ───────────────────────────────────────────────────────────────

def pick_license(licenses):
    """다중 라이선스 중 이 저장소 정책상 가장 적절한 것을 **명시적으로** 고른다.

    우선순위: CC0 > OGA-BY > CC-BY. share-alike 나 GPL 만 있으면 None.
    문자열을 그대로 복사하지 않고 '무엇을 골랐는지'를 기록에 남긴다.
    """
    values = [str(x).strip() for x in (licenses or []) if str(x).strip()]
    for value in values:
        if value.startswith("CC0"):
            return value
    for value in values:
        if value.startswith("OGA-BY"):
            return value
    for value in values:
        if value.startswith("CC-BY") and not value.startswith("CC-BY-SA"):
            return value
    return None


def is_share_alike(value):
    return str(value).strip().startswith(SHARE_ALIKE_PREFIXES)


def scoped_credits(definition, base_path):
    """실제로 쓰는 경로에 해당하는 credits 항목만 고른다.

    LPC 의 body 정의는 male/female/muscular/... 의 credits 를 한꺼번에 담는데,
    male 만 쓰는데도 muscular 가 share-alike 라는 이유로 전체를 탈락시키면 안 된다.
    라이선스는 **실제 사용하는 파일** 기준이다.
    """
    base = base_path.rstrip("/")
    hits = []
    for credit in definition.get("credits") or []:
        target = (credit.get("file") or "").rstrip("/")
        if not target:
            continue
        if base.startswith(target) or target.startswith(base):
            hits.append(credit)
    return hits or list(definition.get("credits") or [])


def credit_record(credit, source_root=""):
    """credits 항목 하나를 우리 attribution 모델로 정규화."""
    licenses = [str(x).strip() for x in (credit.get("licenses") or []) if str(x).strip()]
    selected = pick_license(licenses)
    return {
        "source_file": credit.get("file") or "",
        "authors": [a.strip() for a in (credit.get("authors") or []) if str(a).strip()],
        "selected_license": selected,
        "alternative_licenses": [l for l in licenses if l != selected],
        "source_urls": [u.strip() for u in (credit.get("urls") or []) if str(u).strip()],
        "attribution_required": bool(selected) and not selected.startswith("CC0"),
        "share_alike_required": any(is_share_alike(l) for l in licenses) and not selected,
        "notes": (credit.get("notes") or "").strip(),
    }


# ── sheet_definitions 읽기 ────────────────────────────────────────────────

def load_definitions(pack_root):
    """sheet_definitions/**/*.json 전체를 경로순으로. 순서가 곧 결정성이다."""
    root = os.path.join(pack_root, "sheet_definitions")
    if not os.path.isdir(root):
        raise LpcError("sheet_definitions 가 없다: %s" % paths.rel(root))
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if not name.endswith(".json"):
                continue
            full = os.path.join(dirpath, name)
            with open(full, "r", encoding="utf-8") as fh:
                try:
                    data = json.load(fh)
                except ValueError as exc:
                    raise LpcError("정의 JSON 파싱 실패 %s: %s" % (full, exc))
            out.append((os.path.relpath(full, pack_root).replace(os.sep, "/"), data))
    return out


def definition_id(rel_path):
    """정의 파일 경로에서 안정적인 asset id. 표시 이름(공백 포함)을 키로 쓰지 않는다."""
    return os.path.splitext(os.path.basename(rel_path))[0]


def sheet_path(pack_root, base, animation):
    return os.path.join(pack_root, "spritesheets", base.replace("/", os.sep),
                        animation + ".png")


# ── subset 선택 ───────────────────────────────────────────────────────────

SELECTION_CRITERIA = [
    "type_name 이 이 저장소의 슬롯(body/head/hair/torso/legs/feet)에 대응한다",
    "layer_ 키가 정확히 1개다 (다중 zPos 아이템은 Phase 1 에서 제외)",
    "layer_1 에 male 경로가 있다 (body type 은 male 하나만 사용)",
    "custom_animation 이 없다",
    "animations 가 idle/walk/run 을 모두 포함한다",
    "idle/walk/run 시트가 <base><animation>.png 형태로 실재한다",
    "세 시트 모두 표준 64px 격자 규격이다 (idle 2x4 / walk 9x4 / run 8x4)",
    "실제 사용 경로의 credits 가 전부 CC0 / OGA-BY / CC-BY 중 하나를 제공한다",
    "위를 만족하는 후보를 정의 파일 경로순으로 정렬해 슬롯별 목표 수만큼 앞에서 취한다",
]

DEFAULT_SUBSET = {"body": 1, "head": 2, "hair": 4, "torso": 4, "legs": 3, "feet": 3}

# Phase 2 에서 **의도적으로** 들여오는 예외 자산. Phase 1 필터가 걸러내던 두 종류를
# 각각 하나씩만 넣어 실제 자산으로 검증한다. 수를 늘리지 않는다.
PHASE2_EXTRAS = {
    # 한 logical item 이 여러 zPos 를 갖는 자산 (앞/뒤 레이어)
    "multi_layer": 1,
    # 일부 애니메이션만 지원하는 자산 (hide_layer 정책 실검증용)
    "animation_subset": 1,
}

EXTRA_CRITERIA = [
    "multi_layer: layer_ 키가 2개 이상이고 각 레이어가 제 zPos 를 갖는다",
    "multi_layer: Phase 1 슬롯에 매핑되고 idle/walk/run 을 모두 지원한다",
    "animation_subset: layer_ 가 1개이고 idle/walk/run 중 일부만 지원한다",
    "animation_subset: 최소 1개는 지원하고 최소 1개는 미지원이어야 한다",
    "animation_subset: body 슬롯은 제외한다 — 몸통이 숨겨지면 "
    "'해당 레이어만 사라지고 나머지는 계속 재생' 을 검증할 수 없다",
    "공통: male 경로 · custom_animation 없음 · 표준 64px 격자 · 허용 라이선스",
    "공통: 조건을 만족하는 후보를 정의 파일 경로순으로 정렬해 앞에서 취한다",
]


def _sheet_grid(path, animation):
    """시트 규격이 Phase 1 표준과 맞는지. Pillow 로 크기만 본다."""
    from PIL import Image

    spec = PHASE1_ANIMATIONS[animation]
    with Image.open(path) as im:
        width, height = im.size
    if width % CELL or height % CELL:
        return None
    columns, rows = width // CELL, height // CELL
    if columns != spec["frames"] or rows != spec["directions"]:
        return None
    return {"width": CELL, "height": CELL, "columns": columns, "rows": rows}


def _layer_bases(data):
    """layer_1, layer_2 ... 를 선언 순서대로 (키, male 경로, zPos)."""
    out = []
    for key in sorted((k for k in data if k.startswith("layer_")),
                      key=lambda k: int(k.split("_")[1])):
        layer = data[key]
        if isinstance(layer, dict) and layer.get("male"):
            out.append((key, layer["male"], layer.get("zPos")))
    return out


def _asset_record(rel_path, data, bases, grids_by_layer, credits, animations):
    return {
        "id": definition_id(rel_path),
        "name": data.get("name") or definition_id(rel_path),
        "slot": SLOT_BY_TYPE[data["type_name"]],
        "type_name": data.get("type_name"),
        "definition": rel_path,
        "base": bases[0][1],
        "z_pos": bases[0][2],
        "body_type": "male",
        "animations": grids_by_layer[0],
        # 레이어가 2개 이상일 때만 채운다. 단일 레이어 자산의 카탈로그 모양을 바꾸지 않는다.
        "visual_layers": ([{"index": i, "base": base, "z_pos": z,
                            "animations": grids_by_layer[i]}
                           for i, (_k, base, z) in enumerate(bases)]
                          if len(bases) > 1 else None),
        "supported_animations": sorted(animations),
        "recolors": data.get("recolors"),
        "credits": credits,
    }


def evaluate_extras(pack_root, definitions=None):
    """Phase 2 예외 자산 후보. 기준은 EXTRA_CRITERIA 에 적어 둔 것과 같다."""
    definitions = definitions if definitions is not None else load_definitions(pack_root)
    multi, subset = [], []

    for rel_path, data in definitions:
        if SLOT_BY_TYPE.get(data.get("type_name")) is None:
            continue
        bases = _layer_bases(data)
        if not bases:
            continue
        if any((data[k].get("custom_animation")) for k, _b, _z in bases):
            continue
        if any(z is None for _k, _b, z in bases):
            continue

        grids_by_layer = []
        supported = None
        ok = True
        for _key, base, _z in bases:
            grids = {}
            for animation in sorted(PHASE1_ANIMATIONS):
                path = sheet_path(pack_root, base, animation)
                if not os.path.isfile(path):
                    continue
                grid = _sheet_grid(path, animation)
                if grid is None:
                    ok = False
                    break
                grids[animation] = grid
            if not ok:
                break
            grids_by_layer.append(grids)
            names = set(grids)
            supported = names if supported is None else (supported & names)
        if not ok or not supported:
            continue

        scoped = scoped_credits(data, bases[0][1])
        credits = [credit_record(c) for c in scoped]
        if not credits or any(c["selected_license"] is None for c in credits):
            continue

        record = _asset_record(rel_path, data, bases, grids_by_layer, credits, supported)
        if len(bases) > 1 and supported == set(PHASE1_ANIMATIONS):
            multi.append(record)
        elif (len(bases) == 1 and 0 < len(supported) < len(PHASE1_ANIMATIONS)
              and record["slot"] != "body"):
            # body 는 제외한다. 몸통이 사라지면 hide_layer 정책의 핵심 주장
            # ("나머지 레이어는 계속 애니메이션한다") 자체를 확인할 수 없다.
            subset.append(record)

    multi.sort(key=lambda r: r["definition"])
    subset.sort(key=lambda r: r["definition"])
    return {"multi_layer": multi, "animation_subset": subset}


def evaluate(pack_root, definitions=None):
    """모든 정의를 기준에 걸어 (후보, 탈락사유) 를 만든다. 순수 계산이라 결정적이다."""
    definitions = definitions if definitions is not None else load_definitions(pack_root)
    candidates = {slot: [] for slot in sorted(set(SLOT_BY_TYPE.values()))}
    rejected = []

    for rel_path, data in definitions:
        slot = SLOT_BY_TYPE.get(data.get("type_name"))
        if slot is None:
            continue
        reason = None
        layer_keys = sorted(k for k in data if k.startswith("layer_"))
        base = None
        if len(layer_keys) != 1:
            reason = "multi_layer"
        else:
            layer = data[layer_keys[0]]
            base = layer.get("male")
            if not base:
                reason = "no_male_body_type"
            elif layer.get("custom_animation"):
                reason = "custom_animation"
            elif not set(PHASE1_ANIMATIONS) <= set(data.get("animations") or []):
                reason = "animation_subset"
        grids = {}
        if reason is None:
            for animation in sorted(PHASE1_ANIMATIONS):
                path = sheet_path(pack_root, base, animation)
                if not os.path.isfile(path):
                    reason = "sheet_missing"
                    break
                grid = _sheet_grid(path, animation)
                if grid is None:
                    reason = "nonstandard_topology"
                    break
                grids[animation] = grid
        credits = []
        if reason is None:
            scoped = scoped_credits(data, base)
            credits = [credit_record(c) for c in scoped]
            if not credits or any(c["selected_license"] is None for c in credits):
                reason = "license_not_permissive"

        if reason is not None:
            rejected.append({"definition": rel_path, "slot": slot, "reason": reason})
            continue

        candidates[slot].append({
            "id": definition_id(rel_path),
            "name": data.get("name") or definition_id(rel_path),
            "slot": slot,
            "type_name": data.get("type_name"),
            "definition": rel_path,
            "base": base,
            "z_pos": data[layer_keys[0]].get("zPos"),
            "body_type": "male",
            "animations": {a: grids[a] for a in sorted(grids)},
            "recolors": data.get("recolors"),
            "credits": credits,
        })

    for slot in candidates:
        candidates[slot].sort(key=lambda item: item["definition"])
    return candidates, rejected


def select_subset(pack_root, targets=None, definitions=None, extras=None):
    """기준을 만족하는 후보를 경로순으로 정렬해 슬롯별 목표 수만큼 취한다.

    extras 를 주면 Phase 2 예외 자산(multi_layer / animation_subset)도 함께 고른다.
    예외 자산은 해당 슬롯의 목록에 **추가**된다 — 별도 슬롯을 만들지 않는다.
    """
    targets = targets or DEFAULT_SUBSET
    definitions = definitions if definitions is not None else load_definitions(pack_root)
    candidates, rejected = evaluate(pack_root, definitions)
    chosen = {}
    shortfall = {}
    for slot in sorted(targets):
        want = targets[slot]
        have = candidates.get(slot, [])
        chosen[slot] = have[:want]
        if len(chosen[slot]) < want:
            shortfall[slot] = {"wanted": want, "got": len(chosen[slot])}

    extra_selection = {}
    if extras:
        pools = evaluate_extras(pack_root, definitions)
        for kind in sorted(extras):
            picked = pools.get(kind, [])[:extras[kind]]
            extra_selection[kind] = picked
            if len(picked) < extras[kind]:
                shortfall[kind] = {"wanted": extras[kind], "got": len(picked)}
            for record in picked:
                bucket = chosen.setdefault(record["slot"], [])
                if all(r["id"] != record["id"] for r in bucket):
                    bucket.append(record)
        for slot in chosen:
            chosen[slot].sort(key=lambda r: r["definition"])

    return {
        "adapter": NAME,
        "tool_version": TOOL_VERSION,
        "cell": CELL,
        "direction_rows": list(DIRECTION_ROWS),
        "animations": {a: dict(PHASE1_ANIMATIONS[a]) for a in sorted(PHASE1_ANIMATIONS)},
        "body_type": "male",
        "criteria": list(SELECTION_CRITERIA) + (list(EXTRA_CRITERIA) if extras else []),
        "targets": dict(targets),
        "extra_targets": dict(extras or {}),
        "extras": {k: [r["id"] for r in v] for k, v in sorted(extra_selection.items())},
        "selected": chosen,
        "candidate_counts": {s: len(v) for s, v in sorted(candidates.items())},
        "rejected_counts": _count_reasons(rejected),
        "shortfall": shortfall,
    }


def _count_reasons(rejected):
    out = {}
    for item in rejected:
        out[item["reason"]] = out.get(item["reason"], 0) + 1
    return dict(sorted(out.items()))


# ── 카탈로그 생성 ─────────────────────────────────────────────────────────

def _animation_block(pack_root, base, animation, grid):
    abs_sheet = sheet_path(pack_root, base, animation)
    return paths.rel(abs_sheet), {
        "frame_count": grid["columns"],
        "directions": list(DIRECTION_ROWS[:grid["rows"]]),
        "sheet": paths.rel(abs_sheet),
        "cell": dict(grid),
    }


def build_catalog(pack_root, pack_name, subset=None):
    """선택된 subset 으로 **표준 카탈로그 스키마**를 만든다.

    새 스키마를 만들지 않는다. 다른 점은 애니메이션 정보가 파일 목록 대신
    `sheet` + `cell` + `directions` 를 갖는다는 것뿐이고, compose 가 그 둘을
    같은 방식으로 resolve 한다.
    """
    from ..catalog import SCHEMA, sha256_file

    pack_root = os.path.abspath(pack_root)
    # 예외 자산도 후보에 넣는다. 시트가 팩 폴더에 없으면 선택 단계에서 걸러지므로,
    # 결과는 항상 "이 팩 폴더에 실제로 있는 것" 과 일치한다.
    subset = subset or select_subset(pack_root, extras=PHASE2_EXTRAS)

    entries = []
    parts = {}
    for slot in sorted(subset["selected"]):
        for asset in subset["selected"][slot]:
            part = {
                "category": slot,
                "name": asset["name"],
                "side": "unknown",
                "direction": "unknown",
                "canvas": [CELL, CELL],
                "z_pos": asset["z_pos"],
                "body_type": asset["body_type"],
                "definition": asset["definition"],
                "recolors": asset["recolors"],
                "credits": asset["credits"],
                "animations": {},
            }
            # 레이어가 2개 이상인 logical item 은 VisualLayer 배열로 표현한다.
            # 하나의 선택이 여러 render layer 를 만드는 구조다.
            if asset.get("visual_layers"):
                extra = []
                for layer in asset["visual_layers"][1:]:
                    anims = {}
                    for animation in sorted(layer["animations"]):
                        _rel, block = _animation_block(
                            pack_root, layer["base"], animation,
                            layer["animations"][animation])
                        anims[animation] = block
                    extra.append({"index": layer["index"], "z_pos": layer["z_pos"],
                                  "animations": anims})
                part["visual_layers"] = extra
            part["supported_animations"] = list(asset.get("supported_animations")
                                                or sorted(asset["animations"]))

            total = 0
            for animation in sorted(asset["animations"]):
                grid = asset["animations"][animation]
                abs_sheet = sheet_path(pack_root, asset["base"], animation)
                rel_sheet = paths.rel(abs_sheet)
                directions = list(DIRECTION_ROWS[:grid["rows"]])
                part["animations"][animation] = {
                    "frame_count": grid["columns"],
                    "directions": directions,
                    "sheet": rel_sheet,
                    "cell": dict(grid),
                }
                total += grid["columns"] * grid["rows"]
                entries.append({
                    "pack": pack_name,
                    "path": rel_sheet,
                    "pack_path": os.path.relpath(abs_sheet, pack_root).replace(os.sep, "/"),
                    "file_type": "image",
                    "bytes": os.path.getsize(abs_sheet),
                    "sha256": sha256_file(abs_sheet),
                    "inferred": {
                        "group": "spritesheets",
                        "category": slot,
                        "subcategory": asset["base"].rstrip("/"),
                        "part": asset["id"],
                        "animation": animation,
                        "frame": None,
                        "direction": "multi",
                        "side": "unknown",
                        "tile_size": [CELL, CELL],
                        "kind_hint": "character",
                        "animation_source": "declared_metadata",
                        "asset_kind": "character_part",
                        "packaging": "sheet",
                        "grid": {"columns": grid["columns"], "rows": grid["rows"],
                                 "cells": grid["columns"] * grid["rows"]},
                    },
                    "confidence": {
                        "category": 1.0, "part": 1.0, "animation": 1.0,
                        "frame": 0.0, "direction": 1.0, "side": 0.0,
                        "asset_kind": 1.0,
                    },
                    "tags": [slot, asset["id"], animation],
                    "image": {"dimensions": [grid["columns"] * CELL, grid["rows"] * CELL],
                              "mode": "RGBA", "has_alpha": True, "content_bbox": None},
                })
            for layer in (part.get("visual_layers") or []):
                for animation, block in sorted(layer["animations"].items()):
                    abs_extra = paths.abspath(block["sheet"])
                    entries.append({
                        "pack": pack_name,
                        "path": block["sheet"],
                        "pack_path": os.path.relpath(abs_extra, pack_root).replace(os.sep, "/"),
                        "file_type": "image",
                        "bytes": os.path.getsize(abs_extra),
                        "sha256": sha256_file(abs_extra),
                        "inferred": {
                            "group": "spritesheets", "category": slot,
                            "subcategory": os.path.dirname(block["sheet"]),
                            "part": asset["id"], "animation": animation, "frame": None,
                            "direction": "multi", "side": "unknown",
                            "tile_size": [CELL, CELL], "kind_hint": "character",
                            "animation_source": "declared_metadata",
                            "asset_kind": "character_part", "packaging": "sheet",
                            "visual_layer": layer["index"],
                            "grid": {"columns": block["cell"]["columns"],
                                     "rows": block["cell"]["rows"],
                                     "cells": block["cell"]["columns"] * block["cell"]["rows"]},
                        },
                        "confidence": {"category": 1.0, "part": 1.0, "animation": 1.0,
                                       "frame": 0.0, "direction": 1.0, "side": 0.0,
                                       "asset_kind": 1.0},
                        "tags": [slot, asset["id"], animation],
                        "image": {"dimensions": [block["cell"]["columns"] * CELL,
                                                 block["cell"]["rows"] * CELL],
                                  "mode": "RGBA", "has_alpha": True, "content_bbox": None},
                    })
            part["frame_total"] = total
            parts.setdefault(slot, {})[asset["id"]] = part

    # 메타데이터 파일도 카탈로그에 기록한다 (소스 불변 검사 대상이 되어야 한다)
    for rel_meta in _metadata_files(pack_root):
        abs_meta = os.path.join(pack_root, rel_meta)
        entries.append({
            "pack": pack_name,
            "path": paths.rel(abs_meta),
            "pack_path": rel_meta,
            "file_type": "text",
            "bytes": os.path.getsize(abs_meta),
            "sha256": sha256_file(abs_meta),
            "inferred": {
                "group": rel_meta.split("/")[0], "category": "unknown",
                "subcategory": os.path.dirname(rel_meta), "part": os.path.basename(rel_meta),
                "animation": "unknown", "frame": None, "direction": "unknown",
                "side": "unknown", "tile_size": None, "kind_hint": None,
                "animation_source": "unknown", "asset_kind": "source_document",
                "packaging": "individual",
            },
            "confidence": {"category": 0.0, "part": 1.0, "animation": 0.0,
                           "frame": 0.0, "direction": 0.0, "side": 0.0,
                           "asset_kind": 1.0},
            "tags": [],
        })

    entries.sort(key=lambda e: e["path"])
    parts = {c: dict(sorted(p.items())) for c, p in sorted(parts.items())}

    return {
        "schema": SCHEMA,
        "tool_version": TOOL_VERSION,
        "pack": _pack_block(pack_name, pack_root, entries, parts, subset),
        "parts": parts,
        "entries": entries,
    }


def _metadata_files(pack_root):
    out = []
    for rel in ("CREDITS.csv", "LICENSE", "SOURCE.md"):
        if os.path.isfile(os.path.join(pack_root, rel)):
            out.append(rel)
    root = os.path.join(pack_root, "sheet_definitions")
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            if name.endswith(".json"):
                full = os.path.join(dirpath, name)
                out.append(os.path.relpath(full, pack_root).replace(os.sep, "/"))
    return out


def _pack_block(pack_name, pack_root, entries, parts, subset):
    animations = {}
    for slot_parts in parts.values():
        for part in slot_parts.values():
            for animation, info in part["animations"].items():
                animations.setdefault(animation, set()).update(info["directions"])

    images = [e for e in entries if e["file_type"] == "image"]
    part_total = sum(len(p) for p in parts.values())
    # 모든 파츠가 같은 셀 규격을 쓰고 같은 애니메이션 집합을 가지면 조합 가능하다.
    cells = set()
    anim_sets = set()
    for slot_parts in parts.values():
        for part in slot_parts.values():
            anim_sets.add(frozenset(part["animations"]))
            for info in part["animations"].values():
                cells.add((info["cell"]["width"], info["cell"]["height"]))
    same_cell = len(cells) == 1
    if len(anim_sets) == 1:
        anim_compat = "yes"
    elif set.intersection(*[set(a) for a in anim_sets]):
        anim_compat = "partial"   # 일부 파츠가 서브셋만 지원. 합성은 가능하다.
    else:
        anim_compat = "no"
    same_anims = anim_compat in ("yes", "partial")

    return {
        "name": pack_name,
        "root": paths.rel(pack_root),
        "adapter": NAME,
        "domain": "characters",
        "file_count": len(entries),
        "image_count": len(images),
        "modular_part_count": len(images),
        "capabilities": {
            "parts_separable": "yes" if part_total >= 2 else "no",
            # 팩 전체 이미지 크기는 애니메이션마다 다르다. 합성에 필요한 건
            # 겹쳐지는 레이어들의 **논리 셀**이 같은지다.
            "shared_canvas": "no",
            "shared_cell": "yes" if same_cell else "no",
            "pre_aligned": "yes" if same_cell else "no",
            "shared_origin": "yes" if same_cell else "unknown",
            "animation_compatible": anim_compat,
            "directional": "yes" if animations else "unknown",
            "composable": "yes" if (part_total >= 2 and same_cell and same_anims) else "no",
            "generation_mode": ("modular_composition"
                               if (part_total >= 2 and same_cell and same_anims) else "unsupported"),
            "origin_policy": "logical_cell",
            "cell": [CELL, CELL],
        },
        "asset_kinds": _counts(e["inferred"]["asset_kind"] for e in entries),
        "packaging": _counts(e["inferred"]["packaging"] for e in entries),
        "declared_tile_sizes": {"%dx%d" % (CELL, CELL): len(images)},
        "scale_variant_groups": {},
        "direction_axis": {
            "present": "yes" if animations else "unknown",
            "encoding": "sheet_row",
            "values": sorted(set().union(*animations.values())) if animations else [],
            # 방향 수는 전역 상수가 아니다. 애니메이션별로 기록한다.
            "by_animation": {a: sorted(v) for a, v in sorted(animations.items())},
        },
        "pre_aligned": True,
        "canvas": [CELL, CELL],
        "content_bbox": [0, 0, CELL, CELL],
        "animation_bbox": {},
        "canvas_histogram": [],
        "subset": {
            "criteria": subset["criteria"],
            "targets": subset["targets"],
            "candidate_counts": subset["candidate_counts"],
            "rejected_counts": subset["rejected_counts"],
            "body_type": subset["body_type"],
            "selected": {slot: [a["id"] for a in items]
                         for slot, items in sorted(subset["selected"].items())},
        },
    }


def _counts(values):
    out = {}
    for value in values:
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items()))
