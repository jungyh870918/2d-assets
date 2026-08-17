"""소스 트리 지문 — **한 가지 방법만 둔다.**

이전에는 `01_SOURCE` 의 해시를 그때그때 셸 파이프로 냈다. 명령이 조금만 달라도
(정렬 유무, `.DS_Store` 포함 여부, 절대경로 포함 여부) 값이 달라져서, 같은 트리인데
회차마다 다른 값이 나왔다. 불변식을 측정하는 방법이 불안정하면 불변식도 못 지킨다.

그래서 규칙을 고정한다:

  - 상대 경로 + 파일 바이트만 쓴다. 절대 경로는 들어가지 않는다.
  - 경로는 POSIX 구분자로 정규화하고 **명시적으로 정렬**한다.
    os.walk 순서(=파일시스템 순서)에 의존하지 않는다.
  - mtime · 크기 · 권한 · inode 를 쓰지 않는다.
  - EXCLUDED_NAMES 는 여기 한 곳에만 있다.
  - 빈 디렉터리는 무시한다 (git 도 추적하지 않는다).

무결성 서브시스템을 만들지 않는다. 함수 두 개가 전부다.
"""

import hashlib
import os

# OS/편집기가 만드는 부산물. 내용이 사람 없이도 바뀌므로 지문에서 뺀다.
EXCLUDED_NAMES = frozenset([
    ".DS_Store",        # macOS Finder — 폴더를 열어보기만 해도 바뀐다
    "Thumbs.db",        # Windows 탐색기
    "desktop.ini",      # Windows
])

# macOS 가 비-HFS 볼륨에 만드는 AppleDouble 잔재
EXCLUDED_PREFIXES = ("._",)

ALGORITHM = "sha256(relpath + NUL + sha256(bytes) + LF, sorted by relpath, POSIX sep)"


def is_excluded(name):
    return name in EXCLUDED_NAMES or name.startswith(EXCLUDED_PREFIXES)


def file_hashes(root):
    """root 아래 (상대경로 -> sha256). 경로는 항상 POSIX 구분자다."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in filenames:
            if is_excluded(name):
                continue
            full = os.path.join(dirpath, name)
            h = hashlib.sha256()
            with open(full, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            out[rel] = h.hexdigest()
    return out


def tree_fingerprint(root):
    """트리 하나를 sha256 한 개로. 같은 내용이면 어디서 돌려도 같은 값이다."""
    digest = hashlib.sha256()
    hashes = file_hashes(root)
    for rel in sorted(hashes):
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashes[rel].encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()
