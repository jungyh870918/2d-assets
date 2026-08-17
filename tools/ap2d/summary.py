"""02_CATALOG/<pack>.summary.md — 사람이 카탈로그를 검토하기 위한 요약.

CLAUDE.md: "스캔/검증 결과는 항상 파일로 남긴다. 터미널 출력만으로 끝내지 않는다."
"""

import collections
import os

from . import licensing, paths


KIND_MEANING = {
    "character_part": "조합 가능한 신체 파츠 (generation 후보)",
    "composed_character": "캐릭터 전체가 그려진 완성 이미지",
    "environment_tile": "타일 격자 기반 환경/타일셋 이미지",
    "prop": "단품 오브젝트 이미지",
    "animation_frame": "시퀀스의 한 프레임이지만 파츠 의미는 미확정",
    "spritesheet": "격자는 확인됐으나 내용 미상",
    "source_document": "라이선스/README/레이어 소스 등 비이미지",
    "unknown": "판단 불가 — 추측하지 않고 남겨둔 것",
}


CAPABILITY_MEANING = {
    "parts_separable": "조합할 파츠가 개별 주소로 존재하는가",
    "shared_canvas": "합성 대상 이미지가 한 캔버스를 쓰는가",
    "pre_aligned": "파츠가 사전 정렬되어 alpha-over 만으로 합성되는가",
    "shared_origin": "파츠가 원점을 공유하는가",
    "animation_compatible": "모든 파츠가 같은 애니메이션 집합을 갖는가",
    "directional": "방향 변형이 있는가",
    "composable": "**modular composition 이 가능한가** (위 셋의 곱)",
    "origin_policy": "pivot 의 근거. 자동 검출은 하지 않는다",
}

GENERATION_MODE_MEANING = {
    "modular_composition": "파츠를 골라 합성한다. compose.py 의 입력이 된다",
    "composed_sheet": "완성 캐릭터 시트다. 파츠 교체 불가 — compose.py 입력이 아니다",
    "unsupported": "캐릭터 생성 대상이 아니다",
}

UNSUPPORTED_REASON = {
    "composed_sheets_only": "파츠가 없고 완성 캐릭터 시트만 있다",
    "atlas_only_no_individual_props": "전부 아틀라스라 개별 주소를 가진 오브젝트가 없다",
    "no_modular_parts": "조합 가능한 파츠를 찾지 못했다",
    "incompatible_parts": "파츠는 있으나 캔버스/애니메이션이 서로 맞지 않는다",
    "no_images": "이미지가 없다",
}


def _capability_table(caps, direction_axis=None):
    if not caps:
        return []
    mode = caps.get("generation_mode", "unknown")
    L = ["## generation capability", ""]
    L.append("generator 가 암묵적으로 전제하던 조건을 명시적으로 계산한 값이다. "
             "증명할 수 없으면 `no` 가 아니라 `unknown` 이다.")
    L.append("")
    L.append("| capability | 값 | 뜻 |")
    L.append("|---|---|---|")
    for key, meaning in CAPABILITY_MEANING.items():
        L.append("| `%s` | `%s` | %s |" % (key, caps.get(key, "unknown"), meaning))
    L.append("")
    L.append("### generation_mode: `%s`" % mode)
    L.append("")
    L.append(GENERATION_MODE_MEANING.get(mode, mode) + ".")
    L.append("")
    if mode != "modular_composition":
        reason = caps.get("reason", "unknown")
        L.append("```")
        L.append("generation_mode: %s" % mode)
        L.append("reason: %s" % reason)
        L.append("```")
        L.append("")
        L.append("%s. `compose.py` 는 modular composition 전용 엔진이라 이 팩을 받으면 "
                 "`UnsupportedModeError` 로 즉시 멈춘다 — 실패가 아니라 명시적 SKIP 이다. "
                 "이미 합성된 시트를 통과시키기 위한 예외 코드는 넣지 않는다."
                 % UNSUPPORTED_REASON.get(reason, reason))
        L.append("")

    axis = direction_axis or {}
    L.append("### direction 축")
    L.append("")
    L.append("| 항목 | 값 |")
    L.append("|---|---|")
    L.append("| `present` | `%s` |" % axis.get("present", "unknown"))
    L.append("| `encoding` | `%s` |" % axis.get("encoding", "unknown"))
    L.append("| `values` | %s |" % (", ".join("`%s`" % v for v in axis.get("values", []))
                                    or "—"))
    L.append("")
    if axis.get("present") != "yes":
        L.append("파일명에서 방향을 찾지 못했다. **이는 '방향이 없다'는 뜻이 아니다** — "
                 "방향을 시트의 행에 담는 팩이 실제로 존재하고, 그런 팩은 파일명만 "
                 "봐서는 알 수 없다. 그래서 `no` 가 아니라 `unknown` 이다.")
        L.append("")
    return L


