---
pack: unknown_free-hd-survivor-w-bike_v1
display_name: FREE Character HD Survivor W Bike
author: SmallScaleInt
source_product: Character Creator 2D - Modern
source_url: https://smallscaleint.itch.io/character-creator-2d-modern
provenance: official free download / pre-exported character
license: unknown
license_file: none
commercial_use: unknown
modification: unknown
redistribution: unknown
ai_training: unknown
credit_required: unknown
acquired: 2026-08-16
pipeline_approved: no
---

# FREE Character HD Survivor W Bike — 출처 확인 / **라이선스 미확인**

> **provenance 와 license capability 를 동일시하지 않는다.**
> 누가 만들었고 어디서 받았는지는 확인됐지만, 그것이 상업 이용 허가를 뜻하지는 않는다.
> 상업 조건을 명시적으로 증명하기 전까지 `commercial_use: unknown` /
> `pipeline_approved: no` 를 유지한다.

## 출처 (확인됨)

- 제작자: **SmallScaleInt**
- 원 상품: **Character Creator 2D - Modern**
- 상품 페이지: https://smallscaleint.itch.io/character-creator-2d-modern
- 경위: 공식 페이지에서 무료로 제공되는 **pre-exported character** 파일.
  공식 페이지가 이 캐릭터를 Character Creator 로 만든 무료 예제로 명시하고 있고,
  배포 파일명이 이 zip 과 일치한다.
- SmallScaleInt 는 `00_DOCS/asset-shortlist.md` Tier 1/2 에 이미 올라 있는 제작자다.

## 라이선스 (여전히 미확인)

> ⛔ **이 팩은 generation 파이프라인에 진입할 수 없다.**
> `pipeline_approved: no` — CLAUDE.md: "라이선스가 불확실한 에셋은
> `00_DOCS/licenses/` 에 확인 전까지 생성 파이프라인에 넣지 않는다."

- 취득일: 2026-08-16 (`FREE Character HD Survivor W Bike.zip`, 저장소 루트)
- 버전: 표기 없음. 파일 타임스탬프 2025-04-30 기준본 → 폴더명 `_v1`
- 라이선스 원문 위치: **없음**

archive 안에 PNG 23장 **외에 아무것도 없다.** LICENSE / README / .url 이 전부 없다.

```
FREE Character HD Survivor W Bike/
  Attack1.png … Walk.png      (23장, 전부 1792x1024)
```

출처가 확인됐다고 해서 라이선스 조항이 확인된 것은 아니다. 이 저장소는
**archive 안의 라이선스 원문 또는 명시적으로 증명 가능한 상품 조항**을 근거로만
capability 를 채운다. 그 근거가 없으므로 전 항목 `unknown` 을 유지한다.

폴더명의 `unknown_` 접두어는 제작자가 미상이라는 뜻이 아니라, **팩을 넣을 당시
출처가 확정되지 않았다**는 이력이다. 팩 폴더 이름은 카탈로그·라이선스 기록의 키라
바꾸면 세 곳이 함께 깨지므로 이번에는 바꾸지 않는다. 라이선스가 확정되어
파이프라인에 실제로 투입할 때 `smallscaleint_hd-survivor-w-bike_v1` 로 함께 옮긴다.

## 확인하는 방법

위 상품 페이지의 라이선스 조항에서 다음을 확인해 채우면 된다.

- `license`, `commercial_use`, `modification`, `redistribution`, `ai_training`
- 확인 후 `pipeline_approved: yes` 로 바꾸면 generation 게이트가 열린다.

## 현재 취급

| 단계 | 허용 | 근거 |
|---|---|---|
| catalog scan | **가능** | 카탈로그는 파일명/치수/해시 메타데이터일 뿐 원본 아트가 아니다 |
| generation | **차단** | `pipeline_approved: no` → `licensing.require_approved()` 가 예외로 막는다 |
| Unity export | **차단** | generation 이 없으므로 대상 자체가 없다 |
| 상업 출시 | **불가** | `commercial_release_eligible: false` |

다만 이 팩은 **라이선스와 무관하게 구조적으로도** modular generation 대상이 아니다.
파츠가 분리되어 있지 않고 완성 캐릭터 시트만 있다. 자세한 실측:
[02_CATALOG/unknown_free-hd-survivor-w-bike_v1.summary.md](../../02_CATALOG/unknown_free-hd-survivor-w-bike_v1.summary.md)

## 메모

- 원본 zip 은 저장소 루트에 받은 그대로 두었다. 압축 해제본만 팩 폴더로 정리했고
  zip 내부 구조를 그대로 보존했다.
- 이 팩은 **generation layer 의 숨은 전제를 검증하기 위한 측정 대상**으로 넣었다.
  아트 소스로 쓰기 위해 넣은 것이 아니다.
