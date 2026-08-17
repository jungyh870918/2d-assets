"""Deterministic character generator.

입력: catalog + rule + palette + seed
출력: 05_GENERATED/characters/<profile>/<seed>/

결정성 규칙 (CLAUDE.md):
  - random.random() / Math.random() / 현재 시각을 쓰지 않는다.
  - 슬롯마다 독립된 난수 스트림을 쓴다. 스트림 seed 는
    sha256("<rule id>|<seed>|<attempt>|<key>") 로 만든다.
    파이썬의 내장 hash() 는 실행마다 salt 가 달라지므로 절대 쓰지 않는다.
  - 슬롯별 스트림이 독립이라 규칙에 슬롯을 하나 추가해도
    기존 슬롯의 선택 결과가 밀리지 않는다.
"""

import hashlib
import json
import os
import random

from . import (TOOL_VERSION, attribution, catalog as catalog_mod, compose,
               licensing, palette as palette_mod, paths, rules)

CHARACTER_SCHEMA = "ap2d.character/1"


class GenerateError(RuntimeError):
    pass


class UnsupportedPackError(GenerateError):
    """팩 구조가 modular composition 에 맞지 않아 생성을 시작조차 할 수 없다.

    버그가 아니라 팩의 성질이다. 호출한 쪽이 SKIPPED 상태로 다룰 수 있게
    reason 을 기계가 읽을 수 있는 형태로 들고 있는다.
    """

    def __init__(self, pack, capabilities):
        self.pack = pack
        self.capabilities = capabilities
        self.reason = capabilities.get("reason", "unknown")
        self.mode = capabilities.get("generation_mode", "unknown")
        super(UnsupportedPackError, self).__init__(
            "%s 는 modular composition 을 지원하지 않는다 "
            "(generation_mode=%s, reason=%s). "
            "parts_separable=%s pre_aligned=%s animation_compatible=%s"
            % (pack, self.mode, self.reason,
               capabilities.get("parts_separable"),
               capabilities.get("pre_aligned"),
               capabilities.get("animation_compatible")))


def generation_status(catalog):
    """팩의 생성 가능 여부를 machine-readable 하게. 예외 없이 조회만 한다."""
    caps = catalog["pack"].get("capabilities", {})
    mode = caps.get("generation_mode", "unknown")
    supported = mode == compose.MODULAR_MODE
    status = {
        "pack": catalog["pack"]["name"],
        "generation_mode": mode,
        "status": "supported" if supported else "skipped",
        "capabilities": caps,
    }
    if not supported:
        status["reason"] = caps.get("reason", "unknown")
    return status


# ── 결정적 난수 ────────────────────────────────────────────────────────────

def stream(rule_id, seed, attempt, key):
    """(rule, seed, attempt, key) 마다 재현 가능한 독립 난수 스트림."""
    material = "%s|%d|%d|%s" % (rule_id, seed, attempt, key)
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest, "big"))


def pick(rng, options):
    """정렬된 목록에서 하나. random.choice 는 시퀀스 길이에만 의존해 안정적이다."""
    return options[rng.randrange(len(options))]


# ── 슬롯 선택 ──────────────────────────────────────────────────────────────

