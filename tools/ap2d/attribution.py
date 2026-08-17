"""파일 단위 provenance / attribution 집계.

pack-level licensing(`licensing.py`)은 그대로 둔다. 팩 하나에 라이선스 한 줄이
붙는 경우(CC0, Modern Interiors)에는 그게 맞는 모델이다.

문제는 LPC 처럼 **한 팩 안에서 파일마다 저자와 라이선스가 다른** 경우다.
그때 답해야 하는 질문은 이것이다:

    이 캐릭터 하나에 어떤 source asset 이 들어갔고,
    이걸 상업 게임에 쓸 때 어떤 표기 의무가 생기는가?

그래서 카탈로그의 파츠별 `credits` 를 생성물까지 실어 나른다.
credits 가 없는 팩에서는 이 모듈이 조용히 빈 결과를 낸다 — 기존 팩에 영향이 없다.

집계는 전부 정렬 기반이라 결정적이다.
"""

import os

from . import paths

SCHEMA = "ap2d.attribution/1"


def _dedup(values):
    """순서를 보존하지 않고 정렬로 중복 제거. 재현 가능해야 한다."""
    return sorted(set(v for v in values if v))


def credits_for_parts(catalog, selections):
    """selections: [(category, part_name)] -> 해당 파츠들의 credit 레코드 목록."""
    out = []
    for category, part_name in selections:
        part = (catalog["parts"].get(category) or {}).get(part_name)
        if not part:
            continue
        for credit in part.get("credits") or []:
            entry = dict(credit)
            entry["slot"] = category
            entry["asset"] = part_name
            out.append(entry)
    return out


def summarize(credits):
    """credit 레코드 목록 -> 생성물에 실을 attribution 블록."""
    if not credits:
        return {
            "schema": SCHEMA,
            "source_assets": 0,
            "authors": [],
            "licenses": [],
            "source_urls": [],
            "attribution_required": False,
            "attribution_entries": [],
            "share_alike_present": False,
        }

    authors = _dedup(a for c in credits for a in (c.get("authors") or []))
    licenses = _dedup(c.get("selected_license") for c in credits)
    urls = _dedup(u for c in credits for u in (c.get("source_urls") or []))
    share_alike = any(c.get("share_alike_required") for c in credits)
    required = any(c.get("attribution_required") for c in credits)

    # 표기 항목은 (source_file, license) 로 묶는다. 같은 파일이 여러 슬롯에서
    # 쓰여도 표기는 한 번이면 된다.
    grouped = {}
    for credit in credits:
        key = (credit.get("source_file") or "", credit.get("selected_license") or "")
        item = grouped.setdefault(key, {
            "source_file": key[0],
            "selected_license": key[1],
            "authors": set(),
            "alternative_licenses": set(),
            "source_urls": set(),
            "used_by": set(),
        })
        item["authors"].update(credit.get("authors") or [])
        item["alternative_licenses"].update(credit.get("alternative_licenses") or [])
        item["source_urls"].update(credit.get("source_urls") or [])
        item["used_by"].add("%s/%s" % (credit.get("slot"), credit.get("asset")))

    entries = []
    for key in sorted(grouped):
        item = grouped[key]
        entries.append({
            "source_file": item["source_file"],
            "selected_license": item["selected_license"],
            "authors": sorted(item["authors"]),
            "alternative_licenses": sorted(item["alternative_licenses"]),
            "source_urls": sorted(item["source_urls"]),
            "used_by": sorted(item["used_by"]),
            "text": attribution_text(sorted(item["authors"]), item["selected_license"]),
        })

    return {
        "schema": SCHEMA,
        "source_assets": len(entries),
        "authors": authors,
        "licenses": licenses,
        "source_urls": urls,
        "attribution_required": required,
        "attribution_entries": entries,
        "share_alike_present": share_alike,
    }


