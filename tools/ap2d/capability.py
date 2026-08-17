"""팩마다 흩어진 「지금 무엇을 시킬 수 있는가」를 한 자리에 모은다.

발주하는 쪽이 카탈로그 4개 + summary 4개를 읽고서야 규칙을 쓸 수 있는 상태를
없애는 것이 목적이다. **새로 계산하지 않는다** — 스캐너와 라이선스 기록이 이미
계산해 둔 값을 모아 놓을 뿐이다. 그래서 여기에는 판정도 점수도 없다.

`02_CATALOG/CAPABILITIES.md` 가 산출물이고, 카탈로그가 바뀌면 다시 만든다.
사람이 손으로 고치지 않는다.
"""

import glob
import json
import os

from . import catalog as catalog_mod
from . import licensing, paths

SCHEMA = "ap2d.capabilities/1"


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def catalog_paths():
    """`.summary.md` 를 빼고 카탈로그 JSON 만. 경로 순으로 결정적이다."""
    return sorted(p for p in glob.glob(os.path.join(paths.CATALOG, "*.json"))
                  if not p.endswith(".summary.json"))


def _animations(pack):
    """카탈로그가 이미 아는 애니메이션 이름.

    팩마다 그 사실이 다른 자리에 있다 — 방향이 있는 팩은 `direction_axis`,
    프레임 시퀀스 팩은 `animation_bbox`. 둘의 합집합을 쓴다. 없으면 추론하지
    않고 빈 목록으로 둔다 (unknown 을 지어내지 않는다).
    """
    names = set()
    axis = pack.get("direction_axis") or {}
    names.update((axis.get("by_animation") or {}).keys())
    names.update((pack.get("animation_bbox") or {}).keys())
    return sorted(names)


def _slot_counts(cat):
    """슬롯별 후보 수. 규칙을 쓸 때 가장 먼저 필요한 숫자다."""
    return {slot: len(assets) for slot, assets in sorted((cat.get("parts") or {}).items())}


def _license(pack_name):
    """라이선스 3상태. 기록이 없으면 그 사실을 그대로 돌려준다."""
    try:
        return licensing.summarize(licensing.load(pack_name))
    except Exception as exc:                       # 기록 없음 · 필드 누락
        return {
            "pack": pack_name,
            "license": "unknown",
            "commercial_use": "unknown",
            "pipeline_approved": "unknown",
            "commercial_release_eligible": False,
            "error": str(exc),
        }


def pack_capability(catalog_path):
    cat = _read(catalog_path)
    pack = cat["pack"]
    caps = pack.get("capabilities") or {}
    axis = pack.get("direction_axis") or {}
    slots = _slot_counts(cat)
    return {
        "pack": pack["name"],
        "domain": pack.get("domain", "unknown"),
        "adapter": pack.get("adapter"),
        "catalog": paths.rel(catalog_path),
        "generation_mode": caps.get("generation_mode", "unknown"),
        "composable": caps.get("composable", "unknown"),
        "animation_compatible": caps.get("animation_compatible", "unknown"),
        "origin_policy": caps.get("origin_policy", "unknown"),
        "cell": caps.get("cell"),
        "slots": slots,
        "slot_total": sum(slots.values()),
        "combinations": _combinations(slots),
        "animations": _animations(pack),
        "direction_axis": {
            "present": axis.get("present", "unknown"),
            "values": axis.get("values") or [],
        },
        "license": _license(pack["name"]),
        "modular_part_count": pack.get("modular_part_count", 0),
        "subset": bool(pack.get("subset")),
    }


def _combinations(slots):
    """슬롯 후보를 전부 곱한 수. 제약을 걸기 전의 상한이다.

    실제 만들 수 있는 수는 규칙의 금지 조합만큼 이보다 적다. 그래서 '상한'이라고
    부르고, 이 값으로 무엇을 판정하지 않는다.
    """
    if not slots:
        return 0
    total = 1
    for count in slots.values():
        total *= max(count, 1)
    return total