def choose_parts(rule, cat, arch, seed, attempt):
    """slot -> part 이름 (없으면 None). layer_order 순서로 결정한다."""
    constraints = arch.get("constraints", {})
    chosen = {}
    for slot_name in rule["layer_order"]:
        slot = rules.merge_constraint(rule["slots"][slot_name],
                                      constraints.get(slot_name, {}))
        follows = slot.get("follows")
        if follows:
            # 짝 파츠: 따라가는 쪽은 자기 후보 목록에서 같은 index 를 쓴다.
            if chosen.get(follows) is None:
                chosen[slot_name] = None
                continue
            lead_slot = rules.merge_constraint(rule["slots"][follows],
                                               constraints.get(follows, {}))
            lead_candidates = rules.candidates_for(lead_slot, cat)
            own_candidates = rules.candidates_for(slot, cat)
            index = lead_candidates.index(chosen[follows])
            if index >= len(own_candidates):
                raise GenerateError(
                    "slot %r 이 %r 을 follows 하는데 대응 후보가 없다" % (slot_name, follows))
            chosen[slot_name] = own_candidates[index]
            continue

        candidates = rules.candidates_for(slot, cat)
        if not candidates:
            if slot["required"]:
                raise GenerateError("required slot %r 의 후보가 0개다" % slot_name)
            chosen[slot_name] = None
            continue

        rng = stream(rule["id"], seed, attempt, "slot:" + slot_name)
        if not slot["required"] and slot["none_weight"] > 0:
            if rng.random() < slot["none_weight"]:
                chosen[slot_name] = None
                continue
        chosen[slot_name] = pick(rng, candidates)
    return chosen


def choose_palette(rule, pal, arch, seed, attempt, chosen_parts):
    """slot -> ramp id. untinted 슬롯은 배정하지 않는다."""
    pconf = rule.get("palettes")
    if not pconf:
        return {}, {}
    untinted = set(pconf.get("untinted", []))
    tint_index = pconf.get("tint_index", 1)
    overrides = arch.get("palette_constraints", {})

    assignments = {}
    group_choice = {}
    for gname in sorted(pconf["groups"]):
        group = pconf["groups"][gname]
        ramps = list(group["ramps"])
        allow = overrides.get(gname, {}).get("only")
        if allow:
            ramps = [r for r in ramps if r in allow]
            if not ramps:
                raise GenerateError(
                    "archetype %r 의 palette 제약이 group %r 의 ramp 를 전부 없앴다"
                    % (arch["name"], gname))
        # 그룹마다 독립 스트림이라, 아래에서 이 그룹을 버려도 다른 그룹의 결과는 안 밀린다.
        rng = stream(rule["id"], seed, attempt, "palette:" + gname)
        ramp_id = pick(rng, ramps)
        applied = False
        for slot_name in group["slots"]:
            if slot_name in untinted:
                continue
            if chosen_parts.get(slot_name) is None:
                continue
            assignments[slot_name] = ramp_id
            applied = True
        # 실제로 칠해진 슬롯이 하나도 없으면 기록하지 않는다.
        # 안 그러면 날개 없는 캐릭터 둘이 '안 쓰인 날개 램프'만 다른 채로
        # 서로 다른 조합으로 집계돼, 눈에는 똑같은 캐릭터가 중복 검사를 통과한다.
        if applied:
            group_choice[gname] = ramp_id

    tints = {s: palette_mod.tint_color(pal, r, tint_index)
             for s, r in assignments.items()}
    return {"palette": pal["name"],
            "source": pal["_path"],
            "tint_index": tint_index,
            "groups": group_choice,
            "slots": assignments}, tints


def combination_key(parts, palette_info):
    """중복 판정 키. 파츠 조합 + 팔레트 배정이 모두 같아야 중복이다."""
    part_sig = tuple(sorted((k, v) for k, v in parts.items() if v))
    pal_sig = tuple(sorted(palette_info.get("groups", {}).items()))
    return (part_sig, pal_sig)


# ── 한 캐릭터 만들기 ───────────────────────────────────────────────────────