def _license_summary(pack_name):
    """라이선스 기록이 있으면 요약을 붙인다. 없으면 None (스캔 자체는 막지 않는다)."""
    try:
        return licensing.summarize(licensing.load(pack_name))
    except licensing.LicenseError:
        return None


def _counter_table(title, counter, columns=("값", "개수")):
    if not counter:
        return []
    lines = ["### %s" % title, "", "| %s | %s |" % columns, "|---|---:|"]
    for key, count in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        lines.append("| `%s` | %d |" % (key, count))
    lines.append("")
    return lines


def find_anomalies(cat):
    """파이프라인에 넣기 전에 사람이 봐야 할 것들."""
    entries = cat["entries"]
    images = [e for e in entries if e["file_type"] == "image"]
    anomalies = []

    broken = [e for e in images if "error" in e.get("image", {})]
    if broken:
        anomalies.append(("이미지 열기 실패", [e["pack_path"] for e in broken]))

    # 프레임인데 파츠 의미를 못 읽은 것 = 조합 후보로 올리지 않은 것
    unclassified = [e for e in images
                    if e["inferred"]["asset_kind"] in ("animation_frame",
                                                       "composed_character")]
    if unclassified:
        # group(경로 첫 조각)은 zip 이 래퍼 폴더 하나로 감싸져 있으면 전부 같은 값이라
        # 쓸모가 없다. 실제 디렉터리를 보여준다.
        dirs = sorted(set(os.path.dirname(e["pack_path"]) for e in unclassified))
        anomalies.append((
            "파츠로 확정하지 않은 이미지 %d장 (character_part 후보에서 제외)"
            % len(unclassified),
            dirs[:12] + (["… 외 %d개 폴더" % (len(dirs) - 12)] if len(dirs) > 12 else []),
        ))

    # 프레임 번호처럼 보였지만 시퀀스가 아니었던 것 — 오탐을 잡은 지점이라 남긴다
    demoted = [e for e in images if e["inferred"].get("variant_index") is not None]
    if demoted:
        dirs = sorted(set(os.path.dirname(e["pack_path"]) for e in demoted))
        anomalies.append((
            "파일명 끝 번호가 프레임이 아니었던 이미지 %d장 "
            "(번호가 연속이 아니라 variant_index 로 되돌림)" % len(demoted),
            dirs[:8],
        ))

    # 격자인 건 알겠는데 내용을 모르는 시트
    opaque_sheets = [e for e in images
                     if e["inferred"]["asset_kind"] == "spritesheet"]
    if opaque_sheets:
        anomalies.append((
            "정체 미상 시트 %d장 (격자는 확인됐으나 무엇의 격자인지 추론 불가)"
            % len(opaque_sheets),
            [e["pack_path"] for e in opaque_sheets][:10],
        ))

    # 알파 없는 이미지 — 레이어 합성에 쓸 수 없다
    opaque = [e for e in images
              if "error" not in e.get("image", {}) and not e["image"]["has_alpha"]]
    if opaque:
        anomalies.append(("알파 채널 없음 (레이어 합성 불가)",
                          [e["pack_path"] for e in opaque][:20]))

    # 캔버스가 팩 표준과 다른 것
    canvas = cat["pack"].get("canvas")
    if canvas:
        odd = [e for e in images
               if "error" not in e.get("image", {})
               and e["image"]["dimensions"] != canvas]
        if odd:
            anomalies.append((
                "팩 표준 캔버스 %dx%d 와 다른 이미지" % (canvas[0], canvas[1]),
                ["%s (%dx%d)" % (e["pack_path"], *e["image"]["dimensions"])
                 for e in odd][:20],
            ))

    # 파트별 프레임 수 불일치
    per_anim = collections.defaultdict(set)
    for cat_name, parts in cat["parts"].items():
        for part_name, part in parts.items():
            for anim, info in part["animations"].items():
                per_anim[anim].add(info["frame_count"])
    ragged = {a: sorted(v) for a, v in per_anim.items() if len(v) > 1}
    if ragged:
        anomalies.append(("애니메이션별 프레임 수 불일치",
                          ["%s: %s" % (a, v) for a, v in sorted(ragged.items())]))

    return anomalies


