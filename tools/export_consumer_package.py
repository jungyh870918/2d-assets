#!/usr/bin/env python3
"""외부 Unity 게임 프로젝트로 넘길 **자족적 패키지**를 만든다.

    python3 tools/export_consumer_package.py <소비자 Assets 경로> --profiles lpc_phase2_showcase

Factory 저장소를 옆에 두지 않아도 소비자가 열리고 실행되어야 한다.
그래서 symlink 를 만들지 않고 **실제로 복사**한다. 복사한 목록은 그대로 출력해
Export Contract 의 실측 근거로 남긴다.

이 스크립트는 "무엇이 필요한지" 를 미리 단정하지 않는다. 지금 넣는 것은
소비자를 실제로 붙여 보며 **필요하다고 관찰된 것**이고, 분류(runtime/editor/
provenance)를 함께 기록한다.
"""

import argparse
import hashlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import paths, runtime_export  # noqa: E402

UNITY_SRC = os.path.join(paths.REPO_ROOT, "tools", "unity")

# (파일, 소비자 하위 경로, 분류, 메모)
RUNTIME_SCRIPTS = [
    ("CharacterView.cs", "runtime required", "Animator 상태 -> 라벨 -> Resolver"),
    ("CharacterAppearance.cs", "runtime required", "외형 정의 (frame 미포함)"),
    ("CharacterAnimationState.cs", "runtime required", "state -> 애니메이션 이름"),
    ("CharacterProfile.cs", "runtime required", "소비자가 아는 유일한 진입점"),
]
EDITOR_SCRIPTS = [
    ("SpriteLibraryBuilder.cs", "editor/import required", "manifest -> 라이브러리/프리팹/프로파일"),
    ("AnimationClipBuilder.cs", "editor/import required", "manifest -> clip/controller"),
]


# ownership 경계 (Export Contract v1)
#   Factory-owned  : Runtime/ · Editor/ · Profiles/<p>/runtime_manifest.json · Profiles/<p>/parts/
#   Consumer-generated : Profiles/<p>/Generated/     <- 절대 지우지 않는다
#   Game-owned     : Assets/Game/...                 <- 건드리지 않는다
GENERATED_DIR = "Generated"


def _replace_tree(src, dest):
    """Factory-owned 하위 트리만 갈아끼운다. .meta 는 남긴다.

    Unity 의 .meta 에 GUID 가 들어 있어서, 통째로 지우면 이미 이 에셋을 참조하던
    게임 쪽 직렬화 참조가 전부 끊긴다. 그래서 **파일만 덮어쓰고**, 더 이상 소스에
    없는 파일만 지운다 (그 파일의 .meta 도 함께).
    """
    os.makedirs(dest, exist_ok=True)
    wanted = set()
    for root, _dirs, files in os.walk(src):
        rel = os.path.relpath(root, src)
        target_dir = dest if rel == "." else os.path.join(dest, rel)
        os.makedirs(target_dir, exist_ok=True)
        for name in files:
            wanted.add(os.path.normpath(os.path.join(target_dir, name)))
            shutil.copy2(os.path.join(root, name), os.path.join(target_dir, name))

    removed = []
    for root, dirs, files in os.walk(dest, topdown=False):
        dirs[:] = [d for d in dirs if d != GENERATED_DIR]
        if GENERATED_DIR in os.path.relpath(root, dest).split(os.sep):
            continue
        for name in files:
            path = os.path.normpath(os.path.join(root, name))
            if name.endswith(".meta"):
                continue          # .meta 는 짝이 사라질 때만 정리한다
            if path not in wanted:
                os.unlink(path)
                meta = path + ".meta"
                if os.path.isfile(meta):
                    os.unlink(meta)
                removed.append(path)
    return removed


