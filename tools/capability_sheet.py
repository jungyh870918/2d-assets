#!/usr/bin/env python3
"""`02_CATALOG/CAPABILITIES.md` — 지금 무엇을 시킬 수 있는지 한 장으로.

    python3 tools/capability_sheet.py

카탈로그·라이선스 기록·팔레트·규칙에 이미 있는 사실을 모으기만 한다.
새로 계산하거나 판정하지 않는다. 스캔 후에 다시 돌린다.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import capability, paths  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="Markdown 대신 JSON 을 표준출력으로")
    args = ap.parse_args(argv)

    data = capability.build()
    if args.json:
        import json
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    for pack in data["packs"]:
        slots = pack["slots"]
        print("  %-46s composable=%-8s 슬롯 %d  조합상한 %s" % (
            pack["pack"], pack["composable"], len(slots),
            "{:,}".format(pack["combinations"]) if pack["combinations"] else "—"))
        if slots:
            print("      " + " · ".join("%s %d" % (k, v) for k, v in slots.items()))
    md = capability.write(data)
    print("  -> %s" % paths.rel(md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
