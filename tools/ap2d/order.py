"""발주 회신 한 장.

이미 있는 리포트 넷(`<pack>.summary.md` · `<profile>_validation.{json,md}` ·
`<profile>_attribution.md` · contact sheet)을 없애거나 합치지 않는다. 각각 제 역할이
있다. 그 위에 **한 번에 읽는 요약 한 장**만 얹는다.

새로 계산하는 값은 없다. 검증 리포트와 규칙과 카탈로그에 이미 있는 것을 모은다.

규칙 파일의 선택적 `order` 블록이 사람이 쓴 쪽 입력이다:

    "order": {
      "purpose":  "self_verification" | "order_response",
      "consumer": "art-studio 가 발급한 식별자",     # 없으면 생략 = unknown
      "request":  "요구 원문 또는 요약",
      "not_done": [{"요구": "...", "근거": "..."}]
    }

`purpose` 는 **막는 라벨이 아니라 표시하는 라벨이다.** 자체 기술 검증도 발주 대응도
똑같이 자유롭게 하고, 산출물을 나중에 봤을 때 성격을 알 수 있게만 한다.
"""

import hashlib
import json
import os

from . import attribution as attribution_mod
from . import paths

SCHEMA = "ap2d.order_brief/1"

PURPOSES = ("self_verification", "order_response", "unknown")


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def order_block(rule_raw):
    """규칙의 `order` 블록. 없으면 unknown 으로 채운다 — 억지로 짐작하지 않는다."""
    block = dict(rule_raw.get("order") or {})
    purpose = block.get("purpose", "unknown")
    if purpose not in PURPOSES:
        purpose = "unknown"
    return {
        "purpose": purpose,
        # 소비자 식별자는 art-studio 가 발급한다. 저장소 디렉터리 이름이나 축약형을
        # 여기서 지어내지 않는다. 발급받지 못했으면 unknown 이 정당한 값이다.
        "consumer": block.get("consumer", "unknown"),
        "request": block.get("request"),
        "not_done": list(block.get("not_done") or []),
    }


def _seed_ranges(rule_raw):
    out = []
    for arch in rule_raw.get("archetypes") or []:
        spec = arch.get("seeds") or {}
        if isinstance(spec, dict) and "from" in spec:
            out.append("%s: %s–%s" % (arch.get("name", "?"), spec["from"], spec["to"]))
        elif isinstance(spec, list):
            out.append("%s: %s" % (arch.get("name", "?"),
                                   ", ".join(str(s) for s in spec)))
    return out


def build(rule_path, report=None):
    """회신 dict. report 를 주지 않으면 디스크의 검증 리포트를 읽는다."""
    rule_abs = paths.abspath(rule_path)
    rule_raw = _read(rule_abs)
    profile = rule_raw["profile"]

    if report is None:
        report_path = os.path.join(paths.GEN_REPORTS, "%s_validation.json" % profile)
        if not os.path.isfile(report_path):
            raise RuntimeError("검증 리포트가 없다: %s — validate 를 먼저 돌려라"
                               % paths.rel(report_path))
        report = _read(report_path)

    catalog_abs = paths.abspath(rule_raw["catalog"])
    order = order_block(rule_raw)

    checks = report.get("checks") or []
    failed = [c for c in checks if c["status"] != "pass"]
    warned = [c for c in checks if c.get("warnings")]

    # 기계가 아는 「못 한 것」. 사람이 쓴 not_done 과 합쳐 ⑥ 이 된다.
    observed = []
    for c in failed:
        for f in (c.get("failures") or [])[:5]:
            observed.append({"요구": "%s — %s" % (c["title"], f["subject"]),
                             "근거": f["message"]})
    lic = report.get("license") or {}
    if not report.get("commercial_release_eligible", False):
        observed.append({
            "요구": "상업 출시",
            "근거": "소스 팩 `%s` 의 `commercial_use: %s` — 생성은 되지만 출시 자격이 없다"
                    % (report.get("pack"), lic.get("commercial_use")),
        })

    return {
        "schema": SCHEMA,
        "profile": profile,
        "pack": report.get("pack"),
        "order": order,
        "coordinates": {
            "rule": paths.rel(rule_abs),
            "rule_sha256": _sha256(rule_abs),
            "catalog": paths.rel(catalog_abs),
            # 카탈로그는 소스 파일 전체의 sha256 을 품고 있다. 그래서 이 한 값이
            # "어느 팩 상태였나" 를 고정한다.
            "catalog_sha256": _sha256(catalog_abs),
            "seeds": _seed_ranges(rule_raw),
            "palette": (rule_raw.get("palettes") or {}).get("source"),
            "animations": rule_raw.get("animations") or [],
        },
        "verification": {
            "status": report.get("status"),
            "checks": len(checks),
            "passed": len(checks) - len(failed),
            "failed": len(failed),
            "with_warnings": len(warned),
            "characters": report.get("characters"),
            "expected_characters": report.get("expected_characters"),
        },
        "release": {
            "commercial_release_eligible": report.get("commercial_release_eligible", False),
            "license": lic.get("license"),
            "commercial_use": lic.get("commercial_use"),
            "attribution_required": (report.get("attribution") or {}).get(
                "attribution_required", False),
            "share_alike_present": (report.get("attribution") or {}).get(
                "share_alike_present", False),
            "authors": (report.get("attribution") or {}).get("authors") or [],
        },
        "distribution": report.get("distribution") or {},
        "not_done": order["not_done"] + observed,
    }


