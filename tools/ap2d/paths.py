"""저장소 경로 해석. 폴더 구조는 README.md 에 정의된 것을 그대로 쓴다."""

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DOCS = os.path.join(REPO_ROOT, "00_DOCS")
LICENSES = os.path.join(DOCS, "licenses")
SOURCE = os.path.join(REPO_ROOT, "01_SOURCE")
CATALOG = os.path.join(REPO_ROOT, "02_CATALOG")
PALETTES = os.path.join(REPO_ROOT, "03_PALETTES")
RULES = os.path.join(REPO_ROOT, "04_RULES")
GENERATED = os.path.join(REPO_ROOT, "05_GENERATED")
GEN_CHARACTERS = os.path.join(GENERATED, "characters")
GEN_REPORTS = os.path.join(GENERATED, "reports")
UNITY_EXPORT = os.path.join(REPO_ROOT, "06_UNITY_EXPORT")


def rel(path):
    """절대경로를 저장소 루트 기준 상대경로(슬래시 구분)로."""
    return os.path.relpath(os.path.abspath(path), REPO_ROOT).replace(os.sep, "/")


def abspath(relpath):
    """저장소 루트 기준 상대경로를 절대경로로."""
    if os.path.isabs(relpath):
        return relpath
    return os.path.join(REPO_ROOT, relpath.replace("/", os.sep))


def is_inside_source(path):
    """경로가 01_SOURCE 안에 있는지. 쓰기 가드용."""
    p = os.path.abspath(path)
    return p == SOURCE or p.startswith(SOURCE + os.sep)


def assert_writable(path):
    """01_SOURCE 아래에 쓰려는 시도를 즉시 차단한다."""
    if is_inside_source(path):
        raise PermissionError(
            "01_SOURCE 는 읽기 전용이다. 쓰기 시도가 차단됨: %s" % rel(path)
        )
    return path


def ensure_dir(path):
    assert_writable(path)
    os.makedirs(path, exist_ok=True)
    return path
