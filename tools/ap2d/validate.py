"""생성 결과 검증.

검사 항목:
  source_integrity   01_SOURCE 가 스캔 시점과 바이트 단위로 동일한가 (가장 중요)
  catalog_reference  character.json 이 카탈로그에 없는 파츠를 가리키지 않는가
  asset_presence     sources.json 의 소스 파일이 전부 실재하는가
  output_presence    preview / sheet 파일이 실재하는가
  dimensions         선언한 크기와 실제 이미지 크기가 맞는가
  alpha              합성 결과에 알파가 살아있고 내용이 비어있지 않은가
  uniqueness         같은 조합이 두 번 나오지 않았는가
  determinism        같은 seed 로 다시 생성하면 바이트가 같은가

결과는 05_GENERATED/reports/<profile>_validation.json 과 .md 로 남긴다.
프로파일마다 파일이 갈린다 — 팩이 여러 개면 한 파일에 덮어쓰면 안 되기 때문이다.
"""

import hashlib
import json
import os
import shutil
import tempfile

from PIL import Image

from . import (attribution, catalog as catalog_mod, generate as generate_mod,
               licensing, paths, rules)


class Check(object):
    def __init__(self, key, title):
        self.key = key
        self.title = title
        self.failures = []
        self.warnings = []
        self.checked = 0

    def fail(self, subject, message):
        self.failures.append({"subject": subject, "message": message})

    def warn(self, subject, message):
        self.warnings.append({"subject": subject, "message": message})

    @property
    def passed(self):
        return not self.failures

    def to_dict(self):
        return {
            "check": self.key,
            "title": self.title,
            "status": "pass" if self.passed else "fail",
            "items_checked": self.checked,
            "failures": self.failures,
            "warnings": self.warnings,
        }


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _character_dirs(profile_dir):
    out = []
    for name in sorted(os.listdir(profile_dir), key=lambda n: (len(n), n)):
        cdir = os.path.join(profile_dir, name)
        if os.path.isfile(os.path.join(cdir, "character.json")):
            out.append(cdir)
    return out


# ── 개별 검사 ──────────────────────────────────────────────────────────────

def check_source_integrity(cat):
    """01_SOURCE 가 스캔 이후 바뀌지 않았는지. CLAUDE.md 의 read-only 규칙 강제."""
    c = Check("source_integrity", "01_SOURCE 원본 불변 (hash 대조)")
    pack_root = paths.abspath(cat["pack"]["root"])
    recorded = {e["path"]: e["sha256"] for e in cat["entries"]}

    on_disk = set()
    for dirpath, dirnames, filenames in os.walk(pack_root):
        dirnames.sort()
        for name in sorted(filenames):
            if name in (".DS_Store", "Thumbs.db") or name.startswith("._"):
                continue
            on_disk.add(paths.rel(os.path.join(dirpath, name)))

    for rel_path, expected in sorted(recorded.items()):
        c.checked += 1
        abs_path = paths.abspath(rel_path)
        if not os.path.isfile(abs_path):
            c.fail(rel_path, "카탈로그에 있는 소스 파일이 사라졌다")
            continue
        actual = _sha256(abs_path)
        if actual != expected:
            c.fail(rel_path, "소스 파일이 변조됐다 (기대 %s… / 실제 %s…)"
                   % (expected[:12], actual[:12]))

    for rel_path in sorted(on_disk - set(recorded)):
        c.warn(rel_path, "카탈로그에 없는 파일이 소스 폴더에 있다 — 재스캔 필요")
    return c


