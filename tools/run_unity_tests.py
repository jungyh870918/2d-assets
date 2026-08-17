#!/usr/bin/env python3
"""Unity 테스트 하네스. scratch 에 프로젝트를 조립하고 CLI 로 돌린다.

    python3 tools/run_unity_tests.py                 # EditMode + PlayMode 둘 다
    python3 tools/run_unity_tests.py --only playmode

Unity 프로젝트는 저장소에 커밋하지 않는다 (Library/ 등 대용량). 소스는
`tools/unity/` 에만 두고 export 결과와 조합해 매번 재구성한다.

EditMode 는 자체 어서션 하네스(SpriteRuntimeTests)를 `-executeMethod` 로 돌리고,
PlayMode 는 Unity Test Framework 를 `-runTests` 로 돌린다. PlayMode 는 실제
플레이 루프가 필요해서 EditMode 와 같은 방식으로는 돌릴 수 없다 — 그래서
실행 경로가 둘로 나뉜다.
"""

import argparse
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ap2d import paths  # noqa: E402

UNITY = "/Applications/Unity/Hub/Editor/6000.0.81f1/Unity.app/Contents/MacOS/Unity"
UNITY_SRC = os.path.join(paths.REPO_ROOT, "tools", "unity")

RUNTIME_SCRIPTS = ["CharacterAppearance.cs", "CharacterView.cs",
                   "CharacterAnimationState.cs", "CharacterProfile.cs",
                   "GeneratedCharacter.cs"]
EDITOR_SCRIPTS = ["SpriteLibraryBuilder.cs", "AnimationClipBuilder.cs",
                  "SpriteRuntimeTests.cs", "GeneratedCharacterImporter.cs"]

MANIFEST = """{
  "dependencies": {
    "com.unity.2d.animation": "10.1.4",
    "com.unity.2d.sprite": "1.0.0",
    "com.unity.test-framework": "1.4.5",
    "com.unity.modules.animation": "1.0.0",
    "com.unity.modules.imageconversion": "1.0.0",
    "com.unity.modules.jsonserialize": "1.0.0"
  }
}
"""

PROJECT_VERSION = "m_EditorVersion: 6000.0.81f1\n"


def build_project(project_dir, profiles):
    """runtime export 결과 + C# 소스로 Unity 프로젝트를 조립한다."""
    if os.path.isdir(project_dir):
        shutil.rmtree(project_dir)
    for sub in ("Assets/Scripts", "Assets/Editor", "Assets/Tests/PlayMode",
                "Packages", "ProjectSettings"):
        os.makedirs(os.path.join(project_dir, sub))

    with open(os.path.join(project_dir, "Packages", "manifest.json"), "w") as fh:
        fh.write(MANIFEST)
    with open(os.path.join(project_dir, "ProjectSettings",
                           "ProjectVersion.txt"), "w") as fh:
        fh.write(PROJECT_VERSION)

    for name in RUNTIME_SCRIPTS:
        shutil.copy2(os.path.join(UNITY_SRC, name),
                     os.path.join(project_dir, "Assets/Scripts", name))
    shutil.copy2(os.path.join(UNITY_SRC, "ArtFactory.Runtime.asmdef"),
                 os.path.join(project_dir, "Assets/Scripts"))
    for name in EDITOR_SCRIPTS:
        shutil.copy2(os.path.join(UNITY_SRC, name),
                     os.path.join(project_dir, "Assets/Editor", name))
    shutil.copy2(os.path.join(UNITY_SRC, "ArtFactory.Editor.asmdef"),
                 os.path.join(project_dir, "Assets/Editor"))
    for name in os.listdir(os.path.join(UNITY_SRC, "PlayMode")):
        shutil.copy2(os.path.join(UNITY_SRC, "PlayMode", name),
                     os.path.join(project_dir, "Assets/Tests/PlayMode", name))

    copied = 0
    for profile in profiles:
        src = os.path.join(paths.UNITY_EXPORT, "runtime", profile)
        if not os.path.isdir(src):
            print("  runtime export 없음, 건너뜀: %s" % profile)
            continue
        dest = os.path.join(project_dir, "Assets/Runtime", profile)
        shutil.copytree(src, dest)
        copied += 1
    return copied


