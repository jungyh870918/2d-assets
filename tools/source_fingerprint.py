#!/usr/bin/env python3
"""`01_SOURCE` (또는 임의 폴더) 의 canonical 지문을 찍는다.

    python3 tools/source_fingerprint.py
    python3 tools/source_fingerprint.py 01_SOURCE/characters/<pack>

산출법은 `ap2d.integrity` 한 곳에만 있다. 셸 파이프로 즉석 해시를 내지 않는다 —
명령이 조금만 달라도 값이 달라져서 불변식을 측정할 수 없게 된다.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import integrity, paths  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=paths.SOURCE)
    ap.add_argument("--files", action="store_true", help="파일별 해시도 출력")
    args = ap.parse_args(argv)

    root = os.path.abspath(args.root)
    if not os.path.isdir(root):
        raise SystemExit("폴더가 없다: %s" % root)

    hashes = integrity.file_hashes(root)
    if args.files:
        for rel in sorted(hashes):
            print("%s  %s" % (hashes[rel], rel))
    print("root        %s" % paths.rel(root))
    print("algorithm   %s" % integrity.ALGORITHM)
    print("excluded    %s" % ", ".join(sorted(integrity.EXCLUDED_NAMES)
                                       + [p + "*" for p in integrity.EXCLUDED_PREFIXES]))
    print("files       %d" % len(hashes))
    print("fingerprint %s" % integrity.tree_fingerprint(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