def check_catalog_reference(cat, characters, rule):
    """character.json 이 카탈로그에 실재하는 파츠만 가리키는가."""
    c = Check("catalog_reference", "카탈로그에 없는 asset 참조 금지")
    policy = rule.get("animation_policy", "require_all")
    for cdir, definition in characters:
        for slot, part_name in definition["parts"].items():
            c.checked += 1
            if part_name is None:
                continue
            if slot not in rule["slots"]:
                c.fail(paths.rel(cdir), "규칙에 없는 slot %r" % slot)
                continue
            category = rule["slots"][slot]["from"]
            parts = cat["parts"].get(category, {})
            if part_name not in parts:
                c.fail(paths.rel(cdir),
                       "slot %s 가 카탈로그에 없는 part %s/%s 를 참조"
                       % (slot, category, part_name))
                continue
            for anim in definition["animations"]:
                if anim in parts[part_name]["animations"]:
                    continue
                if policy == "allow_subset":
                    # 규칙이 서브셋을 허용했다. 미지원 애니메이션에서는 그 레이어만
                    # 빠지고(hide_layer) 나머지는 정상이므로 실패가 아니다.
                    c.warn(paths.rel(cdir),
                           "part %s/%s 가 animation %r 을 지원하지 않는다 — "
                           "해당 레이어는 숨겨진다 (animation_policy: allow_subset)"
                           % (category, part_name, anim))
                    continue
                c.fail(paths.rel(cdir),
                       "part %s/%s 에 animation %r 이 없다 (animation compatibility)"
                       % (category, part_name, anim))
    return c


def check_asset_presence(characters):
    """sources.json 이 가리키는 소스 파일이 전부 존재하는가 (broken path)."""
    c = Check("asset_presence", "소스 asset 존재 / 경로 유효")
    for cdir, _definition in characters:
        spath = os.path.join(cdir, "sources.json")
        if not os.path.isfile(spath):
            c.fail(paths.rel(cdir), "sources.json 이 없다")
            continue
        data = _load_json(spath)
        if data["count"] != len(data["assets"]):
            c.fail(paths.rel(cdir), "sources.json 의 count(%d) 와 실제 목록(%d) 이 다르다"
                   % (data["count"], len(data["assets"])))
        for rel_path in data["assets"]:
            c.checked += 1
            if not os.path.isfile(paths.abspath(rel_path)):
                c.fail(paths.rel(cdir), "소스 파일 없음: %s" % rel_path)
            elif not paths.is_inside_source(paths.abspath(rel_path)):
                c.fail(paths.rel(cdir), "소스가 01_SOURCE 밖을 가리킨다: %s" % rel_path)
    return c


def check_outputs(characters):
    """출력 파일 존재 + 치수 + 알파."""
    presence = Check("output_presence", "생성물 파일 존재")
    dims = Check("dimensions", "이미지 치수 일치")
    alpha = Check("alpha", "알파 채널 / 내용 유효")

    for cdir, definition in characters:
        outputs = definition.get("outputs") or {}
        entries = []
        if outputs.get("preview"):
            entries.append(("preview", outputs["preview"]))
        for anim, info in (outputs.get("sheets") or {}).items():
            entries.append(("sheet:" + anim, info))
        if not entries:
            presence.fail(paths.rel(cdir), "outputs 가 비어 있다")
            continue

        for label, info in entries:
            presence.checked += 1
            img_path = os.path.join(cdir, info["file"])
            if not os.path.isfile(img_path):
                presence.fail(paths.rel(cdir), "%s 파일 없음: %s" % (label, info["file"]))
                continue

            with Image.open(img_path) as im:
                im = im.convert("RGBA")
                size = list(im.size)
                bbox = im.getbbox()
                extrema = im.getchannel("A").getextrema()

            dims.checked += 1
            if size != info["size"]:
                dims.fail(paths.rel(cdir), "%s 크기 불일치: 선언 %s / 실제 %s"
                          % (label, info["size"], size))
            if any(v <= 0 for v in size):
                dims.fail(paths.rel(cdir), "%s 크기가 0 이하다: %s" % (label, size))
            if "frame_count" in info:
                expected_w = info["cell_size"][0] * info["frame_count"]
                if size[0] != expected_w:
                    dims.fail(paths.rel(cdir),
                              "%s 시트 폭이 cell(%d) × frame(%d) = %d 과 다르다: %d"
                              % (label, info["cell_size"][0], info["frame_count"],
                                 expected_w, size[0]))

            alpha.checked += 1
            if bbox is None:
                alpha.fail(paths.rel(cdir), "%s 가 완전히 투명하다 (내용 없음)" % label)
            elif extrema[1] == 0:
                alpha.fail(paths.rel(cdir), "%s 의 알파가 전부 0 이다" % label)
            elif extrema[0] == 255:
                alpha.warn(paths.rel(cdir),
                           "%s 에 투명 픽셀이 하나도 없다 — 배경이 구워졌을 수 있다" % label)

        # 한 캐릭터의 모든 시트는 셀 크기가 같아야 한다. 다르면 Unity 에서 애니메이션이
        # 바뀔 때 캐릭터 크기와 발 위치가 튄다.
        cells = set(tuple(info["cell_size"])
                    for info in (outputs.get("sheets") or {}).values())
        if len(cells) > 1:
            dims.fail(paths.rel(cdir),
                      "시트마다 셀 크기가 다르다: %s — 애니메이션 전환 시 크기/발 위치가 튄다"
                      % sorted(cells))
    return presence, dims, alpha


