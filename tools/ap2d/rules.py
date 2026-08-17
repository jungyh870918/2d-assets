"""04_RULES/*.json 로딩 + 검증.

_example_character_rule.json 의 철학을 그대로 유지한다:
  slots / palettes / archetypes / global(no_duplicate_combinations, deterministic).

이 팩에 맞춰 추가된 것은 두 가지뿐이다.
  - slot.side        : 같은 category 안에서 좌/우를 가르기 위한 필터 (Left feet vs Right feet)
  - slot.follows     : 짝 파츠. 왼쪽 날개를 뽑으면 오른쪽 날개도 같은 index 로 따라간다.
  - layer_order      : 합성 z-order. 코드가 아니라 데이터로 둔다.

규칙이 잘못되면 조용히 넘어가지 않고 RuleError 로 즉시 죽는다.
"""

import json
import os

from . import paths

SCHEMA = "ap2d.rule/1"


class RuleError(ValueError):
    pass


def _require(cond, msg):
    if not cond:
        raise RuleError(msg)


def load(path, catalog=None, pal=None):
    """규칙을 읽고 구조를 검증한다. catalog/palette 를 주면 참조 무결성까지 본다."""
    abs_path = paths.abspath(path)
    _require(os.path.isfile(abs_path), "규칙 파일이 없다: %s" % path)
    with open(abs_path, "r", encoding="utf-8") as fh:
        try:
            rule = json.load(fh)
        except json.JSONDecodeError as exc:
            raise RuleError("규칙 JSON 파싱 실패 %s: %s" % (path, exc))

    _require(rule.get("schema") == SCHEMA,
             "규칙 schema 가 %r 이어야 한다 (현재: %r)" % (SCHEMA, rule.get("schema")))
    for field in ("id", "profile", "pack", "catalog", "slots", "archetypes"):
        _require(field in rule, "규칙에 필수 항목 %r 이 없다" % field)
    _require(isinstance(rule["slots"], dict) and rule["slots"], "slots 가 비어 있다")
    _require(isinstance(rule["archetypes"], list) and rule["archetypes"],
             "archetypes 가 비어 있다")

    rule.setdefault("animations", [])
    rule.setdefault("layer_order", list(rule["slots"].keys()))
    rule.setdefault("global", {})
    rule["_path"] = paths.rel(abs_path)

    _validate_slots(rule)
    # layer_order 가 "by_z_pos" 면 소스가 선언한 z-order 를 쓴다.
    # 팩이 z-order 를 선언하는데도 사람이 규칙에 손으로 베껴 적을 이유가 없다.
    if rule["layer_order"] == "by_z_pos":
        if catalog is None:
            raise RuleError("layer_order: by_z_pos 는 카탈로그가 있어야 계산할 수 있다")
        rule["layer_order"] = layer_order_by_z_pos(rule, catalog)
        rule["_layer_order_source"] = "catalog:z_pos"
    else:
        rule["_layer_order_source"] = "rule"
    _validate_layer_order(rule)
    _validate_archetypes(rule)
    if catalog is not None:
        _validate_against_catalog(rule, catalog)
    if pal is not None:
        _validate_palettes(rule, pal)
    return rule


def _validate_slots(rule):
    for name, slot in rule["slots"].items():
        _require(isinstance(slot, dict), "slot %r 이 객체가 아니다" % name)
        _require("from" in slot, "slot %r 에 'from'(category) 이 없다" % name)
        slot.setdefault("required", False)
        slot.setdefault("none_weight", 0.0)
        slot.setdefault("side", None)
        slot.setdefault("allow", None)
        slot.setdefault("deny", [])
        slot.setdefault("follows", None)
        _require(isinstance(slot["none_weight"], (int, float))
                 and 0.0 <= slot["none_weight"] < 1.0,
                 "slot %r 의 none_weight 는 0 이상 1 미만이어야 한다" % name)
        _require(not (slot["required"] and slot["none_weight"] > 0),
                 "slot %r: required 인데 none_weight 가 0 이 아니다" % name)
        if slot["follows"]:
            _require(slot["follows"] in rule["slots"],
                     "slot %r 의 follows 대상 %r 이 없다" % (name, slot["follows"]))
            _require(slot["follows"] != name, "slot %r 이 자기 자신을 follows 한다" % name)