def build_definition(rule, cat, pal, arch, seed, used_keys=None,
                     max_attempts=64):
    """character.json 에 해당하는 dict + tint 표를 만든다. 이미지는 아직 안 그린다."""
    used_keys = used_keys if used_keys is not None else set()
    no_dupes = rule.get("global", {}).get("no_duplicate_combinations", True)

    attempt = 0
    while True:
        parts = choose_parts(rule, cat, arch, seed, attempt)
        palette_info, tints = choose_palette(rule, pal, arch, seed, attempt, parts)
        key = combination_key(parts, palette_info)
        if not no_dupes or key not in used_keys:
            break
        attempt += 1
        if attempt >= max_attempts:
            raise GenerateError(
                "seed %d: %d번 재시도했지만 중복되지 않는 조합을 못 찾았다. "
                "규칙의 후보 수가 생성 개수보다 적을 수 있다." % (seed, max_attempts))

    animations = list(rule["animations"])
    definition = {
        "schema": CHARACTER_SCHEMA,
        "pack": rule["pack"],
        "profile": rule["profile"],
        "archetype": arch["name"],
        "seed": seed,
        "parts": {slot: parts[slot] for slot in rule["layer_order"]},
        "palette": palette_info,
        "animations": animations,
        "layer_order": [s for s in rule["layer_order"] if parts[s]],
    }
    meta = {"attempt": attempt, "key": key}
    return definition, tints, meta


def layers_for(definition, rule, tints, cat=None):
    """합성용 레이어 목록 (z-order 순).

    logical item 하나가 render layer 여러 개를 만들 수 있다 (LPC 의 앞/뒤 머리).
    그 경우 각 레이어가 **자기 zPos** 를 갖고, 그 값으로 전체를 다시 정렬한다 —
    한 아이템의 뒤 레이어가 몸통보다 뒤로 가야 하기 때문에 슬롯 순서로는 표현이 안 된다.

    카탈로그가 없거나 z_pos 선언이 없는 팩(CC0)은 기존처럼 layer_order 를 따른다.
    """
    entries = []
    for index, slot in enumerate(definition["layer_order"]):
        part_name = definition["parts"][slot]
        if not part_name:
            continue
        category = rule["slots"][slot]["from"]
        visuals = ([(0, None)] if cat is None
                   else compose.visual_layers(cat, category, part_name))
        for layer_index, z_pos in visuals:
            entries.append({
                "slot": slot, "category": category, "part": part_name,
                "tint": tints.get(slot), "layer_index": layer_index,
                "z_pos": z_pos, "order": index,
            })

    if entries and all(e["z_pos"] is not None for e in entries):
        entries.sort(key=lambda e: (e["z_pos"], e["order"], e["layer_index"]))
    return [(e["slot"], e["category"], e["part"], e["tint"], e["layer_index"])
            for e in entries]