def check_uniqueness(characters):
    """동일 파츠 조합 + 팔레트가 두 번 나오지 않았는가."""
    c = Check("uniqueness", "중복 조합 없음")
    seen = {}
    for cdir, definition in characters:
        c.checked += 1
        key = json.dumps(
            {"parts": {k: v for k, v in definition["parts"].items() if v},
             "palette": definition.get("palette", {}).get("groups", {})},
            sort_keys=True, ensure_ascii=False)
        if key in seen:
            c.fail(paths.rel(cdir), "seed %s 와 조합이 완전히 같다"
                   % os.path.basename(seen[key]))
        else:
            seen[key] = cdir
    return c


def check_license_propagation(rule, characters, license_summary):
    """라이선스 제한이 생성물 전체에 실려 있는가.

    이건 상업 사용 가능 여부를 판정하는 검사가 아니라, **제한이 유실되지 않았는지**
    를 보는 검사다. 비상업 팩이어도 제한만 제대로 붙어 있으면 pass 다.
    """
    c = Check("license_propagation", "라이선스 제한 전파")
    expected = license_summary["commercial_release_eligible"]
    for cdir, _definition in characters:
        gpath = os.path.join(cdir, "generation.json")
        c.checked += 1
        if not os.path.isfile(gpath):
            c.fail(paths.rel(cdir), "generation.json 이 없다")
            continue
        gen = _load_json(gpath)
        lic = gen.get("license") or {}
        if "commercial_release_eligible" not in gen:
            c.fail(paths.rel(cdir), "generation.json 에 commercial_release_eligible 이 없다")
        elif gen["commercial_release_eligible"] != expected:
            c.fail(paths.rel(cdir),
                   "commercial_release_eligible 불일치: 기록 %r / 라이선스 %r"
                   % (gen["commercial_release_eligible"], expected))
        if lic.get("commercial_use") != license_summary["commercial_use"]:
            c.fail(paths.rel(cdir),
                   "commercial_use 불일치: 기록 %r / 라이선스 %r"
                   % (lic.get("commercial_use"), license_summary["commercial_use"]))
        if not expected and "warning" not in lic:
            c.fail(paths.rel(cdir), "비상업 팩인데 경고 문구가 누락됐다")

    manifest = os.path.join(paths.UNITY_EXPORT, "characters", rule["profile"],
                            "manifest.json")
    if os.path.isfile(manifest):
        c.checked += 1
        data = _load_json(manifest)
        if data.get("commercial_release_eligible") != expected:
            c.fail(paths.rel(manifest),
                   "Unity manifest 의 commercial_release_eligible 불일치: %r"
                   % data.get("commercial_release_eligible"))
    else:
        c.warn(paths.rel(manifest), "Unity export 가 아직 없다 — 전파 검사에서 제외")
    return c


