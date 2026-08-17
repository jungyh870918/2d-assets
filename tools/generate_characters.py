#!/usr/bin/env python3
"""규칙 하나를 실행해 05_GENERATED/characters/<profile>/<seed>/ 를 만든다.

    python3 tools/generate_characters.py 04_RULES/cc0_test_population.json
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import generate, paths  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rule", help="04_RULES 아래 규칙 JSON")
    ap.add_argument("--out", help="출력 루트 (기본: 05_GENERATED/characters/<profile>)")
    ap.add_argument("--no-images", action="store_true",
                    help="정의만 만들고 PNG 는 그리지 않는다 (빠른 결정성 확인용)")
    ap.add_argument("--preview-size", type=int, default=384)
    ap.add_argument("--sheet-size", type=int, default=256)
    args = ap.parse_args(argv)

    print("규칙: %s" % args.rule)
    result = generate.generate(
        args.rule,
        out_root=paths.abspath(args.out) if args.out else None,
        render_images=not args.no_images,
        preview_size=args.preview_size,
        sheet_size=args.sheet_size,
    )
    print("생성 %d개 -> %s" % (len(result["records"]), result["out_root"]))
    rerolls = sum(1 for r in result["records"] if r["attempt"] > 0)
    print("중복 회피 재시도가 있었던 캐릭터: %d개" % rerolls)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