def render(definition, rule, cat, tints, out_dir, preview_size=384,
           sheet_size=256):
    """preview.png + sheet_<anim>.png 를 쓰고, 사용한 소스 파일 목록을 돌려준다."""
    paths.ensure_dir(out_dir)
    layers = layers_for(definition, rule, tints, cat)
    preview_anim = rule.get("preview", {}).get("animation", definition["animations"][0])
    preview_frame = rule.get("preview", {}).get("frame", 0)

    used = set()
    outputs = {}

    # 방향 축은 팩마다 다르다. 없는 팩(CC0)은 [None] 한 번만 돈다 —
    # 그래야 기존 출력이 파일명까지 그대로 유지된다.
    def directions_of(animation):
        first = next((l for l in layers
                      if compose.supports(cat, l[1], l[2], animation, l[4])), layers[0])
        found = compose.directions_for(cat, first[1], first[2], animation, first[4])
        if not found:
            return [None]
        wanted = rule.get("directions")
        return [d for d in found if not wanted or d in wanted] or [None]

    preview_dir = rule.get("preview", {}).get("direction")
    if preview_dir is None:
        candidates = directions_of(preview_anim)
        preview_dir = candidates[0]
    img, used_paths = compose.compose_frame(
        cat, layers, preview_anim, preview_frame, size=preview_size,
        direction=preview_dir)
    used.update(used_paths)
    preview_path = os.path.join(out_dir, "preview.png")
    img.save(paths.assert_writable(preview_path))
    outputs["preview"] = {
        "file": "preview.png",
        "animation": preview_anim,
        "frame": preview_frame,
        "size": list(img.size),
    }
    if preview_dir:
        outputs["preview"]["direction"] = preview_dir

    # 시트로 나가는 애니메이션은 전부 같은 사각형으로 자른다. 애니메이션별 tight bbox 를
    # 쓰면 셀 크기와 발 위치가 애니메이션마다 달라져서, Unity 에서 idle -> walk 전환 때
    # 캐릭터가 커졌다 작아졌다 하고 위아래로 튄다.
    sheet_anims = list(rule.get("sheets", []))
    # union_box 는 프레임 파일 기반 팩에서만 의미가 있다 (애니메이션마다 bbox 가 달라서).
    # 시트 셀 기반 팩은 셀 크기가 고정이라 필요 없다.
    sheet_box = None
    if sheet_anims:
        first = layers[0]
        info0 = compose.animation_info(cat, first[1], first[2], sheet_anims[0])
        if not compose.is_sheet_based(info0):
            sheet_box = compose.union_box(cat, sheet_anims)

    sheets = {}
    for anim in sheet_anims:
        if not any(compose.supports(cat, c, p, anim, li)
                   for _s, c, p, _t, li in layers):
            continue
        for direction in directions_of(anim):
            sheet, used_paths, info = compose.compose_sheet(
                cat, layers, anim, size=sheet_size, box=sheet_box,
                direction=direction)
            used.update(used_paths)
            key = anim if direction is None else "%s:%s" % (anim, direction)
            name = ("sheet_%s.png" % anim if direction is None
                    else "sheet_%s_%s.png" % (anim, direction))
            sheet.save(paths.assert_writable(os.path.join(out_dir, name)))
            entry = {
                "file": name,
                "frame_count": info["frame_count"],
                "cell_size": info["cell_size"],
                "size": list(sheet.size),
            }
            if direction:
                # 방향이 있으면 키가 "anim:direction" 이라 애니메이션 이름을 따로 적는다.
                # 방향이 없는 팩은 키가 곧 애니메이션 이름이므로 중복 필드를 넣지 않는다.
                entry["animation"] = anim
                entry["direction"] = direction
            sheets[key] = entry
    outputs["sheets"] = sheets
    if sheet_box:
        outputs["sheet_crop"] = list(sheet_box)
    return sorted(used), outputs