def check_determinism(rule_path, characters):
    """같은 seed 로 다시 생성했을 때 바이트가 같은가."""
    c = Check("determinism", "동일 seed 재생성 결과 일치")
    tmp = tempfile.mkdtemp(prefix="ap2d_determinism_")
    try:
        generate_mod.generate(rule_path, out_root=tmp, verbose=False)
        for cdir, definition in characters:
            seed_dir = os.path.join(tmp, str(definition["seed"]))
            if not os.path.isdir(seed_dir):
                c.fail(paths.rel(cdir), "재생성 결과에 seed %d 가 없다" % definition["seed"])
                continue
            for name in sorted(os.listdir(cdir)):
                original = os.path.join(cdir, name)
                if not os.path.isfile(original):
                    continue
                c.checked += 1
                replay = os.path.join(seed_dir, name)
                if not os.path.isfile(replay):
                    c.fail(paths.rel(cdir), "재생성 결과에 %s 가 없다" % name)
                elif _sha256(original) != _sha256(replay):
                    c.fail(paths.rel(cdir), "%s 가 재생성 결과와 다르다 (비결정적)" % name)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return c


# ── 실행 ───────────────────────────────────────────────────────────────────

def observe_distribution(characters, rule, cat):
    """슬롯마다 후보 중 몇 개가 실제로 나왔는지 **센다.**

    이건 검사가 아니라 관측이다. 임계값도 등급도 없고 status 에 영향을 주지 않는다.
    "후보 5개 중 2개를 썼다" 는 셀 수 있는 사실이고, 그게 좋은지 나쁜지는 사람이 정한다.
    (`00_DOCS/DIRECTOR_CONTEXT.md` §1 — validator 는 사실만 본다.)

    PASS 표만으로는 열 명이 사실상 한 명인 population 을 구분할 수 없어서 넣었다.
    """
    total = len(characters)
    catalog_parts = cat.get("parts") or {}
    slots = []
    for slot_name in rule["layer_order"]:
        slot = rule["slots"][slot_name]
        allowed = rules.candidates_for(slot, cat)
        counts = {}
        empty = 0
        for _dir, defn in characters:
            value = (defn.get("parts") or {}).get(slot_name)
            if not value:
                empty += 1
                continue
            counts[value] = counts.get(value, 0) + 1
        filled = total - empty
        top = max(counts.values()) if counts else 0
        slots.append({
            "slot": slot_name,
            "catalog_candidates": len(catalog_parts.get(slot_name) or {}),
            "allowed_candidates": len(allowed),
            "used": len(counts),
            "empty": empty,
            "most_common": max(counts, key=counts.get) if counts else None,
            "most_common_share": round(top / filled, 3) if filled else 0.0,
            "counts": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        })

    # 팔레트는 슬롯과 축이 달라서 따로 센다. 팔레트를 안 쓰는 규칙에서는 빈 목록이다.
    # 세는 단위는 `palette.groups` 의 group -> ramp 다 (슬롯별 적용 결과가 아니라
    # 그룹마다 어떤 램프를 골랐는가). 팔레트를 안 쓰면 이 키 자체가 없다.
    palette_groups = {}
    for _dir, defn in characters:
        groups = (defn.get("palette") or {}).get("groups") or {}
        for group, ramp in groups.items():
            palette_groups.setdefault(group, {})
            palette_groups[group][ramp] = palette_groups[group].get(ramp, 0) + 1
    palettes = []
    for group, counts in sorted(palette_groups.items()):
        top = max(counts.values())
        palettes.append({
            "group": group,
            "used": len(counts),
            "most_common_share": round(top / sum(counts.values()), 3),
            "counts": dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))),
        })

    return {"population": total, "slots": slots, "palette_groups": palettes}


