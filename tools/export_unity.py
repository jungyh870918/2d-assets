#!/usr/bin/env python3
"""05_GENERATED 결과를 06_UNITY_EXPORT/characters/<profile>/ 로 내보낸다.

    python3 tools/export_unity.py 04_RULES/cc0_test_population.json
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import catalog as catalog_mod, generate as generate_mod  # noqa: E402
from ap2d import palette as palette_mod, paths, rules, unity_export  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rule", help="04_RULES 아래 규칙 JSON")
    ap.add_argument("--out", help="출력 루트 (기본: 06_UNITY_EXPORT/characters/<profile>)")
    args = ap.parse_args(argv)

    rule_raw = generate_mod._peek_rule(args.rule)
    cat = catalog_mod.load_catalog(rule_raw["catalog"])
    pal = palette_mod.load(rule_raw["palettes"]["source"]) if rule_raw.get("palettes") else None
    rule = rules.load(args.rule, catalog=cat, pal=pal)

    profile_dir = os.path.join(paths.GEN_CHARACTERS, rule["profile"])
    if not os.path.isdir(profile_dir):
        print("생성 결과가 없다: %s" % paths.rel(profile_dir), file=sys.stderr)
        return 1

    characters = []
    for name in sorted(os.listdir(profile_dir), key=lambda n: (len(n), n)):
        cpath = os.path.join(profile_dir, name, "character.json")
        if os.path.isfile(cpath):
            with open(cpath, "r", encoding="utf-8") as fh:
                characters.append((os.path.join(profile_dir, name), json.load(fh)))

    caps = dict(cat["pack"].get("capabilities", {}))
    caps["direction_axis"] = cat["pack"].get("direction_axis",
                                             {"present": "unknown"})
    # 파일 단위 attribution 요약을 manifest 에 실어 Unity 쪽에서도 표기 의무를 잃지 않게 한다.
    from ap2d import attribution as attribution_mod
    summaries = []
    for cdir, _defn in characters:
        gpath = os.path.join(cdir, "generation.json")
        if os.path.isfile(gpath):
            with open(gpath, "r", encoding="utf-8") as fh:
                summaries.append(json.load(fh).get("attribution") or {})
    merged = attribution_mod.merge(summaries)
    ref = {
        "source_assets": merged["source_assets"],
        "authors": merged["authors"],
        "licenses": merged["licenses"],
        "attribution_required": merged["attribution_required"],
        "share_alike_present": merged["share_alike_present"],
        "report": "05_GENERATED/reports/%s_attribution.md" % rule["profile"],
    }
    manifest_path, copied, manifest = unity_export.export(
        rule, characters, out_root=paths.abspath(args.out) if args.out else None,
        capabilities=caps, attribution_ref=ref)
    print("캐릭터 %d개 / 파일 %d개 복사" % (manifest["character_count"], copied))
    print("  -> %s" % paths.rel(manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
