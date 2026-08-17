#!/usr/bin/env python3
"""Sprite Library / Resolver 용 runtime export (기존 baked export 와 별개).

    python3 tools/export_unity_runtime.py 04_RULES/lpc_phase1_population.json --seeds 4001

기존 `tools/export_unity.py` (baked) 를 대체하지 않는다. 둘 다 같은
`character.json` 을 입력으로 쓰고, 출력만 다르다.
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import catalog as catalog_mod, generate as generate_mod  # noqa: E402
from ap2d import palette as palette_mod, paths, rules, runtime_export  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rule", help="04_RULES 아래 규칙 JSON")
    ap.add_argument("--seeds", nargs="*", type=int,
                    help="POC 대상 seed. 생략하면 전부")
    ap.add_argument("--cell-size", type=int, default=256,
                    help="파츠 시트 셀 최대 변 (baked 와 같은 값을 써야 비교가 성립한다)")
    ap.add_argument("--out", help="출력 루트")
    args = ap.parse_args(argv)

    rule_raw = generate_mod._peek_rule(args.rule)
    cat = catalog_mod.load_catalog(rule_raw["catalog"])
    pal = (palette_mod.load(rule_raw["palettes"]["source"])
           if rule_raw.get("palettes") else None)
    rule = rules.load(args.rule, catalog=cat, pal=pal)

    profile_dir = os.path.join(paths.GEN_CHARACTERS, rule["profile"])
    if not os.path.isdir(profile_dir):
        print("생성 결과가 없다: %s" % paths.rel(profile_dir), file=sys.stderr)
        return 1

    characters = []
    for name in sorted(os.listdir(profile_dir), key=lambda n: (len(n), n)):
        cpath = os.path.join(profile_dir, name, "character.json")
        if not os.path.isfile(cpath):
            continue
        with open(cpath, "r", encoding="utf-8") as fh:
            definition = json.load(fh)
        if args.seeds and definition["seed"] not in args.seeds:
            continue
        characters.append((os.path.join(profile_dir, name), definition))
    if not characters:
        print("대상 캐릭터가 없다", file=sys.stderr)
        return 1

    out_root = (paths.abspath(args.out) if args.out
                else os.path.join(paths.UNITY_EXPORT, "runtime", rule["profile"]))
    manifest_path, manifest = runtime_export.export(
        rule, cat, characters, out_root=out_root, cell_size=args.cell_size)

    counts = manifest["counts"]
    print("appearance %d / 고유 파츠 %d / 파츠 시트 %d / 고유 스프라이트 %d"
          % (counts["appearances"], counts["unique_parts"],
             counts["part_sheets"], counts["unique_sprites"]))
    print("  categories: %s" % ", ".join(manifest["categories"]))
    for animation, topo in manifest["topology"].items():
        print("  %-6s frames=%-2d directions=%s"
              % (animation, topo["frame_count"],
                 ", ".join(topo["directions"]) or "—"))
    print("  -> %s" % paths.rel(manifest_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