def run_unity(args, log_path, timeout=1800):
    cmd = [UNITY, "-batchmode", "-nographics", "-projectPath", args["project"],
           "-logFile", log_path] + args["extra"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode


def summarize_nunit(xml_path):
    if not os.path.isfile(xml_path):
        return None
    root = ET.parse(xml_path).getroot()
    return {
        "total": int(root.get("total", 0)),
        "passed": int(root.get("passed", 0)),
        "failed": int(root.get("failed", 0)),
        "skipped": int(root.get("skipped", 0)),
        "result": root.get("result", "?"),
        "duration": root.get("duration", "?"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=["editmode", "playmode"],
                    help="한 쪽만 실행")
    ap.add_argument("--project", help="Unity 프로젝트 경로 (기본: scratch)")
    ap.add_argument("--profiles", nargs="*",
                    default=["cc0_test_population", "lpc_phase1_population",
                             "lpc_phase2_showcase"])
    args = ap.parse_args(argv)

    if not os.path.isfile(UNITY):
        print("Unity 에디터를 찾지 못했다: %s" % UNITY, file=sys.stderr)
        return 2

    project = args.project or os.path.join(
        os.environ.get("TMPDIR", "/tmp"), "ap2d_unity_tests")
    print("프로젝트 조립: %s" % project)
    copied = build_project(project, args.profiles)
    print("  runtime profile %d개 복사" % copied)

    log_dir = os.path.dirname(project)
    failures = 0

    if args.only != "playmode":
        print("\n[EditMode] SpriteRuntimeTests.RunAll")
        log = os.path.join(log_dir, "unity_editmode.log")
        code = run_unity({"project": project,
                          "extra": ["-quit", "-executeMethod",
                                    "ArtFactory.EditorTools.SpriteRuntimeTests.RunAll"]},
                         log)
        result = _grep(log, "[RESULT]")
        print("  exit=%d  %s" % (code, result or "(결과 줄 없음)"))
        if code != 0:
            failures += 1
            for line in _grep_all(log, "[FAIL]")[:10]:
                print("   ", line)

    if args.only != "editmode":
        print("\n[PlayMode] Unity Test Framework")
        log = os.path.join(log_dir, "unity_playmode.log")
        results_xml = os.path.join(log_dir, "playmode_results.xml")
        if os.path.isfile(results_xml):
            os.unlink(results_xml)
        code = run_unity({"project": project,
                          "extra": ["-runTests", "-testPlatform", "PlayMode",
                                    "-testResults", results_xml]},
                         log)
        summary = summarize_nunit(results_xml)
        if summary:
            print("  exit=%d  total=%d passed=%d failed=%d skipped=%d result=%s"
                  % (code, summary["total"], summary["passed"], summary["failed"],
                     summary["skipped"], summary["result"]))
            if summary["failed"]:
                failures += 1
                for line in _failed_tests(results_xml):
                    print("   FAIL:", line)
        else:
            print("  exit=%d  결과 XML 이 없다 — 로그: %s" % (code, log))
            failures += 1
        for line in _grep_all(log, "[PLAYMODE"):
            print("   ", line)

    print("\n%s" % ("모두 통과" if failures == 0 else "실패 %d" % failures))
    return 0 if failures == 0 else 1


def _grep(path, needle):
    for line in _grep_all(path, needle):
        return line
    return None


def _grep_all(path, needle):
    if not os.path.isfile(path):
        return []
    out = []
    with open(path, "r", errors="replace") as fh:
        for line in fh:
            if needle in line:
                out.append(line.strip())
    return out


def _failed_tests(xml_path):
    root = ET.parse(xml_path).getroot()
    out = []
    for case in root.iter("test-case"):
        if case.get("result") == "Failed":
            message = case.find("failure/message")
            out.append("%s — %s" % (case.get("fullname"),
                                    (message.text or "").strip().splitlines()[0]
                                    if message is not None and message.text else ""))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
