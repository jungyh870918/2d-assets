"""Sprite Library / Resolver 용 runtime export.

## 기존 baked export 와의 관계

`unity_export.py` 는 **캐릭터마다 합성된 시트**를 내보낸다 (baked path).
그건 그대로 둔다 — 참조 구현이고 regression baseline 이다.

이 모듈은 같은 `character.json` 을 입력으로 **파츠 시트**를 내보낸다 (resolver path).
차이는 compose 에 넘기는 레이어 수뿐이다:

    baked    : compose_sheet(레이어 전부)  -> 캐릭터마다 시트 1장
    resolver : compose_sheet(레이어 1개)   -> 파츠마다 시트 1장 (여러 캐릭터가 공유)

**같은 compose 경로를 쓴다.** resolver 전용 렌더러를 만들지 않는다.

## Sprite Library 매핑

    category = 정규 슬롯 이름        (body / head / hair / torso / legs / feet ...)
    label    = "<animation>__<direction>__<frame:02d>"   (방향 없으면 direction 생략)

이렇게 두면 appearance 교체가 **SpriteLibraryAsset 교체**만으로 끝난다.
카테고리와 라벨 이름이 appearance 마다 동일하므로 AnimationClip 을 그대로 공유한다.
Animator 는 (animation, direction, frame) 을 정하고, Resolver 는 그 라벨에 해당하는
스프라이트를 현재 라이브러리에서 찾는다. 두 책임이 분리된다.

애니메이션을 지원하지 않는 파츠는 그 라벨이 **아예 없다**. Resolver 가 못 찾으면
스프라이트가 null 이 되어 그 레이어만 사라지고 나머지는 계속 움직인다 —
누락 처리 정책이 데이터 구조에서 그대로 나온다.
"""

import json
import os

from . import TOOL_VERSION, attribution, compose, licensing, order, paths

SCHEMA = "ap2d.unity_runtime/1"
# 소비자 패키지 안에서의 리포트 이름. 패키지 상대 경로로 manifest 에 실린다.
ATTRIBUTION_REPORT = "ATTRIBUTION.md"

LABEL_SEP = "__"


def label_for(animation, frame, direction=None):
    if direction:
        return "%s%s%s%s%02d" % (animation, LABEL_SEP, direction, LABEL_SEP, frame)
    return "%s%s%02d" % (animation, LABEL_SEP, frame)


def parse_label(label):
    bits = label.split(LABEL_SEP)
    if len(bits) == 3:
        return {"animation": bits[0], "direction": bits[1], "frame": int(bits[2])}
    return {"animation": bits[0], "direction": None, "frame": int(bits[1])}


def _directions(cat, category, part_name, animation, wanted=None, layer_index=0):
    found = compose.directions_for(cat, category, part_name, animation, layer_index)
    if not found:
        return [None]
    return [d for d in found if not wanted or d in wanted] or [None]


def category_for(slot, layer_index):
    """render layer 하나의 Sprite Library category.

    한 logical item 이 여러 layer 를 만들면 각 layer 가 **별도 category** 여야 한다.
    같은 category 안에 두 layer 를 넣으면 라벨이 정확히 겹쳐 서로를 덮어쓴다.
    slot 이름은 유지하고 layer index 만 덧붙여, appearance 간 label namespace 는
    그대로 공유된다.
    """
    return slot if not layer_index else "%s#%d" % (slot, layer_index)


def collect_parts(characters, rule, cat):
    """appearance 들이 실제로 쓰는 render layer 집합. 정렬되어 결정적.

    반환: [(slot, category_slot_name, asset, layer_index, z_pos)]
    """
    used = {}
    for _cdir, definition in characters:
        for slot, part_name in (definition.get("parts") or {}).items():
            if not part_name:
                continue
            category = rule["slots"][slot]["from"]
            for layer_index, z_pos in compose.visual_layers(cat, category, part_name):
                used[(slot, category, part_name, layer_index)] = z_pos
    return sorted((s, c, p, li, used[(s, c, p, li)]) for (s, c, p, li) in used)


