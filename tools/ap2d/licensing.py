"""라이선스 게이트.

CLAUDE.md: "라이선스가 불확실한 에셋은 00_DOCS/licenses/ 에 확인 전까지
생성 파이프라인에 넣지 않는다."

이를 강제하기 위해 00_DOCS/licenses/<pack>.md 상단에 기계가 읽을 수 있는
frontmatter 블록을 요구한다. 문서 본문은 licenses/README.md 템플릿 그대로 사람이 읽는다.

    ---
    pack: rgsdev_...
    license: CC0-1.0
    commercial_use: yes
    modification: yes
    redistribution: ...
    ai_training: ...
    pipeline_approved: yes
    ---

pipeline_approved 가 yes 가 아니면 generator 진입을 막는다.
"""

import os

from . import paths

REQUIRED_FIELDS = (
    "pack",
    "license",
    "commercial_use",
    "modification",
    "redistribution",
    "ai_training",
    "pipeline_approved",
    "acquired",
    "source_url",
)

_TRUE = ("yes", "true", "allowed", "permitted", "1")
_FALSE = ("no", "false", "prohibited", "forbidden", "0")

# capability 는 3상태다. unknown 을 yes 로 반올림하지 않는다.
YES, NO, UNKNOWN = "yes", "no", "unknown"

NONCOMMERCIAL_BANNER = (
    "NON-COMMERCIAL SOURCE — generated outputs are not approved for "
    "commercial game use."
)


class LicenseError(RuntimeError):
    pass


def capability(fields, name):
    """라이선스 필드를 yes / no / unknown 셋 중 하나로 정규화한다."""
    raw = str(fields.get(name, "")).strip().lower()
    if raw in _TRUE:
        return YES
    if raw in _FALSE:
        return NO
    return UNKNOWN


def license_path(pack_name):
    return os.path.join(paths.LICENSES, pack_name + ".md")


def parse_frontmatter(text):
    """--- 로 감싼 key: value 블록을 파싱한다 (YAML 의존성 없이 최소 구현)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise LicenseError("frontmatter 블록(---)이 파일 맨 위에 없다")
    fields = {}
    for i, line in enumerate(lines[1:], start=2):
        if line.strip() == "---":
            return fields
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise LicenseError("frontmatter %d행을 해석할 수 없다: %r" % (i, line))
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    raise LicenseError("frontmatter 닫는 --- 가 없다")


def load(pack_name):
    """라이선스 기록을 읽어 dict 로 반환. 없거나 불완전하면 LicenseError."""
    path = license_path(pack_name)
    if not os.path.isfile(path):
        raise LicenseError(
            "라이선스 기록이 없다: %s — 확인 전에는 파이프라인에 넣지 않는다"
            % paths.rel(path)
        )
    with open(path, "r", encoding="utf-8") as fh:
        fields = parse_frontmatter(fh.read())
    missing = [f for f in REQUIRED_FIELDS if f not in fields]
    if missing:
        raise LicenseError(
            "%s 에 필수 항목 누락: %s" % (paths.rel(path), ", ".join(missing))
        )
    if fields["pack"] != pack_name:
        raise LicenseError(
            "pack 이름 불일치: 파일에는 %r, 요청은 %r" % (fields["pack"], pack_name)
        )
    return fields


def summarize(fields):
    """생성물에 따라다닐 machine-readable 라이선스 요약.

    세 상태를 구분한다:
      pipeline 사용 가능 + 상업 가능   -> commercial_release_eligible: true   (CC0)
      pipeline 사용 가능 + 상업 금지   -> commercial_release_eligible: false  (Modern Interiors Free)
      pipeline 사용 불가              -> 애초에 require_approved 가 막는다
    """
    commercial = capability(fields, "commercial_use")
    # unknown 은 eligible 로 치지 않는다. 모르면 안 되는 쪽으로 판단한다.
    eligible = commercial == YES
    summary = {
        "pack": fields["pack"],
        "license": fields["license"],
        "commercial_use": commercial,
        "modification": capability(fields, "modification"),
        "redistribution": capability(fields, "redistribution"),
        "ai_training": capability(fields, "ai_training"),
        "pipeline_approved": capability(fields, "pipeline_approved"),
        # 표기 의무는 상업 사용 가능 여부와 **독립된 축**이다. commercial_use: yes 여도
        # CC-BY / OGA-BY 는 저자 표기 없이 배포하면 라이선스 위반이다. 이 값이 요약에
        # 없으면 소비자 패키지까지 따라가는 신호가 끊긴다 (실제로 끊겨 있었다).
        "credit_required": capability(fields, "credit_required"),
        "commercial_release_eligible": eligible,
        "record": paths.rel(license_path(fields["pack"])),
    }
    if not eligible:
        summary["warning"] = NONCOMMERCIAL_BANNER
    return summary


def require_approved(pack_name):
    """생성 단계 진입 게이트. 승인되지 않았으면 예외.

    commercial_use 는 이 게이트를 막지 않는다. 비상업 팩도 검증 목적의 생성은
    라이선스가 허용하기 때문이다. 대신 summarize() 가 제한을 결과물에 실어 나른다.
    """
    fields = load(pack_name)
    if capability(fields, "pipeline_approved") != YES:
        raise LicenseError(
            "%s 는 pipeline_approved 가 아니다 (현재: %r). 생성 단계 진입 차단."
            % (pack_name, fields["pipeline_approved"])
        )
    if capability(fields, "modification") != YES:
        raise LicenseError(
            "%s 는 수정(파츠 조합/색변경)이 허용되지 않는다 (현재: %r). 생성 단계 진입 차단."
            % (pack_name, fields["modification"])
        )
    return fields
