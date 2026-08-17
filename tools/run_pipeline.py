#!/usr/bin/env python3
"""scan -> generate -> contact sheet -> validate -> unity export 를 한 번에.

    python3 tools/run_pipeline.py 04_RULES/cc0_test_population.json

05_GENERATED 를 지우고 처음부터 다시 만들려면:

    rm -rf 05_GENERATED/characters 05_GENERATED/reports 06_UNITY_EXPORT/characters
    python3 tools/run_pipeline.py 04_RULES/cc0_test_population.json
"""

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import export_unity  # noqa: E402
import generate_characters  # noqa: E402
import make_contact_sheet  # noqa: E402
import scan_pack  # noqa: E402
import validate_generated  # noqa: E402
from ap2d import catalog as catalog_mod, generate as generate_mod, paths  # noqa: E402


def step(index, total, title):
    print("\n[%d/%d] %s" % (index, total, title))
    print("-" * (len(title) + 8))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rule", help="04_RULES 아래 규칙 JSON")
    ap.add_argument("--rescan", action="store_true",
                    help="카탈로그가 이미 있어도 다시 스캔한다")
    ap.add_argument("--adapter", help="pack adapter (예: lpc). 생략하면 기존 카탈로그의 값을 쓴다")
    ap.add_argument("--clean", action="store_true",
                    help="이 profile 의 기존 생성물을 지우고 시작한다")
    args = ap.parse_args(argv)

    started = time.time()
    rule_raw = generate_mod._peek_rule(args.rule)
    profile = rule_raw["profile"]
    catalog_path = rule_raw["catalog"]
    pack_name = rule_raw["pack"]
    total = 5

    step(1, total, "Scan — 01_SOURCE -> 02_CATALOG")
    if args.rescan or not os.path.isfile(paths.abspath(catalog_path)):
        pack_root = _find_pack_root(pack_name)
        argv = [paths.rel(pack_root), "--name", pack_name]
        # adapter 로 만든 카탈로그는 재스캔할 때도 같은 adapter 를 써야 한다.
        # 어떤 adapter 였는지는 기존 카탈로그가 기억하고 있다.
        adapter = args.adapter or _adapter_of(catalog_path)
        if adapter:
            argv += ["--adapter", adapter]
        scan_pack.main(argv)
    else:
        cat = catalog_mod.load_catalog(catalog_path)
        print("기존 카탈로그 사용: %s (파일 %d, 파츠 %d)"
              % (catalog_path, cat["pack"]["file_count"],
                 sum(len(p) for p in cat["parts"].values())))

    if args.clean:
        for target in (os.path.join(paths.GEN_CHARACTERS, profile),
                       os.path.join(paths.UNITY_EXPORT, "characters", profile)):
            if os.path.isdir(target):
                shutil.rmtree(paths.assert_writable(target))
                print("지움: %s" % paths.rel(target))

    step(2, total, "Generate — 규칙 + 팔레트 + seed -> 05_GENERATED")
    generate_characters.main([args.rule])

    step(3, total, "Contact sheet — 05_GENERATED/reports")
    make_contact_sheet.main([profile, "--rule", args.rule])

    # export 를 validate 보다 먼저 돌린다. validate 가 05_GENERATED 뿐 아니라
    # 06_UNITY_EXPORT 의 manifest 까지 검사 대상으로 삼기 때문이다.
    step(4, total, "Unity export — 06_UNITY_EXPORT")
    export_unity.main([args.rule])

    step(5, total, "Validate — 05_GENERATED/reports/<profile>_validation.*")
    validate_rc = validate_generated.main([args.rule])

    print("\n%s (%.1fs)" % ("완료" if validate_rc == 0 else "완료 — 단 검증 실패가 있다",
                            time.time() - started))
    return validate_rc


def _adapter_of(catalog_path):
    """기존 카탈로그에 기록된 adapter 이름. 없으면 None."""
    path = paths.abspath(catalog_path)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)["pack"].get("adapter")
    except (ValueError, KeyError):
        return None


def _find_pack_root(pack_name):
    """01_SOURCE 아래에서 팩 폴더를 찾는다."""
    for domain in sorted(os.listdir(paths.SOURCE)):
        candidate = os.path.join(paths.SOURCE, domain, pack_name)
        if os.path.isdir(candidate):
            return candidate
    raise SystemExit("01_SOURCE 아래에서 팩 폴더를 찾지 못했다: %s" % pack_name)


if __name__ == "__main__":
    raise SystemExit(main())
