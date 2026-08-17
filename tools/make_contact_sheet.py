#!/usr/bin/env python3
"""생성 결과를 한 장으로 모은 contact sheet 를 만든다.

    python3 tools/make_contact_sheet.py cc0_test_population
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import contactsheet, paths  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("profile", help="05_GENERATED/characters 아래 profile 이름")
    ap.add_argument("--out", help="출력 PNG (기본: 05_GENERATED/reports/<profile>.png)")
    ap.add_argument("--rule", help="라벨 슬롯 순서를 정할 규칙 JSON (선택)")
    ap.add_argument("--columns", type=int, default=5)
    ap.add_argument("--cell", type=int, default=300)
    args = ap.parse_args(argv)

    profile_dir = os.path.join(paths.GEN_CHARACTERS, args.profile)
    out = paths.abspath(args.out) if args.out else os.path.join(
        paths.GEN_REPORTS, args.profile + ".png")

    rule = None
    if args.rule:
        with open(paths.abspath(args.rule), "r", encoding="utf-8") as fh:
            rule = json.load(fh)

    path, count = contactsheet.build(
        profile_dir, out, columns=args.columns, cell=args.cell,
        title=args.profile, rule=rule)
    print("contact sheet %d칸 -> %s" % (count, paths.rel(path)))

    # 방향 축이 있는 팩은 방향별 정렬 확인용 이미지도 남긴다.
    # 좌표가 맞아도 레이어가 어긋나는 문제는 눈으로만 잡힌다.
    anim = (rule or {}).get("preview", {}).get("animation", "walk")
    result = contactsheet.build_direction_sheet(
        profile_dir,
        os.path.join(paths.GEN_REPORTS, "%s_directions.png" % args.profile),
        animation=anim,
        title="%s - %s direction alignment" % (args.profile, anim))
    if result:
        dpath, directions, seed = result
        print("방향 검증 시트 (seed %s, %s) -> %s"
              % (seed, "/".join(directions), paths.rel(dpath)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