def run(rule_path):
    rule_raw = generate_mod._peek_rule(rule_path)
    cat = catalog_mod.load_catalog(rule_raw["catalog"])
    from . import palette as palette_mod
    pal = palette_mod.load(rule_raw["palettes"]["source"]) if rule_raw.get("palettes") else None
    rule = rules.load(rule_path, catalog=cat, pal=pal)

    profile_dir = os.path.join(paths.GEN_CHARACTERS, rule["profile"])
    if not os.path.isdir(profile_dir):
        raise RuntimeError("생성 결과가 없다: %s — 먼저 generate 를 돌려라"
                           % paths.rel(profile_dir))

    characters = [(d, _load_json(os.path.join(d, "character.json")))
                  for d in _character_dirs(profile_dir)]

    expected = sum(len(a["_seeds"]) for a in rule["archetypes"])
    checks = []

    count_check = Check("population", "생성 개수 일치")
    count_check.checked = len(characters)
    if len(characters) != expected:
        count_check.fail(paths.rel(profile_dir),
                         "규칙은 %d개를 요구하는데 %d개가 있다" % (expected, len(characters)))
    checks.append(count_check)

    license_summary = licensing.summarize(licensing.load(rule["pack"]))

    checks.append(check_source_integrity(cat))
    checks.append(check_catalog_reference(cat, characters, rule))
    checks.append(check_asset_presence(characters))
    checks.extend(check_outputs(characters))
    checks.append(check_uniqueness(characters))
    checks.append(check_license_propagation(rule, characters, license_summary))
    checks.append(check_determinism(rule_path, characters))

    report = {
        "schema": "ap2d.validation/1",
        "rule": rule["_path"],
        "profile": rule["profile"],
        "pack": rule["pack"],
        "characters": len(characters),
        "expected_characters": expected,
        "status": "pass" if all(c.passed for c in checks) else "fail",
        # 검증 통과 여부와 상업 출시 자격은 별개의 축이다.
        # 여기서 막지는 않지만, 값은 반드시 계산되어 리포트에 남는다.
        "license": license_summary,
        "commercial_release_eligible":
            license_summary["commercial_release_eligible"],
        # 파일 단위 attribution 을 population 전체로 합친다.
        # credits 가 없는 팩에서는 빈 블록이라 기존 팩에 영향이 없다.
        "attribution": attribution.merge([
            _load_json(os.path.join(d, "generation.json")).get("attribution") or {}
            for d, _defn in characters
            if os.path.isfile(os.path.join(d, "generation.json"))
        ]),
        "checks": [c.to_dict() for c in checks],
        # 검사가 아니라 관측이다. status 에 영향을 주지 않는다.
        "distribution": observe_distribution(characters, rule, cat),
    }
    return report, characters


