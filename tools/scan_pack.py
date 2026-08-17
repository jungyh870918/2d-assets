#!/usr/bin/env python3
"""01_SOURCE 의 팩 하나를 스캔해 02_CATALOG/<pack>.json + .summary.md 를 만든다.

    python3 tools/scan_pack.py 01_SOURCE/characters/rgsdev_free-cc0-modular-vector-characters_v1
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import catalog, paths, summary  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("pack_root", help="01_SOURCE 아래 팩 폴더 (저장소 기준 상대경로 가능)")
    ap.add_argument("--name", help="팩 이름 (기본: 폴더명)")
    ap.add_argument("--adapter",
                    help="팩이 권위 metadata 를 제공하는 경우 사용할 adapter "
                         "(예: lpc). 기본은 경로/파일명 추론.")
    args = ap.parse_args(argv)

    pack_root = paths.abspath(args.pack_root)
    if not paths.is_inside_source(pack_root):
        print("경고: %s 는 01_SOURCE 밖이다." % paths.rel(pack_root), file=sys.stderr)

    name = args.name or os.path.basename(pack_root.rstrip(os.sep))
    print("스캔: %s%s" % (paths.rel(pack_root),
                          " (adapter=%s)" % args.adapter if args.adapter else ""))
    cat = catalog.scan_pack(pack_root, name, adapter=args.adapter)

    json_path = os.path.join(paths.CATALOG, name + ".json")
    md_path = os.path.join(paths.CATALOG, name + ".summary.md")
    catalog.write_catalog(cat, json_path)
    summary.write(cat, md_path)

    pk = cat["pack"]
    print("  파일 %d / 이미지 %d / modular part 프레임 %d"
          % (pk["file_count"], pk["image_count"], pk["modular_part_count"]))
    print("  카테고리 %d종, 파츠 %d개"
          % (len(cat["parts"]), sum(len(p) for p in cat["parts"].values())))
    print("  -> %s" % paths.rel(json_path))
    print("  -> %s" % paths.rel(md_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