def duplicate_hashes(cat):
    by_hash = collections.defaultdict(list)
    for e in cat["entries"]:
        by_hash[e["sha256"]].append(e["pack_path"])
    return {h: sorted(v) for h, v in by_hash.items() if len(v) > 1}


def render(cat):
    pack = cat["pack"]
    entries = cat["entries"]
    images = [e for e in entries if e["file_type"] == "image"]

    categories = collections.Counter(e["inferred"]["category"] for e in images)
    # asset_kind 는 비이미지(source_document)까지 포함해야 합계가 파일 수와 맞는다.
    kinds = collections.Counter(e["inferred"]["asset_kind"] for e in entries)
    packaging = collections.Counter(e["inferred"]["packaging"] for e in images)
    animations = collections.Counter(
        e["inferred"]["animation"] for e in images
        if e["inferred"]["asset_kind"] == "character_part")
    directions = collections.Counter(e["inferred"]["direction"] for e in images)
    sides = collections.Counter(e["inferred"]["side"] for e in images)
    dims = collections.Counter(
        "%dx%d" % tuple(e["image"]["dimensions"])
        for e in images if "error" not in e.get("image", {}))
    filetypes = collections.Counter(e["file_type"] for e in entries)

    unknown_counts = collections.Counter()
    for e in images:
        for field in ("category", "part", "animation", "direction", "side"):
            if e["inferred"][field] in ("unknown", None):
                unknown_counts[field] += 1

    dupes = duplicate_hashes(cat)
    anomalies = find_anomalies(cat)

    lic = _license_summary(pack["name"])

    L = []
    L.append("# %s — 카탈로그 요약" % pack["name"])
    L.append("")
    L.append("자동 생성됨: `tools/scan_pack.py`. 손으로 고치지 않는다.")
    L.append("")
    if lic and not lic["commercial_release_eligible"]:
        L.append("> ⛔ **%s**" % licensing.NONCOMMERCIAL_BANNER)
        L.append(">")
        L.append("> 라이선스: `%s` · `commercial_use: %s` · 기록: `%s`"
                 % (lic["license"], lic["commercial_use"], lic["record"]))
        L.append("")
    L.append("| 항목 | 값 |")
    L.append("|---|---|")
    L.append("| 소스 경로 | `%s` |" % pack["root"])
    L.append("| 총 파일 수 | %d |" % pack["file_count"])
    L.append("| 이미지 수 | %d |" % pack["image_count"])
    L.append("| character_part 프레임 수 | %d |" % pack["modular_part_count"])
    if lic:
        L.append("| 라이선스 | `%s` |" % lic["license"])
        L.append("| 상업적 사용 | `%s` |" % lic["commercial_use"])
        L.append("| commercial_release_eligible | **%s** |"
                 % str(lic["commercial_release_eligible"]).lower())
    L.append("| 팩 표준 캔버스 | %s |" %
             ("%dx%d" % tuple(pack["canvas"]) if pack["canvas"] else "일관되지 않음"))
    L.append("| pre-aligned (단순 합성 가능) | %s |" % ("예" if pack["pre_aligned"] else "아니오"))
    L.append("| 내용 bbox (전 파츠 합집합) | %s |" % (pack["content_bbox"] or "-"))
    L.append("| 중복 hash 그룹 | %d |" % len(dupes))
    if pack.get("declared_tile_sizes"):
        L.append("| 선언된 타일 크기 | %s |" % ", ".join(
            "`%s`×%d" % (k, v) for k, v in pack["declared_tile_sizes"].items()))
    L.append("")

    L += _capability_table(pack.get("capabilities", {}),
                           pack.get("direction_axis"))

    L.append("## asset kind")
    L.append("")
    L.append("| asset_kind | 파일 수 | 뜻 |")
    L.append("|---|---:|---|")
    for key in ("character_part", "composed_character", "environment_tile",
                "prop", "animation_frame", "spritesheet", "source_document",
                "unknown"):
        L.append("| `%s` | %d | %s |" % (key, kinds.get(key, 0), KIND_MEANING[key]))
    L.append("| **합계** | **%d** | |" % sum(kinds.values()))
    L.append("")
    L.append("`character_part` 만 조합(generation) 후보다. 나머지는 카탈로그에 기록만 된다.")
    L.append("")

    L += _counter_table("packaging (sheet / individual / sequence)", packaging,
                        ("packaging", "이미지 수"))

    if pack.get("scale_variant_groups"):
        L.append("### 배율본 후보 (scale_variant_candidate)")
        L.append("")
        L.append("파일명의 타일 크기 토큰만 다르고 치수 비율이 정확히 일치하는 그룹이다. "
                 "**픽셀을 비교한 것이 아니므로 내용이 같다고 증명된 것은 아니다.**")
        L.append("")
        for key, files in pack["scale_variant_groups"].items():
            L.append("- `%s` — %d개: %s" % (key, len(files),
                                            ", ".join("`%s`" % os.path.basename(f)
                                                      for f in files)))
        L.append("")

    if cat["parts"]:
        L.append("## 발견된 파츠 (조합 가능)")
        L.append("")
        L.append("| category | part | side | 애니메이션 | 총 프레임 |")
        L.append("|---|---|---|---|---:|")
        for cat_name, parts in cat["parts"].items():
            for part_name, part in parts.items():
                L.append("| `%s` | `%s` | %s | %s | %d |" % (
                    cat_name, part_name, part["side"],
                    ", ".join(part["animations"].keys()), part["frame_total"]))
        L.append("")
    else:
        L.append("## 발견된 파츠 (조합 가능)")
        L.append("")
        L.append("**없음.** 이 팩에서는 조합 가능한 modular character part 를 하나도 "
                 "찾지 못했다. generation 규칙을 쓸 수 있는 소재가 없다는 뜻이다.")
        L.append("")

    L.append("## 분포")
    L.append("")
    L += _counter_table("category (body part 어휘 전용)", categories,
                        ("category", "이미지 수"))
    L += _counter_table("animation (character_part 만)", animations,
                        ("animation", "프레임 수"))
    L += _counter_table("direction", directions, ("direction", "이미지 수"))
    L += _counter_table("side", sides, ("side", "이미지 수"))
    L += _counter_table("해상도", dims, ("해상도", "이미지 수"))
    L += _counter_table("파일 타입", filetypes, ("file_type", "파일 수"))

    L.append("### unknown 분류 수")
    L.append("")
    L.append("| 필드 | unknown 이미지 수 |")
    L.append("|---|---:|")
    for field in ("category", "part", "animation", "direction", "side"):
        L.append("| %s | %d |" % (field, unknown_counts.get(field, 0)))
    L.append("")

    L.append("## naming anomaly / 잠재 문제")
    L.append("")
    if not anomalies:
        L.append("발견된 문제 없음.")
        L.append("")
    for title, items in anomalies:
        L.append("- **%s**" % title)
        for item in items:
            L.append("  - `%s`" % item)
        L.append("")

    L.append("## 중복 hash")
    L.append("")
    if not dupes:
        L.append("없음.")
    else:
        L.append("바이트가 동일한 파일 그룹 %d개. 프레임이 실제로 안 움직이는 구간이라는 뜻이라"
                 " 반드시 오류는 아니다." % len(dupes))
        L.append("")
        shown = sorted(dupes.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:15]
        for h, files in shown:
            L.append("- `%s…` × %d — %s" % (h[:12], len(files), ", ".join(
                "`%s`" % f for f in files[:4]) + (" …" if len(files) > 4 else "")))
        if len(dupes) > 15:
            L.append("- … 외 %d 그룹" % (len(dupes) - 15))
    L.append("")

    L.append("## 파이프라인 적용 시 주의")
    L.append("")
    for note in pipeline_notes(cat, dupes, unknown_counts):
        L.append("- %s" % note)
    L.append("")
    L += _variation_feasibility(cat)
    return "\n".join(L)