def generate(rule_path, out_root=None, render_images=True, preview_size=384,
             sheet_size=256, verbose=True):
    """규칙 파일 하나를 끝까지 실행한다. 반환: 생성된 캐릭터 레코드 목록."""
    rule_raw = _peek_rule(rule_path)
    pack_name = rule_raw.get("pack")
    if not pack_name:
        raise rules.RuleError("규칙에 pack 이 없다: %s" % rule_path)

    # 라이선스 게이트 — 승인되지 않은 팩은 여기서 막힌다.
    license_fields = licensing.require_approved(pack_name)
    license_summary = licensing.summarize(license_fields)
    if verbose and not license_summary["commercial_release_eligible"]:
        print("  ⛔ %s" % licensing.NONCOMMERCIAL_BANNER)
        print("     pack=%s license=%s commercial_use=%s"
              % (pack_name, license_summary["license"],
                 license_summary["commercial_use"]))

    cat = catalog_mod.load_catalog(rule_raw["catalog"])

    # 팩이 조합 가능한 구조인지 먼저 본다. 아니면 여기서 이유와 함께 멈춘다.
    # 이 검사가 없으면 한참 아래에서 "category 'body' 가 없다" 같은 곁가지 오류로
    # 죽어서, 팩 구조 자체가 안 맞는다는 사실이 드러나지 않는다.
    caps = cat["pack"].get("capabilities", {})
    if caps.get("generation_mode") != compose.MODULAR_MODE:
        raise UnsupportedPackError(pack_name, caps)
    compose.require_modular(cat)   # compose 입력 계약도 같은 지점에서 확인한다

    pal = palette_mod.load(rule_raw["palettes"]["source"]) if rule_raw.get("palettes") else None
    rule = rules.load(rule_path, catalog=cat, pal=pal)

    out_root = out_root or os.path.join(paths.GEN_CHARACTERS, rule["profile"])
    paths.ensure_dir(out_root)

    rule_hash = _file_hash(paths.abspath(rule["_path"]))
    catalog_hash = _file_hash(paths.abspath(rule["catalog"]))
    palette_hash = _file_hash(paths.abspath(pal["_path"])) if pal else None

    used_keys = set()
    records = []
    for arch in rule["archetypes"]:
        for seed in arch["_seeds"]:
            definition, tints, meta = build_definition(
                rule, cat, pal, arch, seed, used_keys)
            used_keys.add(meta["key"])

            seed_dir = os.path.join(out_root, str(seed))
            paths.ensure_dir(seed_dir)

            sources, outputs = ([], {})
            if render_images:
                sources, outputs = render(definition, rule, cat, tints, seed_dir,
                                          preview_size=preview_size,
                                          sheet_size=sheet_size)
            else:
                sources = sorted(_expected_sources(definition, rule, cat))

            selections = [(rule["slots"][s]["from"], p)
                          for s, p in definition["parts"].items() if p]
            attribution_summary = attribution.summarize(
                attribution.credits_for_parts(cat, selections))

            definition["outputs"] = outputs
            _write_json(os.path.join(seed_dir, "character.json"), definition)
            _write_json(os.path.join(seed_dir, "sources.json"), {
                "schema": "ap2d.sources/1",
                "pack": rule["pack"],
                "seed": seed,
                "count": len(sources),
                "assets": sources,
            })
            _write_json(os.path.join(seed_dir, "generation.json"), {
                "schema": "ap2d.generation/1",
                "tool_version": TOOL_VERSION,
                "rule": rule["_path"],
                "rule_sha256": rule_hash,
                "catalog": rule["catalog"],
                "catalog_sha256": catalog_hash,
                "palette": pal["_path"] if pal else None,
                "palette_sha256": palette_hash,
                "seed": seed,
                "archetype": arch["name"],
                "reroll_attempts": meta["attempt"],
                # 파일 단위 provenance. credits 가 없는 팩에서는 빈 블록이 된다.
                "attribution": attribution_summary,
                # 라이선스 제한은 생성물을 따라다녀야 한다. 나중에 이 폴더만 보고도
                # 상업적으로 써도 되는지 판단할 수 있어야 한다.
                "license": license_summary,
                "commercial_release_eligible":
                    license_summary["commercial_release_eligible"],
                "deterministic": True,
            })

            records.append({
                "seed": seed,
                "archetype": arch["name"],
                "dir": paths.rel(seed_dir),
                "definition": definition,
                "sources": sources,
                "attempt": meta["attempt"],
                "attribution": attribution_summary,
            })
            if verbose:
                print("  %s seed=%d attempt=%d parts=%s"
                      % (arch["name"], seed, meta["attempt"],
                         ",".join(p for p in definition["parts"].values() if p)))
    compose.clear_cache()
    return {"rule": rule, "catalog": cat, "palette": pal, "records": records,
            "license": license_summary, "out_root": paths.rel(out_root)}


def _expected_sources(definition, rule, cat):
    out = set()
    anims = set(definition["animations"])
    for slot in definition["layer_order"]:
        part_name = definition["parts"][slot]
        if not part_name:
            continue
        category = rule["slots"][slot]["from"]
        for layer_index, _z in compose.visual_layers(cat, category, part_name):
            for anim in anims:
                if not compose.supports(cat, category, part_name, anim, layer_index):
                    continue
                info = compose.animation_info(cat, category, part_name, anim,
                                              layer_index)
                if info.get("files"):
                    out.update(info["files"])
                elif info.get("sheet"):
                    out.add(info["sheet"])
    return out


def _peek_rule(rule_path):
    with open(paths.abspath(rule_path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _file_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path, data):
    with open(paths.assert_writable(path), "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")