def layer_order_by_z_pos(rule, catalog):
    """카탈로그가 선언한 z_pos 로 레이어 순서를 만든다 (뒤 -> 앞).

    같은 슬롯의 파츠는 같은 z_pos 를 갖는다고 가정하지 않고 최솟값을 쓴다.
    z_pos 가 같으면 슬롯 이름순으로 갈라 결정성을 보장한다.
    """
    ranked = []
    for slot_name, slot in rule["slots"].items():
        parts = catalog["parts"].get(slot["from"], {})
        values = [p["z_pos"] for p in parts.values() if p.get("z_pos") is not None]
        if not values:
            raise RuleError(
                "slot %r 의 category %r 에 z_pos 선언이 없다 — layer_order 를 "
                "직접 적어야 한다" % (slot_name, slot["from"]))
        ranked.append((min(values), slot_name))
    ranked.sort()
    return [name for _z, name in ranked]


def _validate_layer_order(rule):
    order = rule["layer_order"]
    _require(isinstance(order, list), "layer_order 는 리스트여야 한다")
    missing = [s for s in rule["slots"] if s not in order]
    _require(not missing, "layer_order 에 빠진 slot: %s" % ", ".join(sorted(missing)))
    unknown = [s for s in order if s not in rule["slots"]]
    _require(not unknown, "layer_order 에 정의되지 않은 slot: %s" % ", ".join(unknown))
    _require(len(set(order)) == len(order), "layer_order 에 중복 slot 이 있다")


def _validate_archetypes(rule):
    seen_seeds = {}
    for arch in rule["archetypes"]:
        _require("name" in arch, "archetype 에 name 이 없다")
        _require("seeds" in arch, "archetype %r 에 seeds 가 없다" % arch["name"])
        seeds = expand_seeds(arch["seeds"], arch["name"])
        arch["_seeds"] = seeds
        for seed in seeds:
            _require(seed not in seen_seeds,
                     "seed %d 가 archetype %r 과 %r 에 중복 배정됐다"
                     % (seed, seen_seeds.get(seed), arch["name"]))
            seen_seeds[seed] = arch["name"]
        for slot_name in arch.get("constraints", {}):
            _require(slot_name in rule["slots"],
                     "archetype %r 의 제약이 없는 slot %r 을 가리킨다"
                     % (arch["name"], slot_name))


def expand_seeds(spec, arch_name=""):
    """seeds: [1001, 1002] 또는 {"from":1001,"to":1010} 또는 두 형태의 리스트."""
    if isinstance(spec, dict):
        _require("from" in spec and "to" in spec,
                 "archetype %r 의 seeds 객체에 from/to 가 필요하다" % arch_name)
        _require(spec["to"] >= spec["from"],
                 "archetype %r 의 seeds from > to" % arch_name)
        return list(range(int(spec["from"]), int(spec["to"]) + 1))
    _require(isinstance(spec, list) and spec,
             "archetype %r 의 seeds 가 비어 있다" % arch_name)
    out = []
    for item in spec:
        if isinstance(item, dict):
            out.extend(expand_seeds(item, arch_name))
        else:
            out.append(int(item))
    _require(len(set(out)) == len(out), "archetype %r 의 seeds 에 중복이 있다" % arch_name)
    return out


