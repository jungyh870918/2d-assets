---
pack: limezu_modern-interiors-free_v2.2
display_name: Modern Interiors — RPG Tileset [16x16] (FREE VERSION)
author: LimeZu
source_url: https://limezu.itch.io/moderninteriors
license: LimeZu Free Version License (proprietary)
license_file: 01_SOURCE/environments/limezu_modern-interiors-free_v2.2/Modern tiles_Free/LICENSE.txt
commercial_use: no
modification: yes
redistribution: no
ai_training: unknown
credit_required: unknown
acquired: 2026-08-16
pipeline_approved: yes
---

# Modern Interiors — RPG Tileset [16x16] 무료판 (LimeZu)

- 출처 URL: https://limezu.itch.io/moderninteriors
- 제작자: LimeZu
- 취득일 / 버전: 2026-08-16, `Modern_Interiors_Free_v2.2.zip` (무료판 v2.2)
- 가격: 무료 (정식판 별도 판매)
- 라이선스 원문 위치: 팩 루트의 `LICENSE.txt`

## 라이선스 원문 (전문)

```
FREE VERSION LICENSE:

CAN:
YOU CAN USE THE ASSET IN NON COMMERCIAL PROJECTS
YOU CAN EDIT THE SPRITES AND USE THEM IN NON COMMERCIAL PROJECTS

CAN'T:
YOU CAN'T USE THE ASSET IN COMMERCIAL PROJECTS
YOU CAN'T EDIT THE SPRITES AND USE THEM IN COMMERCIAL PROJECTS
YOU CAN'T EDIT AND RESELL THE SPRITES
```

## 허용

- [x] 수정(색변경 / 파츠 조합 / 리사이즈) — **비상업 목적에 한함**
- [x] 비상업 프로젝트에 사용

## 금지

- [x] **상업 프로젝트 사용 금지** — `commercial_use: no`
- [x] **상업 목적 수정본 사용 금지**
- [x] 스프라이트 수정 후 재판매 금지
- [x] 에셋 재배포 금지 — `redistribution: no`
- [ ] 생성형 AI 학습: 라이선스 원문에 언급 없음 → `ai_training: unknown`.
      명시적 허용이 아니므로 이 저장소에서는 금지로 취급한다.
      (CLAUDE.md: 구매/비CC0 에셋 이미지를 외부 이미지 생성 AI에 보내지 않는다)
- [ ] 크레딧 표기: 원문에 언급 없음 → `unknown`

## 파이프라인에서의 취급

**이 팩은 파이프라인 일반화 검증용이다. 상업 출시용이 아니다.**

`pipeline_approved: yes` 이지만 `commercial_use: no` 다. 이 저장소의 라이선스 게이트는
두 값을 분리해서 다룬다:

| 단계 | 허용 여부 | 근거 |
|---|---|---|
| catalog scan | 가능 | 카탈로그는 파일명/치수/해시 메타데이터일 뿐 원본 아트가 아니다 |
| generation (비상업 검증) | 가능 | 원문이 "EDIT THE SPRITES ... IN NON COMMERCIAL PROJECTS" 를 명시적으로 허용 |
| Unity export | 가능 | 위와 동일. 단 결과물에 제한이 따라붙는다 |
| **상업 출시** | **불가** | `commercial_release_eligible: false` |

이 팩에서 나온 모든 생성물은 `05_GENERATED` / `06_UNITY_EXPORT` 메타데이터와
validation 리포트에 `commercial_use: false` 와 `commercial_release_eligible: false` 를
달고 다닌다. 사람이 리포트만 봐도 놓치지 않도록 markdown 상단에 경고 배너가 붙는다.

## 메모

- 무료판은 정식판의 약 1% 분량이다 (`READ ME.txt` 원문: *"This version has around 1%
  of material of the full asset"*). 정식판($1.20)과 달리 **개별 prop PNG 가 없고**
  전부 atlas / tilesheet 다. 이 때문에 environment variation POC 는 이번 단계에서
  SKIPPED 로 처리했다 — 자세한 근거는
  [02_CATALOG/limezu_modern-interiors-free_v2.2.summary.md](../../02_CATALOG/limezu_modern-interiors-free_v2.2.summary.md)
- 원본 zip(`Modern_Interiors_Free_v2.2.zip`)은 저장소 루트에 받은 그대로 두었다.
  압축 해제본만 팩 폴더로 정리했고 zip 내부 구조를 그대로 보존했다.
- 정식판을 구매하면 팩 이름이 달라지므로(`limezu_modern-interiors_v50` 등) 별도의
  라이선스 기록을 새로 쓴다. 이 파일을 고쳐 쓰지 않는다.
