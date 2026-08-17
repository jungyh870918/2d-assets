#!/usr/bin/env python3
"""LPC generator 저장소에서 Phase 1 subset 을 01_SOURCE 로 ingest 한다.

    python3 tools/ingest_lpc_subset.py <LPC 저장소 경로>

88,114장을 전부 넣지 않는다. metadata(sheet_definitions / CREDITS.csv / LICENSE)는
전부 가져오고, 스프라이트는 선택 기준을 만족하는 slot subset 만 가져온다.
선택은 LPC metadata 기반으로 **결정적**이며 사람이 파일명을 보고 고르지 않는다.
"""

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import paths  # noqa: E402
from ap2d.packs import lpc  # noqa: E402

PACK = "lpc_ulpc-generator_phase1"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="LPC generator 저장소 경로 (읽기 전용으로 사용)")
    ap.add_argument("--pack", default=PACK)
    ap.add_argument("--dry-run", action="store_true", help="선택 결과만 보고 복사하지 않는다")
    args = ap.parse_args(argv)

    src = os.path.abspath(args.source)
    if not os.path.isdir(os.path.join(src, "sheet_definitions")):
        raise SystemExit("LPC 저장소가 아니다 (sheet_definitions 없음): %s" % src)

    subset = lpc.select_subset(src, extras=lpc.PHASE2_EXTRAS)
    print("후보 수:", subset["candidate_counts"])
    print("제외 사유:", subset["rejected_counts"])
    total = 0
    for slot in sorted(subset["selected"]):
        items = subset["selected"][slot]
        total += len(items)
        print("  %-6s %d개: %s" % (slot, len(items),
                                   ", ".join(a["id"] for a in items)))
    if subset.get("extras"):
        for kind, ids in subset["extras"].items():
            print("  [extra] %-18s %s" % (kind, ", ".join(ids) or "(없음)"))
    if subset["shortfall"]:
        raise SystemExit("목표 수를 못 채운 슬롯이 있다: %s" % subset["shortfall"])
    print("선택 asset %d개" % total)
    if args.dry_run:
        return 0

    dest = os.path.join(paths.SOURCE, "characters", args.pack)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest)

    copied = 0
    # 1) metadata 전체
    for rel in ("CREDITS.csv", "LICENSE"):
        s = os.path.join(src, rel)
        if os.path.isfile(s):
            shutil.copy2(s, os.path.join(dest, rel))
            copied += 1
    shutil.copytree(os.path.join(src, "sheet_definitions"),
                    os.path.join(dest, "sheet_definitions"))
    copied += sum(len(f) for _r, _d, f in os.walk(os.path.join(dest, "sheet_definitions")))

    # 2) 선택된 슬롯의 idle/walk/run 시트만
    sheets = 0
    for slot in sorted(subset["selected"]):
        for asset in subset["selected"][slot]:
            # multi-layer 자산은 레이어마다 별도 경로를 갖는다. 전부 가져온다.
            bases = ([(l["base"], l["animations"]) for l in asset["visual_layers"]]
                     if asset.get("visual_layers")
                     else [(asset["base"], asset["animations"])])
            for base, anims in bases:
                for animation in sorted(anims):
                    s = lpc.sheet_path(src, base, animation)
                    d = os.path.join(dest, "spritesheets",
                                     base.replace("/", os.sep), animation + ".png")
                    os.makedirs(os.path.dirname(d), exist_ok=True)
                    shutil.copy2(s, d)
                    sheets += 1
    copied += sheets
    print("복사: metadata + 시트 %d장 (총 %d 파일) -> %s"
          % (sheets, copied, paths.rel(dest)))

    _write_manifest(subset, src, args.pack)
    print("  -> 00_DOCS/lpc-phase1-subset.md")
    return 0


def _write_manifest(subset, src, pack):
    lines = ["# LPC Phase 1 subset — 선택 기준과 결과", ""]
    lines.append("자동 생성됨: `tools/ingest_lpc_subset.py`. 손으로 고치지 않는다.")
    lines.append("")
    lines.append("- 원본 저장소: https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator")
    lines.append("- 팩 폴더: `01_SOURCE/characters/%s`" % pack)
    lines.append("- body type: **%s** 한 종류" % subset["body_type"])
    lines.append("- 애니메이션: %s" % ", ".join("`%s`" % a for a in sorted(subset["animations"])))
    lines.append("- 논리 셀: **%dx%d** (팩 상수. 자동 격자 검출을 하지 않는다)"
                 % (subset["cell"], subset["cell"]))
    lines.append("- 방향 행 순서: %s" % ", ".join("`%s`" % d for d in subset["direction_rows"]))
    lines.append("")
    lines.append("## 선택 기준")
    lines.append("")
    lines.append("사람이 파일명을 보고 고르지 않는다. 아래 기준을 순서대로 적용하고, "
                 "통과한 후보를 **정의 파일 경로순**으로 정렬해 앞에서 취한다.")
    lines.append("")
    for i, c in enumerate(subset["criteria"], 1):
        lines.append("%d. %s" % (i, c))
    lines.append("")
    lines.append("## 선택 결과")
    lines.append("")
    lines.append("| slot | 목표 | 후보 | 선택된 asset | zPos | selected license |")
    lines.append("|---|---:|---:|---|---:|---|")
    for slot in sorted(subset["selected"]):
        for asset in subset["selected"][slot]:
            lic = sorted(set(c["selected_license"] for c in asset["credits"]))
            lines.append("| `%s` | %d | %d | `%s` (%s) | %s | %s |" % (
                slot, subset["targets"].get(slot, 0),
                subset["candidate_counts"].get(slot, 0),
                asset["id"], asset["name"], asset["z_pos"],
                ", ".join("`%s`" % l for l in lic)))
    lines.append("")
    lines.append("## 제외 사유별 정의 수")
    lines.append("")
    lines.append("| 사유 | 수 |")
    lines.append("|---|---:|")
    for reason, count in subset["rejected_counts"].items():
        lines.append("| `%s` | %d |" % (reason, count))
    lines.append("")
    lines.append("`license_not_permissive` 는 CC-BY-SA / GPL 만 제공하는 asset 이다. "
                 "Phase 1 은 share-alike 를 배제한다.")
    lines.append("")
    lines.append("## 라이선스 선택 정책")
    lines.append("")
    lines.append("다중 라이선스 asset 은 **CC0 > OGA-BY > CC-BY** 순으로 하나를 명시적으로 "
                 "고르고, 고르지 못하면 제외한다. 고른 값과 나머지 선택지를 둘 다 기록한다.")
    lines.append("")
    path = os.path.join(paths.DOCS, "lpc-phase1-subset.md")
    with open(paths.assert_writable(path), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    json_path = os.path.join(paths.DOCS, "lpc-phase1-subset.json")
    payload = {k: v for k, v in subset.items() if k != "selected"}
    payload["selected"] = subset["selected"]
    with open(paths.assert_writable(json_path), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


if __name__ == "__main__":
    raise SystemExit(main())
