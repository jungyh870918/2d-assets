#!/usr/bin/env python3
"""생성 결과를 검증하고 05_GENERATED/reports/<profile>_validation.{json,md} 를 쓴다.

    python3 tools/validate_generated.py 04_RULES/cc0_test_population.json
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import paths, validate  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rule", help="04_RULES 아래 규칙 JSON")
    args = ap.parse_args(argv)

    report, _ = validate.run(args.rule)
    json_path, md_path = validate.write(report)

    for check in report["checks"]:
        print("  %-6s %-34s (%d 항목, 실패 %d, 경고 %d)" % (
            check["status"].upper(), check["title"], check["items_checked"],
            len(check["failures"]), len(check["warnings"])))
    print("전체: %s" % report["status"].upper())
    print("  -> %s" % paths.rel(json_path))
    print("  -> %s" % paths.rel(md_path))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