def _variation_feasibility(cat):
    """이 팩으로 variation 생성이 가능한지, 안 되면 무엇이 없어서인지.

    카탈로그 수치에서 바로 나오는 판정이다. 손으로 쓴 결론이 아니라 재생성된다.
    """
    pack = cat["pack"]
    kinds = pack.get("asset_kinds", {})
    parts = sum(len(p) for p in cat["parts"].values())
    props = kinds.get("prop", 0)
    tiles = kinds.get("environment_tile", 0)
    sheets = kinds.get("spritesheet", 0)

    L = ["## variation 생성 가능성", ""]
    L.append("| 축 | 필요한 것 | 이 팩 | 판정 |")
    L.append("|---|---|---:|---|")
    L.append("| character variation | 조합 가능한 character_part | %d종 | %s |"
             % (parts, "가능" if parts >= 2 else "**불가**"))
    L.append("| environment variation | 개별 주소를 가진 prop | %d개 | %s |"
             % (props, "가능" if props >= 2 else "**불가**"))
    L.append("")

    if parts >= 2:
        L.append("character variation 은 `04_RULES/` 에 규칙을 쓰면 바로 생성 가능하다.")
        L.append("")
    if props < 2 and (tiles or sheets):
        L.append("### Environment variation POC: `SKIPPED`")
        L.append("")
        L.append("> `SKIPPED — source pack does not expose individually addressable "
                 "semantic props without atlas slicing/manual labeling`")
        L.append("")
        L.append("**어떤 구조 때문에 불가능한가**")
        L.append("")
        L.append("- 환경 이미지 %d장이 전부 아틀라스/시트다 (environment_tile %d, "
                 "spritesheet %d). packaging 이 `individual` 인 환경 이미지가 없다."
                 % (tiles + sheets, tiles, sheets))
        L.append("- 개별 prop PNG 가 **%d개**다. 조합 슬롯(floor / wall / table / chair "
                 "/ decoration)에 넣을 수 있는 주소 단위가 존재하지 않는다." % props)
        L.append("- 아틀라스를 잘라도 격자 칸 하나가 의자인지 책상인지는 파일명·폴더명에 "
                 "적혀 있지 않다. 알아내려면 사람이 눈으로 보고 칸마다 라벨을 붙여야 한다.")
        L.append("")
        L.append("**따라서 필요한 두 가지가 모두 이번 범위 밖이다**")
        L.append("")
        L.append("1. atlas 자동 slicing")
        L.append("2. 격자 칸 semantic labeling (수동 매핑)")
        L.append("")
        L.append("억지로 만들면 카탈로그에 근거 없는 분류가 들어간다. 하지 않는다.")
        L.append("")
        L.append("**어떤 조건이면 POC 가 가능한가**")
        L.append("")
        L.append("- prop 이 개별 PNG 로 분리되어 있고 (`packaging: individual`),")
        L.append("- 파일명이나 폴더명이 종류를 말해주며 "
                 "(`chairs/office_chair_01.png` 처럼),")
        L.append("- 같은 종류 안에 변형이 2개 이상 있을 것.")
        L.append("")
        L.append("세 조건을 만족하면 현재 generator 의 slot/rule/seed 구조를 "
                 "거의 그대로 재사용할 수 있다. 슬롯 이름만 다르고 메커니즘은 동일하다.")
        L.append("")
        if pack.get("declared_tile_sizes"):
            L.append("격자 정보(`inferred.grid`: columns/rows/cells)와 선언된 타일 크기는 "
                     "이미 카탈로그에 기록해 두었다. 나중에 slicing 단계를 만들 때 "
                     "다시 스캔할 필요는 없다.")
            L.append("")
    return L