def attribution_text(authors, license_name):
    """게임 credits 에 그대로 넣을 수 있는 한 줄."""
    if not authors:
        return license_name or ""
    return "%s — %s" % (", ".join(authors), license_name or "license unknown")


def merge(summaries):
    """캐릭터별 attribution 여러 개를 population 하나로 합친다."""
    credits = []
    for summary in summaries:
        for entry in summary.get("attribution_entries") or []:
            for author in entry["authors"] or [None]:
                credits.append({
                    "source_file": entry["source_file"],
                    "selected_license": entry["selected_license"],
                    "authors": entry["authors"],
                    "alternative_licenses": entry["alternative_licenses"],
                    "source_urls": entry["source_urls"],
                    "attribution_required": bool(entry["selected_license"])
                    and not str(entry["selected_license"]).startswith("CC0"),
                    "share_alike_required": False,
                    "slot": entry["used_by"][0].split("/")[0] if entry["used_by"] else "",
                    "asset": entry["used_by"][0].split("/")[-1] if entry["used_by"] else "",
                })
                break
    merged = summarize(credits)
    merged["share_alike_present"] = any(s.get("share_alike_present")
                                        for s in summaries)
    return merged


def render_report(profile, pack, summary, character_count):
    L = ["# %s — attribution report" % profile, ""]
    L.append("자동 생성됨: `tools/validate_generated.py`. 손으로 고치지 않는다.")
    L.append("")
    L.append("| 항목 | 값 |")
    L.append("|---|---|")
    L.append("| 팩 | `%s` |" % pack)
    L.append("| 캐릭터 수 | %d |" % character_count)
    L.append("| 사용된 source asset | %d |" % summary["source_assets"])
    L.append("| 고유 저자 | %d |" % len(summary["authors"]))
    L.append("| 라이선스 | %s |" % (", ".join("`%s`" % l for l in summary["licenses"]) or "—"))
    L.append("| attribution 필요 | **%s** |" % str(summary["attribution_required"]).lower())
    L.append("| share_alike_present | **%s** |" % str(summary["share_alike_present"]).lower())
    L.append("")
    if not summary["attribution_entries"]:
        L.append("이 팩은 파일 단위 credits 를 제공하지 않는다 "
                 "(팩 단위 라이선스 기록만 있다).")
        L.append("")
        return "\n".join(L)

    L.append("## 게임 credits 에 넣을 표기")
    L.append("")
    L.append("아래 목록은 결정적으로 중복 제거된다. 게임 크레딧 화면의 기반 데이터로 "
             "그대로 쓸 수 있다. (완성된 credits 시스템은 아직 만들지 않는다.)")
    L.append("")
    L.append("```")
    for text in sorted(set(e["text"] for e in summary["attribution_entries"])):
        L.append(text)
    L.append("```")
    L.append("")
    L.append("## source asset 별 상세")
    L.append("")
    L.append("| source file | selected license | 대안 | 저자 | 사용된 슬롯 |")
    L.append("|---|---|---|---|---|")
    for entry in summary["attribution_entries"]:
        L.append("| `%s` | `%s` | %s | %s | %s |" % (
            entry["source_file"], entry["selected_license"],
            ", ".join("`%s`" % a for a in entry["alternative_licenses"]) or "—",
            ", ".join(entry["authors"]),
            ", ".join("`%s`" % u for u in entry["used_by"])))
    L.append("")
    L.append("## source URL")
    L.append("")
    for url in summary["source_urls"]:
        L.append("- %s" % url)
    L.append("")
    return "\n".join(L)


def write_report(profile, pack, summary, character_count, out_path=None):
    out_path = out_path or os.path.join(paths.GEN_REPORTS,
                                        "%s_attribution.md" % profile)
    paths.ensure_dir(os.path.dirname(out_path))
    with open(paths.assert_writable(out_path), "w", encoding="utf-8") as fh:
        fh.write(render_report(profile, pack, summary, character_count))
    return out_path