def render_markdown(report):
    lic = report.get("license", {})
    eligible = report.get("commercial_release_eligible", False)

    L = ["# 검증 리포트 — %s" % report["profile"], ""]
    L.append("자동 생성됨: `tools/validate_generated.py`.")
    L.append("")
    if not eligible:
        L.append("> ⛔ **%s**" % licensing.NONCOMMERCIAL_BANNER)
        L.append(">")
        L.append("> 소스 팩 `%s` — 라이선스 `%s`, `commercial_use: %s`."
                 % (report["pack"], lic.get("license"), lic.get("commercial_use")))
        L.append("> 검증 PASS 는 **파이프라인 정합성**을 뜻하지 상업 사용 허가를 뜻하지 않는다.")
        L.append("")
    L.append("| 항목 | 값 |")
    L.append("|---|---|")
    L.append("| 규칙 | `%s` |" % report["rule"])
    L.append("| 팩 | `%s` |" % report["pack"])
    L.append("| 캐릭터 수 | %d / %d |" % (report["characters"], report["expected_characters"]))
    L.append("| 전체 결과 | **%s** |" % report["status"].upper())
    L.append("| 라이선스 | `%s` |" % lic.get("license"))
    L.append("| 상업적 사용 | `%s` |" % lic.get("commercial_use"))
    L.append("| commercial_release_eligible | **%s** |" % str(eligible).lower())
    L.append("")
    L.append("## 검사 결과")
    L.append("")
    L.append("| 검사 | 결과 | 검사 항목 수 | 실패 | 경고 |")
    L.append("|---|---|---:|---:|---:|")
    for c in report["checks"]:
        L.append("| %s | %s | %d | %d | %d |" % (
            c["title"],
            "✅ PASS" if c["status"] == "pass" else "❌ FAIL",
            c["items_checked"], len(c["failures"]), len(c["warnings"])))
    L.append("")

    dist = report.get("distribution")
    if dist and dist["slots"]:
        L.append("## 관측된 분포")
        L.append("")
        L.append("**검사가 아니다.** 합격선도 임계값도 없다 — 후보 중 몇 개가 실제로")
        L.append("나왔는지를 셀 뿐이고, 그 숫자가 좋은지 나쁜지는 사람이 정한다.")
        L.append("")
        L.append("| 슬롯 | 팩 후보 | 규칙 허용 | 사용됨 | 최빈값 | 최빈 비율 | 미사용 |")
        L.append("|---|---:|---:|---:|---|---:|---:|")
        for row in dist["slots"]:
            L.append("| `%s` | %d | %d | **%d** | `%s` | %.0f%% | %d |" % (
                row["slot"], row["catalog_candidates"], row["allowed_candidates"],
                row["used"], row["most_common"] or "—",
                row["most_common_share"] * 100, row["empty"]))
        L.append("")
        L.append("`팩 후보` 는 카탈로그가 가진 수, `규칙 허용` 은 allow/deny 를 적용한 수, "
                 "`사용됨` 은 이 population 에 실제로 나온 수다. "
                 "`미사용` 은 그 슬롯이 비어 있던 캐릭터 수다.")
        L.append("")
        if dist["palette_groups"]:
            L.append("| 팔레트 그룹 | 사용됨 | 최빈 비율 |")
            L.append("|---|---:|---:|")
            for row in dist["palette_groups"]:
                L.append("| `%s` | %d | %.0f%% |" % (
                    row["group"], row["used"], row["most_common_share"] * 100))
            L.append("")

    problems = [c for c in report["checks"] if c["failures"] or c["warnings"]]
    if not problems:
        L.append("실패도 경고도 없음.")
        L.append("")
    for c in problems:
        L.append("### %s (`%s`)" % (c["title"], c["check"]))
        L.append("")
        for f in c["failures"][:50]:
            L.append("- ❌ `%s` — %s" % (f["subject"], f["message"]))
        if len(c["failures"]) > 50:
            L.append("- … 외 실패 %d건" % (len(c["failures"]) - 50))
        for w in c["warnings"][:50]:
            L.append("- ⚠️ `%s` — %s" % (w["subject"], w["message"]))
        if len(c["warnings"]) > 50:
            L.append("- … 외 경고 %d건" % (len(c["warnings"]) - 50))
        L.append("")
    return "\n".join(L)


def write(report, json_path=None, md_path=None):
    json_path = json_path or os.path.join(paths.GEN_REPORTS,
                                          "%s_validation.json" % report["profile"])
    md_path = md_path or os.path.join(paths.GEN_REPORTS,
                                      "%s_validation.md" % report["profile"])
    paths.ensure_dir(os.path.dirname(json_path))
    with open(paths.assert_writable(json_path), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(paths.assert_writable(md_path), "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report))
    attribution.write_report(report["profile"], report["pack"],
                             report.get("attribution") or {},
                             report["characters"])
    return json_path, md_path