# ── 렌더 ────────────────────────────────────────────────────────────────

PURPOSE_LABEL = {
    "self_verification": "자체 기술 검증",
    "order_response": "발주 대응",
    "unknown": "unknown (규칙이 선언하지 않았다)",
}


def render_markdown(brief):
    rel = brief["release"]
    order = brief["order"]
    coord = brief["coordinates"]
    ver = brief["verification"]

    L = ["# 발주 회신 — %s" % brief["profile"], ""]
    L.append("자동 생성됨: `python3 tools/order_brief.py <규칙>`. 손으로 고치지 않는다.")
    L.append("")

    # ── 출시 신호는 맨 위에, 사람이 읽는 형태로 ──
    if rel["commercial_release_eligible"]:
        L.append("> ✅ **상업 출시 가능** — 소스 팩 라이선스 `%s`, `commercial_use: %s`."
                 % (rel["license"], rel["commercial_use"]))
    else:
        L.append("> ⛔ **상업 출시 불가** — 소스 팩 라이선스 `%s`, `commercial_use: %s`."
                 % (rel["license"], rel["commercial_use"]))
        L.append("> 생성과 검증은 정상이다. 출시 자격만 없다.")
    if rel["attribution_required"]:
        L.append("> · **출처 표기 필요** — 기여자 %d명. `%s_attribution.md` 참조."
                 % (len(rel["authors"]), brief["profile"]))
    if rel["share_alike_present"]:
        L.append("> · **share-alike 포함** — 파생물에 같은 조건이 따라붙는다.")
    L.append("")

    # ── ① 무엇을 요청받았나 ──
    L.append("## ① 무엇을 요청받았나")
    L.append("")
    L.append("| 항목 | 값 |")
    L.append("|---|---|")
    L.append("| 성격 | **%s** |" % PURPOSE_LABEL[order["purpose"]])
    L.append("| 소비자 | `%s` |" % order["consumer"])
    L.append("| 프로파일 | `%s` |" % brief["profile"])
    L.append("| 팩 | `%s` |" % brief["pack"])
    L.append("")
    if order["request"]:
        L.append("> %s" % order["request"].replace("\n", "\n> "))
    else:
        L.append("요구 원문 없음 — 이 산출물은 발주에서 나온 것이 아니다.")
    L.append("")

    # ── ② 재현 좌표 ──
    L.append("## ② 재현 좌표")
    L.append("")
    L.append("승인은 PNG 가 아니라 여기에 건다. 이 다섯 값이 같으면 결과는 바이트까지 같다.")
    L.append("")
    L.append("| 좌표 | 값 |")
    L.append("|---|---|")
    L.append("| 규칙 | `%s` |" % coord["rule"])
    L.append("| 규칙 sha256 | `%s` |" % coord["rule_sha256"])
    L.append("| 카탈로그 | `%s` |" % coord["catalog"])
    L.append("| 카탈로그 sha256 | `%s` |" % coord["catalog_sha256"])
    L.append("| seed | %s |" % (" · ".join(coord["seeds"]) or "—"))
    L.append("| 팔레트 | %s |" % ("`%s`" % coord["palette"] if coord["palette"] else "없음"))
    L.append("| 애니메이션 | %s |" % (" · ".join("`%s`" % a for a in coord["animations"]) or "—"))
    L.append("")
    L.append("카탈로그 sha256 은 소스 파일 전체의 해시를 품고 있다 — 팩이 한 바이트라도")
    L.append("달랐다면 이 값이 달라진다.")
    L.append("")
    L.append("```bash")
    L.append("python3 tools/run_pipeline.py %s" % coord["rule"])
    L.append("```")
    L.append("")

    # ── ③ 기술 검증 ──
    L.append("## ③ 기술 검증")
    L.append("")
    L.append("| 전체 | 검사 | 통과 | 실패 | 경고 있음 | 캐릭터 |")
    L.append("|---|---:|---:|---:|---:|---:|")
    L.append("| **%s** | %d | %d | %d | %d | %d / %d |" % (
        (ver["status"] or "?").upper(), ver["checks"], ver["passed"], ver["failed"],
        ver["with_warnings"], ver["characters"] or 0, ver["expected_characters"] or 0))
    L.append("")
    L.append("상세는 `%s_validation.md`. 검증 PASS 는 **파이프라인 정합성**을 뜻하지"
             % brief["profile"])
    L.append("채택이나 출시 허가를 뜻하지 않는다.")
    L.append("")

    # ── ④ 출시 신호 ──
    L.append("## ④ 출시 신호")
    L.append("")
    L.append("| 신호 | 값 |")
    L.append("|---|---|")
    L.append("| commercial_release_eligible | **%s** |"
             % str(rel["commercial_release_eligible"]).lower())
    L.append("| 라이선스 | `%s` |" % rel["license"])
    L.append("| commercial_use | `%s` |" % rel["commercial_use"])
    L.append("| 출처 표기 필요 | %s |" % str(rel["attribution_required"]).lower())
    L.append("| share-alike | %s |" % str(rel["share_alike_present"]).lower())
    L.append("| 기여자 수 | %d |" % len(rel["authors"]))
    L.append("")

    # ── ⑤ 관측된 분포 ──
    L.append("## ⑤ 관측된 분포")
    L.append("")
    dist = brief["distribution"]
    if dist.get("slots"):
        L.append("검사가 아니라 관측이다. 후보 중 몇 개가 실제로 나왔는지만 센다.")
        L.append("")
        L.append("| 슬롯 | 팩 후보 | 규칙 허용 | 사용됨 | 최빈 비율 |")
        L.append("|---|---:|---:|---:|---:|")
        for row in dist["slots"]:
            L.append("| `%s` | %d | %d | **%d** | %.0f%% |" % (
                row["slot"], row["catalog_candidates"], row["allowed_candidates"],
                row["used"], row["most_common_share"] * 100))
        L.append("")
        for row in dist["palette_groups"]:
            L.append("- 팔레트 `%s` — %d개 사용, 최빈 %.0f%%"
                     % (row["group"], row["used"], row["most_common_share"] * 100))
        if dist["palette_groups"]:
            L.append("")
    else:
        L.append("관측 없음.")
        L.append("")

    # ── ⑥ 못 한 것 ──
    L.append("## ⑥ 못 한 것 · 거절한 것")
    L.append("")
    if brief["not_done"]:
        L.append("| 요구 | 근거 |")
        L.append("|---|---|")
        for item in brief["not_done"]:
            L.append("| %s | %s |" % (item.get("요구", "?"), item.get("근거", "?")))
        L.append("")
    else:
        L.append("**없음.** (누락이 아니라 정말로 없다 — 요구를 전부 수행했고 "
                 "거절한 것도 없다.)")
        L.append("")
    return "\n".join(L)


def write(brief, md_path=None, json_path=None):
    md_path = md_path or os.path.join(paths.GEN_REPORTS,
                                      "%s_brief.md" % brief["profile"])
    json_path = json_path or os.path.join(paths.GEN_REPORTS,
                                          "%s_brief.json" % brief["profile"])
    paths.ensure_dir(os.path.dirname(md_path))
    with open(paths.assert_writable(md_path), "w", encoding="utf-8") as fh:
        fh.write(render_markdown(brief))
    with open(paths.assert_writable(json_path), "w", encoding="utf-8") as fh:
        json.dump(brief, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return md_path, json_path