def palettes():
    out = []
    for path in sorted(glob.glob(os.path.join(paths.REPO_ROOT, "03_PALETTES", "*.json"))):
        data = _read(path)
        ramps = data.get("ramps") or []
        groups = {}
        for ramp in ramps:
            groups.setdefault(ramp.get("group", "unknown"), 0)
            groups[ramp.get("group", "unknown")] += 1
        out.append({
            "file": paths.rel(path),
            "name": data.get("name", os.path.basename(path)),
            "example": os.path.basename(path).startswith("_example"),
            "ramps": len(ramps),
            "groups": dict(sorted(groups.items())),
            "ramp_length": len(ramps[0].get("colors", [])) if ramps else 0,
        })
    return out


def rules():
    """어떤 규칙이 어떤 팩/팔레트를 쓰는지. 발주 전 「이미 있는 것」 확인용."""
    out = []
    for path in sorted(glob.glob(os.path.join(paths.REPO_ROOT, "04_RULES", "*.json"))):
        data = _read(path)
        order = data.get("order") or {}
        seeds = []
        for archetype in data.get("archetypes") or []:
            spec = archetype.get("seeds") or {}
            if "from" in spec and "to" in spec:
                seeds.append("%s–%s" % (spec["from"], spec["to"]))
            elif isinstance(spec, list):
                seeds.append("%d개" % len(spec))
        out.append({
            "file": paths.rel(path),
            "id": data.get("id", os.path.basename(path)),
            "profile": data.get("profile"),
            "pack": data.get("pack"),
            "example": os.path.basename(path).startswith("_example"),
            "seeds": seeds,
            "animations": data.get("animations") or [],
            "purpose": order.get("purpose", "unknown"),
            "consumer": order.get("consumer", "unknown"),
        })
    return out


def build():
    return {
        "schema": SCHEMA,
        "packs": [pack_capability(p) for p in catalog_paths()],
        "palettes": palettes(),
        "rules": rules(),
    }


# ── 렌더 ────────────────────────────────────────────────────────────────

def _tri(value):
    return {"yes": "yes", "no": "**no**", "partial": "partial",
            "unknown": "unknown"}.get(value, str(value))


