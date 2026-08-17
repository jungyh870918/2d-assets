#!/usr/bin/env python3
"""발주 회신 한 장 — `05_GENERATED/reports/<profile>_brief.md`

    python3 tools/order_brief.py 04_RULES/lpc_phase1_population.json

이미 있는 리포트 넷을 대체하지 않는다. 그 위에 한 번에 읽는 요약만 얹는다.
`run_pipeline.py` 가 검증 뒤에 자동으로 부른다.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import order, paths  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rule", help="04_RULES 아래 규칙 JSON")
    args = ap.parse_args(argv)

    brief = order.build(args.rule)
    md_path, json_path = order.write(brief)

    rel = brief["release"]
    print("  성격        %s" % order.PURPOSE_LABEL[brief["order"]["purpose"]])
    print("  소비자      %s" % brief["order"]["consumer"])
    print("  검증        %s (%d/%d 통과)" % (
        (brief["verification"]["status"] or "?").upper(),
        brief["verification"]["passed"], brief["verification"]["checks"]))
    print("  출시 자격   %s%s" % (
        str(rel["commercial_release_eligible"]).lower(),
        " · 출처 표기 필요" if rel["attribution_required"] else ""))
    print("  못 한 것    %s" % (len(brief["not_done"]) or "없음"))
    print("  -> %s" % paths.rel(md_path))
    print("  -> %s" % paths.rel(json_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