def export(rule, cat, characters, out_root=None, cell_size=256,
           license_summary=None):
    """파츠 시트 + appearance 정의 + runtime manifest 를 쓴다."""
    if license_summary is None:
        license_summary = licensing.summarize(licensing.load(rule["pack"]))
    out_root = out_root or os.path.join(paths.UNITY_EXPORT, "runtime",
                                        rule["profile"])
    if os.path.isdir(out_root):
        import shutil
        shutil.rmtree(paths.assert_writable(out_root))
    paths.ensure_dir(out_root)

    animations = list(rule.get("sheets") or rule.get("animations") or [])
    wanted_directions = rule.get("directions")
    parts = collect_parts(characters, rule, cat)

    # ── 파츠 시트 ─────────────────────────────────────────────────────────
    sheet_records = []
    sprite_count = 0
    for slot, category, part_name, layer_index, _z in parts:
        for animation in animations:
            # 이 레이어가 지원하지 않는 애니메이션은 시트를 만들지 않는다.
            # 라벨이 없으면 런타임에서 그 레이어만 숨는다 (hide_layer).
            if not compose.supports(cat, category, part_name, animation, layer_index):
                continue
            info = compose.animation_info(cat, category, part_name, animation,
                                          layer_index)
            box = None
            if not compose.is_sheet_based(info):
                # 프레임 파일 기반 팩은 애니메이션끼리 정렬을 맞춰야 한다 (baked 와 동일 규칙)
                box = compose.union_box(cat, animations)
            for direction in _directions(cat, category, part_name, animation,
                                         wanted_directions, layer_index):
                layers = [(slot, category, part_name, None, layer_index)]
                sheet, _used, meta = compose.compose_sheet(
                    cat, layers, animation, size=cell_size, box=box,
                    direction=direction)
                folder = part_name if not layer_index else "%s_l%d" % (part_name, layer_index)
                rel = os.path.join("parts", slot, folder,
                                   "%s.png" % (animation if direction is None
                                               else "%s_%s" % (animation, direction)))
                dest = os.path.join(out_root, rel)
                paths.ensure_dir(os.path.dirname(dest))
                sheet.save(paths.assert_writable(dest))
                labels = [label_for(animation, i, direction)
                          for i in range(meta["frame_count"])]
                sprite_count += len(labels)
                sheet_records.append({
                    "slot": category_for(slot, layer_index),
                    "logical_slot": slot,
                    "layer_index": layer_index,
                    "asset": part_name,
                    "animation": animation,
                    "direction": direction,
                    "file": rel.replace(os.sep, "/"),
                    "frame_count": meta["frame_count"],
                    "cell_width": meta["cell_size"][0],
                    "cell_height": meta["cell_size"][1],
                    "size": list(sheet.size),
                    "labels": labels,
                })

    # ── appearance (character.json 을 그대로 입력으로 쓴다) ─────────────────
    appearances = []
    appearance_attribs = []
    for cdir, definition in characters:
        layers = []
        for slot in definition["layer_order"]:
            part_name = definition["parts"].get(slot)
            if not part_name:
                continue
            category = rule["slots"][slot]["from"]
            for layer_index, z_pos in compose.visual_layers(cat, category, part_name):
                layers.append({
                    "slot": category_for(slot, layer_index),
                    # logical item 은 하나다. 여러 visual layer 가 같은 선택에 묶인다.
                    "logical_slot": slot,
                    "layer_index": layer_index,
                    "asset": part_name,
                    # z-order 는 소스가 선언했으면 그 값, 아니면 layer_order 순번.
                    "z_order": z_pos if z_pos is not None
                    else definition["layer_order"].index(slot),
                    "z_source": "declared" if z_pos is not None else "layer_order",
                    "supported_animations": [
                        a for a in animations
                        if compose.supports(cat, category, part_name, a, layer_index)],
                })
        layers.sort(key=lambda l: l["z_order"])
        gen_path = os.path.join(cdir, "generation.json")
        attrib = {}
        if os.path.isfile(gen_path):
            with open(gen_path, "r", encoding="utf-8") as fh:
                attrib = json.load(fh).get("attribution") or {}
        # appearance 블록에는 요약만 싣지만, 프로파일 단위 rollup 을 만들려면
        # entries 가 있는 원본이 필요하다.
        appearance_attribs.append(attrib)
        appearances.append({
            "seed": definition["seed"],
            "archetype": definition.get("archetype", ""),
            "definition": paths.rel(os.path.join(cdir, "character.json")),
            "layers": layers,
            "attribution": {
                "source_assets": attrib.get("source_assets", 0),
                "authors": attrib.get("authors", []),
                "licenses": attrib.get("licenses", []),
                "attribution_required": attrib.get("attribution_required", False),
                "share_alike_present": attrib.get("share_alike_present", False),
            },
        })

    # 프로파일 전체 슬롯을 z-order 순으로. **appearance 마다가 아니라 프로파일 단위다.**
    # 선택 슬롯(CC0 의 horn/weapon/wing) 때문에 캐릭터마다 슬롯 집합이 달라지는데,
    # 프리팹 구조가 캐릭터마다 다르면 AnimationClip 을 공유할 수 없다.
    # 프리팹은 항상 프로파일 전체 슬롯을 갖고, 안 쓰는 슬롯은 스프라이트가 없어 숨겨진다.
    slot_z = {}
    slot_meta = {}
    for slot, category, part_name, layer_index, z_pos in parts:
        name = category_for(slot, layer_index)
        z = (z_pos if z_pos is not None else rule["layer_order"].index(slot))
        slot_z.setdefault(name, z)
        slot_meta.setdefault(name, {"logical_slot": slot, "layer_index": layer_index})
    profile_slots = [dict(slot_meta[s], slot=s, z_order=slot_z[s])
                     for s in sorted(slot_z, key=lambda s: (slot_z[s], s))]

    topology = _topology(cat, parts, animations, wanted_directions)
    caps = cat["pack"].get("capabilities", {})
    settings = dict(rule.get("unity", {}))

    # 표기 의무는 소비자까지 따라가야 한다. 이전에는 appearance 마다 요약만 실려서,
    # 게임 credits 를 만들려면 소비자가 appearance 를 전부 훑어 합쳐야 했다.
    # 그건 소비자가 할 일이 아니다 — Factory 가 이미 아는 사실이다.
    merged = attribution.merge(appearance_attribs)
    report_name = None
    if merged["attribution_entries"]:
        report_name = ATTRIBUTION_REPORT
        attribution.write_report(
            rule["profile"], rule["pack"], merged, len(appearances),
            out_path=os.path.join(out_root, report_name),
            generated_by="tools/export_unity_runtime.py")
    profile_attribution = {
        "source_assets": merged["source_assets"],
        "authors": merged["authors"],
        "licenses": merged["licenses"],
        "source_urls": merged["source_urls"],
        # credits 화면에 그대로 넣을 줄. 소비자가 저자 목록을 다시 조합하지 않는다.
        "credits": attribution.credit_lines(merged),
        "attribution_required": merged["attribution_required"],
        "share_alike_present": merged["share_alike_present"],
        # **패키지 상대 경로다.** 소비자에게 Factory 저장소 경로를 주면 못 읽는다.
        "report": report_name,
    }

    manifest = {
        "schema": SCHEMA,
        "tool_version": TOOL_VERSION,
        "profile": rule["profile"],
        "pack": rule["pack"],
        "rule": rule["_path"],
        # 이 산출물이 자체 기술 검증인지 발주 대응인지. 파일만 봐서는 성격을 알 수 없어서
        # 라벨 하나를 싣는다. **막는 값이 아니다** — 생성도 export 도 그대로 자유롭다.
        "order": order.order_block(rule),
        "runtime_mode": "modular_runtime",
        "label_format": "<animation>%s[<direction>%s]<frame:02d>" % (LABEL_SEP, LABEL_SEP),
        "categories": sorted(set(category_for(s, li) for s, _c, _p, li, _z in parts)),
        # 프리팹이 만들어야 할 슬롯 목록 (z-order 순). appearance 와 무관하게 고정이다.
        "slots": profile_slots,
        "animations": animations,
        "topology": topology,
        # 소비자(게임)가 이동 방향을 캐릭터 방향으로 바꾸려면 방향 목록이 필요하다.
        # topology 안에 애니메이션별로 흩어져 있으면 게임이 그걸 합쳐야 해서,
        # profile 수준의 합집합을 명시적으로 싣는다. (실제 소비자 붙이며 발견된 필요)
        "direction_axis": {
            "present": "yes" if any(t["directions"] for t in topology.values()) else "no",
            "encoding": cat["pack"].get("direction_axis", {}).get("encoding", "unknown"),
            "values": sorted(set(d for t in topology.values() for d in t["directions"])),
        },
        # JsonUtility 가 dictionary 를 못 읽어서 Unity 용 배열 형태도 함께 싣는다.
        "topology_list": [dict(v, animation=k) for k, v in topology.items()],
        "frame_rate": settings.get("frame_rate", 12),
        "origin": {
            "policy": caps.get("origin_policy", "unknown"),
            "pivot": settings.get("pivot", "BottomCenter"),
            "pixels_per_unit": settings.get("pixels_per_unit", 100),
            "logical_cell": caps.get("cell"),
        },
        "import_settings": settings,
        "missing_animation_policy": "hide_layer",
        "license": license_summary,
        "commercial_release_eligible": license_summary["commercial_release_eligible"],
        # 상업 사용 가능(commercial_release_eligible) 과 **다른 축**이다.
        # 표기 의무를 지키지 않으면 commercial_use: yes 여도 라이선스 위반이다.
        "attribution": profile_attribution,
        "part_sheets": sheet_records,
        "appearances": appearances,
        "counts": {
            "appearances": len(appearances),
            "unique_parts": len(set((s, p) for s, _c, p, _li, _z in parts)),
            "render_layers": len(parts),
            "part_sheets": len(sheet_records),
            "unique_sprites": sprite_count,
        },
    }
    manifest_path = os.path.join(out_root, "runtime_manifest.json")
    with open(paths.assert_writable(manifest_path), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return manifest_path, manifest


def _topology(cat, parts, animations, wanted_directions):
    """애니메이션별 (frame_count, directions). 방향 수가 애니메이션마다 다를 수 있다."""
    out = {}
    for slot, category, part_name, layer_index, _z in parts:
        for animation in animations:
            if not compose.supports(cat, category, part_name, animation, layer_index):
                continue
            directions = _directions(cat, category, part_name, animation,
                                     wanted_directions, layer_index)
            count = compose.frame_count(cat, category, part_name, animation,
                                        layer_index)
            entry = out.setdefault(animation, {
                "frame_count": count,
                "directions": [d for d in directions if d],
            })
            # 파츠마다 프레임 수가 다르면 그건 팩 문제다. 최댓값으로 기록하고 남긴다.
            entry["frame_count"] = max(entry["frame_count"], count)
    return dict(sorted(out.items()))


def measure_baked(profile_dir):
    """baked path 실측. 추정이 아니라 실제 파일에서 센다."""
    textures = 0
    frames = 0
    disk = 0
    pixels = 0
    for name in sorted(os.listdir(profile_dir)):
        cdir = os.path.join(profile_dir, name)
        cpath = os.path.join(cdir, "character.json")
        if not os.path.isfile(cpath):
            continue
        with open(cpath, "r", encoding="utf-8") as fh:
            definition = json.load(fh)
        for info in (definition.get("outputs", {}).get("sheets") or {}).values():
            path = os.path.join(cdir, info["file"])
            if os.path.isfile(path):
                textures += 1
                frames += info["frame_count"]
                disk += os.path.getsize(path)
                pixels += info["size"][0] * info["size"][1]
    return {"textures": textures, "sprites": frames, "disk_bytes": disk,
            "pixels": pixels}


def measure_runtime(manifest, out_root):
    disk = 0
    pixels = 0
    for record in manifest["part_sheets"]:
        path = os.path.join(out_root, record["file"])
        if os.path.isfile(path):
            disk += os.path.getsize(path)
            pixels += record["size"][0] * record["size"][1]
    manifest_path = os.path.join(out_root, "runtime_manifest.json")
    return {
        "textures": len(manifest["part_sheets"]),
        "sprites": manifest["counts"]["unique_sprites"],
        "disk_bytes": disk,
        "pixels": pixels,
        "manifest_bytes": os.path.getsize(manifest_path)
        if os.path.isfile(manifest_path) else 0,
    }