def render_markdown(data):
    L = ["# 가용 능력 — 지금 무엇을 시킬 수 있는가", ""]
    L.append("자동 생성됨: `python3 tools/capability_sheet.py`. 손으로 고치지 않는다.")
    L.append("")
    L.append("여기 있는 값은 전부 스캐너와 라이선스 기록이 **이미 계산한 사실**이다.")
    L.append("좋다/나쁘다는 판정은 없다 — 무엇이 가능한지만 적는다.")
    L.append("")

    # ── 팩 요약 ──
    L.append("## 팩")
    L.append("")
    L.append("| 팩 | 도메인 | generation_mode | composable | 셀 | 슬롯 | 조합 상한 |")
    L.append("|---|---|---|---|---|---:|---:|")
    for p in data["packs"]:
        cell = "%d×%d" % tuple(p["cell"]) if p["cell"] else "—"
        L.append("| `%s` | %s | %s | %s | %s | %d | %s |" % (
            p["pack"], p["domain"], p["generation_mode"], _tri(p["composable"]),
            cell, len(p["slots"]),
            "{:,}".format(p["combinations"]) if p["combinations"] else "—"))
    L.append("")
    L.append("`composable: no` 인 팩은 규칙을 써도 조합이 되지 않는다. "
             "이유는 각 팩 절에 적혀 있다.")
    L.append("")

    # ── 팩별 상세 ──
    for p in data["packs"]:
        L.append("### `%s`" % p["pack"])
        L.append("")
        if p["composable"] != "yes":
            L.append("> 이 팩은 **조합 대상이 아니다** (`composable: %s`, "
                     "`generation_mode: %s`). 발주 대상에서 제외한다."
                     % (p["composable"], p["generation_mode"]))
            L.append("")

        if p["slots"]:
            L.append("**슬롯별 후보**")
            L.append("")
            L.append("| " + " | ".join(p["slots"].keys()) + " |")
            L.append("|" + "---:|" * len(p["slots"]))
            L.append("| " + " | ".join(str(v) for v in p["slots"].values()) + " |")
            L.append("")
            L.append("파츠 %d개 · 제약 없이 곱하면 **%s 조합**."
                     % (p["slot_total"], "{:,}".format(p["combinations"])))
            if p["subset"]:
                L.append("이 카탈로그는 팩 전체가 아니라 **선별된 subset** 이다 "
                         "(기준은 카탈로그의 `subset.criteria`).")
            L.append("")
        else:
            L.append("모듈 슬롯 없음 — 파츠가 분리되지 않는다.")
            L.append("")

        axis = p["direction_axis"]
        L.append("| 축 | 값 |")
        L.append("|---|---|")
        L.append("| 애니메이션 | %s |" % (
            " · ".join("`%s`" % a for a in p["animations"]) if p["animations"] else "unknown"))
        L.append("| 방향 | %s |" % (
            "%d개 — %s" % (len(axis["values"]), " · ".join(axis["values"]))
            if axis["present"] == "yes" else axis["present"]))
        L.append("| animation_compatible | %s |" % _tri(p["animation_compatible"]))
        L.append("| origin_policy | %s |" % p["origin_policy"])
        L.append("")

        lic = p["license"]
        L.append("**라이선스**")
        L.append("")
        L.append("| license | commercial_use | pipeline_approved | commercial_release_eligible |")
        L.append("|---|---|---|---|")
        L.append("| `%s` | %s | %s | **%s** |" % (
            lic.get("license"), _tri(lic.get("commercial_use")),
            _tri(lic.get("pipeline_approved")),
            str(lic.get("commercial_release_eligible")).lower()))
        L.append("")
        if not lic.get("commercial_release_eligible"):
            L.append("> ⛔ 이 팩에서 나온 결과물은 **상업 출시 대상이 아니다.** "
                     "생성은 막지 않지만 신호는 산출물까지 따라간다.")
            L.append("")

    # ── 팔레트 ──
    L.append("## 팔레트")
    L.append("")
    if data["palettes"]:
        L.append("| 파일 | 램프 | 그룹 | 램프 길이 |")
        L.append("|---|---:|---|---:|")
        for pal in data["palettes"]:
            groups = " · ".join("%s %d" % (g, n) for g, n in pal["groups"].items())
            L.append("| `%s`%s | %d | %s | %d |" % (
                pal["file"], " (예시)" if pal["example"] else "",
                pal["ramps"], groups or "—", pal["ramp_length"]))
        L.append("")
        L.append("팔레트는 팩에 묶여 있지 않다. 규칙이 골라 쓴다.")
        L.append("")
    else:
        L.append("없음.")
        L.append("")

    # ── 이미 있는 규칙 ──
    L.append("## 이미 있는 규칙")
    L.append("")
    L.append("| 규칙 | 프로파일 | 팩 | seed | 애니메이션 | 성격 | 소비자 |")
    L.append("|---|---|---|---|---|---|---|")
    for r in data["rules"]:
        if r["example"]:
            continue
        L.append("| `%s` | `%s` | `%s` | %s | %s | %s | %s |" % (
            os.path.basename(r["file"]), r["profile"], r["pack"],
            " · ".join(r["seeds"]) or "—",
            " · ".join(r["animations"]) or "—",
            r["purpose"], r["consumer"]))
    L.append("")
    L.append("`성격` 은 이 산출물이 자체 기술 검증인지 발주 대응인지를 뜻한다 "
             "(`04_RULES/<규칙>.json` 의 `order.purpose`). `unknown` 은 규칙이 아직 "
             "선언하지 않았다는 뜻이고, 그 자체로 정당한 값이다.")
    L.append("")
    return "\n".join(L)


def write(data=None, md_path=None):
    data = data or build()
    md_path = md_path or os.path.join(paths.CATALOG, "CAPABILITIES.md")
    paths.assert_writable(md_path)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(data))
    return md_path