def export(dest_assets, profiles, package="ArtFactory"):
    manifest_records = []
    attributions = {}
    pkg_root = os.path.join(dest_assets, package)
    scripts_dir = os.path.join(pkg_root, "Runtime")
    editor_dir = os.path.join(pkg_root, "Editor")
    # **rmtree 하지 않는다.** Generated/ 와 .meta 가 사라지면 게임 참조가 끊긴다.
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(editor_dir, exist_ok=True)

    for name, kind, note in RUNTIME_SCRIPTS:
        shutil.copy2(os.path.join(UNITY_SRC, name), os.path.join(scripts_dir, name))
        manifest_records.append((name, "tools/unity/%s" % name,
                                 "%s/Runtime/%s" % (package, name), kind, note))
    shutil.copy2(os.path.join(UNITY_SRC, "ArtFactory.Runtime.asmdef"), scripts_dir)
    manifest_records.append(("ArtFactory.Runtime.asmdef",
                             "tools/unity/ArtFactory.Runtime.asmdef",
                             "%s/Runtime/" % package, "editor/import required",
                             "어셈블리 경계. 게임 코드가 참조한다"))

    for name, kind, note in EDITOR_SCRIPTS:
        shutil.copy2(os.path.join(UNITY_SRC, name), os.path.join(editor_dir, name))
        manifest_records.append((name, "tools/unity/%s" % name,
                                 "%s/Editor/%s" % (package, name), kind, note))
    shutil.copy2(os.path.join(UNITY_SRC, "ArtFactory.Editor.asmdef"), editor_dir)
    manifest_records.append(("ArtFactory.Editor.asmdef",
                             "tools/unity/ArtFactory.Editor.asmdef",
                             "%s/Editor/" % package, "editor/import required",
                             "어셈블리 경계"))

    for profile in profiles:
        src = os.path.join(paths.UNITY_EXPORT, "runtime", profile)
        if not os.path.isdir(src):
            raise SystemExit("runtime export 가 없다: %s — export_unity_runtime.py 를 먼저 돌려라"
                             % paths.rel(src))
        dest = os.path.join(pkg_root, "Profiles", profile)
        # Generated/ 를 보존하면서 Factory-owned 입력만 갱신한다.
        _replace_tree(src, dest)

        sheets = sum(len(files) for _r, _d, files in os.walk(os.path.join(dest, "parts")))
        manifest_records.append(("runtime_manifest.json",
                                 "06_UNITY_EXPORT/runtime/%s/" % profile,
                                 "%s/Profiles/%s/" % (package, profile),
                                 "editor/import required",
                                 "slot/label/topology/origin 선언. 빌더 입력"))
        manifest_records.append(("parts/**.png (%d장)" % sheets,
                                 "06_UNITY_EXPORT/runtime/%s/parts/" % profile,
                                 "%s/Profiles/%s/parts/" % (package, profile),
                                 "runtime required",
                                 "슬라이스된 스프라이트의 실제 텍스처"))

        # 표기 의무는 소비자 저장소에서 지켜져야 한다. Factory 저장소의 리포트를
        # 가리키기만 하면 소비자는 그걸 못 읽는다 — 그래서 패키지 안으로 복사된다.
        report = os.path.join(dest, runtime_export.ATTRIBUTION_REPORT)
        if os.path.isfile(report):
            manifest_records.append((runtime_export.ATTRIBUTION_REPORT,
                                     "06_UNITY_EXPORT/runtime/%s/" % profile,
                                     "%s/Profiles/%s/" % (package, profile),
                                     "license obligation",
                                     "저자 표기 원문. 배포 전 credits 에 반영해야 한다"))
        manifest_path = os.path.join(dest, "runtime_manifest.json")
        if os.path.isfile(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as fh:
                attributions[profile] = json.load(fh).get("attribution") or {}

    fingerprint = _write_export_manifest(pkg_root, profiles)
    _write_readme(pkg_root, profiles, manifest_records, attributions)
    return pkg_root, manifest_records, fingerprint


CONTRACT_VERSION = "1.0"


def _write_export_manifest(pkg_root, profiles):
    """패키지 식별용 최소 metadata.

    fingerprint 는 **내보낸 결정적 입력의 해시**다. 시각/UUID 를 쓰지 않는다 —
    같은 입력이면 같은 지문이 나와야 "이 패키지가 그 패키지인가" 를 판정할 수 있다.
    """
    entries = []
    # `sorted(os.walk(...))` 로 감싸면 안 된다 — walk 가 통째로 소비된 뒤에 정렬되므로
    # `dirs[:]` 가지치기가 무효가 되고 소비자 소유인 Generated/ 가 지문에 섞인다.
    # (실제로 그렇게 새서, 소비자가 빌드한 뒤 같은 입력의 지문이 달라졌다.)
    for root, dirs, files in os.walk(pkg_root):
        dirs[:] = [d for d in dirs if d != GENERATED_DIR]
        for name in sorted(files):
            if name.endswith(".meta") or name in ("export_manifest.json", "README.md"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, pkg_root).replace(os.sep, "/")
            h = hashlib.sha256()
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            entries.append((rel, h.hexdigest()))

    entries.sort()
    digest = hashlib.sha256()
    for rel, file_hash in entries:
        digest.update(rel.encode("utf-8"))
        digest.update(file_hash.encode("utf-8"))
    fingerprint = digest.hexdigest()

    payload = {
        "contract_version": CONTRACT_VERSION,
        "profiles": sorted(profiles),
        "content_fingerprint": fingerprint,
        "file_count": len(entries),
        "$comment": "content_fingerprint 는 Factory-owned 입력만의 해시다. "
                    "Generated/ 와 .meta 는 제외한다 (소비자 소유). "
                    "시간·UUID 를 쓰지 않으므로 같은 입력이면 같은 값이다.",
    }
    with open(os.path.join(pkg_root, "export_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return fingerprint


def _write_readme(pkg_root, profiles, records, attributions=None):
    attributions = attributions or {}
    lines = ["# ArtFactory — consumer package", ""]
    lines.append("`tools/export_consumer_package.py` 가 복사한 자족 패키지다.")
    lines.append("Factory 저장소가 없어도 이 폴더만으로 동작해야 한다. 손으로 고치지 않는다.")
    lines.append("")
    required = sorted(p for p, a in attributions.items()
                      if a.get("attribution_required"))
    if required:
        lines.append("## ⚠️ 저자 표기 의무")
        lines.append("")
        lines.append("이 패키지의 아트는 **표기 없이 배포하면 라이선스 위반**이다. "
                     "`commercial_use: yes` 와는 별개의 축이다.")
        lines.append("")
        for profile in required:
            attrib = attributions[profile]
            lines.append("**`%s`** — 저자 %d명 · %s · 원문 `Profiles/%s/%s`"
                         % (profile, len(attrib.get("authors") or []),
                            ", ".join("`%s`" % l for l in attrib.get("licenses") or []),
                            profile, attrib.get("report") or "—"))
            lines.append("")
            lines.append("```")
            for text in attrib.get("credits") or []:
                lines.append(text)
            lines.append("```")
            lines.append("")
    lines.append("## 쓰는 법")
    lines.append("")
    lines.append("1. 메뉴 **2D Art Factory > Build Sprite Libraries** 에서 "
                 "`Profiles/<profile>/runtime_manifest.json` 을 고른다 (에디터 1회).")
    lines.append("2. 생성된 `Profiles/<profile>/Generated/<profile>_profile.asset` 을 "
                 "게임 코드에 물린다. 게임이 아는 에셋은 이것 하나다.")
    lines.append("")
    lines.append("## 포함된 것")
    lines.append("")
    lines.append("| artifact | Factory 원본 | 분류 | 메모 |")
    lines.append("|---|---|---|---|")
    for name, src, _dest, kind, note in records:
        lines.append("| `%s` | `%s` | %s | %s |" % (name, src, kind, note))
    lines.append("")
    lines.append("## profile")
    lines.append("")
    for profile in profiles:
        lines.append("- `%s`" % profile)
    lines.append("")
    with open(os.path.join(pkg_root, "README.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dest", help="소비자 Unity 프로젝트의 Assets 경로")
    ap.add_argument("--profiles", nargs="+", required=True)
    ap.add_argument("--package", default="ArtFactory")
    args = ap.parse_args(argv)

    dest = os.path.abspath(args.dest)
    if not os.path.isdir(dest):
        raise SystemExit("소비자 Assets 폴더가 없다: %s" % dest)

    pkg_root, records, fingerprint = export(dest, args.profiles, args.package)
    print("패키지 -> %s" % pkg_root)
    print("%-34s %-22s %s" % ("artifact", "분류", "메모"))
    for name, _src, _d, kind, note in records:
        print("  %-32s %-22s %s" % (name[:32], kind, note))
    total = sum(len(files) for _r, _d, files in os.walk(pkg_root))
    print("총 %d 파일" % total)
    print("contract %s · fingerprint %s" % (CONTRACT_VERSION, fingerprint[:16]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