def pipeline_notes(cat, dupes, unknown_counts):
    pack = cat["pack"]
    kinds = pack.get("asset_kinds", {})
    notes = []

    if not cat["parts"]:
        notes.append(
            "**조합 가능한 character part 가 0개다.** 이 팩은 현재 generator 의 "
            "입력이 될 수 없다. character_part 는 (신체 파츠 어휘 확정 + 검증된 "
            "프레임 시퀀스) 두 조건을 모두 만족해야 하는데 하나도 만족하지 못했다.")
    if kinds.get("prop", 0) == 0 and kinds.get("environment_tile", 0):
        notes.append(
            "**개별 prop 이미지가 0개다** (environment_tile %d장 / spritesheet %d장). "
            "환경 오브젝트가 전부 아틀라스 안에 들어 있어서, 개별 주소를 가진 소품이 "
            "존재하지 않는다. floor/wall/table/chair 조합을 하려면 아틀라스 slicing 과 "
            "격자 칸 semantic labeling 이 선행되어야 한다 — 둘 다 현재 범위 밖이다."
            % (kinds.get("environment_tile", 0), kinds.get("spritesheet", 0)))
    if pack.get("declared_tile_sizes"):
        notes.append(
            "팩이 파일명에 타일 크기를 직접 적어두었다 (%s). 추론이 아니라 팩이 "
            "선언한 값이므로 그대로 신뢰해 격자 정합을 검사했다. 향후 slicing 이나 "
            "Sprite Library 전환에 필요한 격자 정보(columns/rows/cells)는 각 엔트리의 "
            "`inferred.grid` 에 이미 들어 있다."
            % ", ".join(pack["declared_tile_sizes"]))
    if pack.get("scale_variant_groups"):
        notes.append(
            "같은 내용의 배율본이 %d 그룹 있다. SHA 가 다르므로 중복 hash 검사에는 "
            "걸리지 않는다. 한 배율만 골라 쓰고 나머지는 파이프라인에서 제외해야 "
            "카탈로그와 아틀라스가 3배로 부풀지 않는다."
            % len(pack["scale_variant_groups"]))

    if pack["pre_aligned"]:
        notes.append(
            "모든 modular part 가 %dx%d 동일 캔버스에 사전 정렬되어 있다. "
            "pivot 계산 없이 alpha-over 합성만으로 캐릭터가 만들어진다."
            % tuple(pack["canvas"]))
        if pack["content_bbox"]:
            bb = pack["content_bbox"]
            notes.append(
                "실제 내용은 캔버스의 %d×%d 영역(%s)에만 있다. 합성 전에 이 사각형으로 "
                "잘라야 메모리/시간이 %.0f배 절약된다."
                % (bb[2] - bb[0], bb[3] - bb[1], bb,
                   (pack["canvas"][0] * pack["canvas"][1]) /
                   float((bb[2] - bb[0]) * (bb[3] - bb[1]))))
    elif cat["parts"]:
        notes.append("캔버스가 파츠마다 다르다. 합성 전에 pivot/offset 정규화가 필요하다.")

    single = [c for c, parts in cat["parts"].items() if len(parts) == 1]
    if single:
        notes.append(
            "변형이 1개뿐인 category: %s — 이 슬롯들은 variation 에 기여하지 못한다."
            % ", ".join("`%s`" % c for c in single))

    if cat["parts"] and unknown_counts.get("direction"):
        notes.append(
            "방향 변형이 없다(direction 전부 unknown). 좌우 반전이 필요하면 "
            "flip 으로 만들어야 하며, 팩이 side-view 라 8방향 게임에는 그대로 못 쓴다.")

    if dupes:
        notes.append(
            "중복 hash 그룹 %d개. 스프라이트 아틀라스에서 중복 프레임을 합치면 용량이 줄어든다."
            % len(dupes))

    comp = kinds.get("composed_character", 0)
    if comp:
        notes.append(
            "완성된 캐릭터 이미지 %d장이 섞여 있다. 조합 소스가 아니라 참조용이므로 "
            "generator 후보에서 제외된다." % comp)
    return notes


def write(cat, out_path):
    paths.ensure_dir(os.path.dirname(out_path))
    with open(paths.assert_writable(out_path), "w", encoding="utf-8") as fh:
        fh.write(render(cat))
    return out_path