def _validate_against_catalog(rule, catalog):
    _require(catalog["pack"]["name"] == rule["pack"],
             "규칙의 pack(%r) 과 카탈로그의 pack(%r) 이 다르다"
             % (rule["pack"], catalog["pack"]["name"]))
    parts = catalog["parts"]
    for name, slot in rule["slots"].items():
        category = slot["from"]
        _require(category in parts,
                 "slot %r 이 카탈로그에 없는 category %r 을 참조한다 (있는 것: %s)"
                 % (name, category, ", ".join(sorted(parts))))
        candidates = candidates_for(slot, catalog)
        _require(candidates or not slot["required"],
                 "slot %r (required) 의 후보가 0개다 — category=%r side=%r allow=%r"
                 % (name, category, slot["side"], slot["allow"]))
        for part in (slot["allow"] or []):
            _require(part in parts[category],
                     "slot %r 의 allow 가 카탈로그에 없는 part %r 을 가리킨다" % (name, part))
        for part in slot["deny"]:
            _require(part in parts[category],
                     "slot %r 의 deny 가 카탈로그에 없는 part %r 을 가리킨다" % (name, part))
        if slot["follows"]:
            other = candidates_for(rule["slots"][slot["follows"]], catalog)
            _require(len(other) == len(candidates),
                     "slot %r 은 %r 을 follows 하는데 후보 수가 다르다 (%d vs %d)"
                     % (name, slot["follows"], len(candidates), len(other)))

    for arch in rule["archetypes"]:
        for slot_name, constraint in arch.get("constraints", {}).items():
            merged = merge_constraint(rule["slots"][slot_name], constraint)
            cands = candidates_for(merged, catalog)
            _require(cands or merged["none_weight"] > 0 or not merged["required"],
                     "archetype %r 의 slot %r 제약이 후보를 전부 없앴다"
                     % (arch["name"], slot_name))

    # 애니메이션 호환 정책.
    #   require_all  (기본) : 모든 후보가 모든 애니메이션을 지원해야 한다
    #   allow_subset        : 일부만 지원해도 된다. 미지원 애니메이션에서는 그 레이어를
    #                         숨긴다 (runtime 의 hide_layer 정책과 같은 규칙).
    # 기본을 require_all 로 두어 기존 규칙의 동작을 바꾸지 않는다.
    policy = rule.get("animation_policy", "require_all")
    _require(policy in ("require_all", "allow_subset"),
             "animation_policy 는 require_all 또는 allow_subset 이어야 한다 (현재: %r)"
             % policy)
    for anim in rule["animations"]:
        for name, slot in rule["slots"].items():
            covered = 0
            for part_name in candidates_for(slot, catalog):
                part = parts[slot["from"]][part_name]
                if anim in part["animations"]:
                    covered += 1
                    continue
                _require(policy == "allow_subset",
                         "animation %r 이 part %s/%s 에 없다 — animation compatibility 위반. "
                         "의도한 것이면 animation_policy: allow_subset 을 쓴다."
                         % (anim, slot["from"], part_name))
            if slot["required"] and policy == "allow_subset":
                _require(covered > 0,
                         "required slot %r 에 animation %r 을 지원하는 후보가 하나도 없다"
                         % (name, anim))


def _validate_palettes(rule, pal):
    pconf = rule.get("palettes")
    if not pconf:
        return
    _require("groups" in pconf, "palettes 에 groups 가 없다")
    tint_index = pconf.get("tint_index", 1)
    covered = set(pconf.get("untinted", []))
    for gname, group in pconf["groups"].items():
        _require("slots" in group and "ramps" in group,
                 "palette group %r 에 slots/ramps 가 필요하다" % gname)
        _require(group["ramps"], "palette group %r 의 ramps 가 비어 있다" % gname)
        for ramp_id in group["ramps"]:
            _require(ramp_id in pal["_by_id"],
                     "palette group %r 이 %s 에 없는 ramp %r 을 참조한다"
                     % (gname, pal["name"], ramp_id))
            _require(0 <= tint_index < len(pal["_by_id"][ramp_id]["colors"]),
                     "tint_index %d 가 ramp %r 범위를 벗어난다" % (tint_index, ramp_id))
        for slot_name in group["slots"]:
            _require(slot_name in rule["slots"],
                     "palette group %r 이 없는 slot %r 을 가리킨다" % (gname, slot_name))
            _require(slot_name not in covered,
                     "slot %r 이 두 palette group 에 중복 배정됐다" % slot_name)
            covered.add(slot_name)
    uncovered = [s for s in rule["slots"] if s not in covered]
    _require(not uncovered,
             "palette 배정이 없는 slot: %s — groups 에 넣거나 untinted 에 명시해라"
             % ", ".join(uncovered))


def merge_constraint(slot, constraint):
    """archetype 제약을 slot 기본값 위에 덮어쓴 새 dict 를 만든다 (원본 불변)."""
    merged = dict(slot)
    for key in ("allow", "deny", "none_weight", "required", "side"):
        if key in constraint:
            merged[key] = constraint[key]
    return merged


def candidates_for(slot, catalog):
    """slot 조건에 맞는 part 이름 목록. 항상 정렬된 순서 — 결정성의 전제."""
    parts = catalog["parts"].get(slot["from"], {})
    names = []
    for name in sorted(parts):
        part = parts[name]
        if slot.get("side") and part.get("side") != slot["side"]:
            continue
        if slot.get("allow") is not None and name not in slot["allow"]:
            continue
        if name in (slot.get("deny") or []):
            continue
        names.append(name)
    return names
