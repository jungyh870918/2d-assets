---
pack: lpc_ulpc-generator_phase1
display_name: Universal LPC Spritesheet Character Generator — Phase 1 subset
author: multiple (16 contributors — CREDITS.csv 참조)
source_url: https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator
provenance: upstream git repository / deterministic metadata-driven subset
license: per-asset (OGA-BY 3.0 / CC-BY 3.0 / CC0-1.0)
license_file: 01_SOURCE/characters/lpc_ulpc-generator_phase1/CREDITS.csv
commercial_use: yes
modification: yes
redistribution: yes
ai_training: unknown
credit_required: yes
acquired: 2026-08-16
pipeline_approved: yes
---

# Universal LPC Spritesheet Character Generator — Phase 1 subset

> ⚠️ **attribution 필수.** 이 팩의 결과물을 배포할 때 저자 표기가 의무다.
> `commercial_use: yes` 이지만 조건 없는 사용이 아니다.

## 코드 라이선스와 에셋 라이선스는 다르다

| 대상 | 라이선스 | 근거 |
|---|---|---|
| generator **코드** | GPL-3.0 | 저장소 루트 `LICENSE` |
| sprite **에셋** | 파일마다 다름 | `CREDITS.csv` + 각 `sheet_definitions/*.json` 의 `credits` |

저장소 루트의 GPL-3.0 은 **generator 프로그램**에 붙은 것이다. 이 저장소는 그
프로그램을 쓰지 않고 스프라이트만 쓰므로, 적용되는 것은 **에셋별 라이선스**다.
둘을 혼동하지 않는다.

## Phase 1 subset 이 고른 것

전체 88,114장 중 **51장(17 asset × idle/walk/run)** 만 ingest 했다.
선택은 LPC metadata 기반으로 결정적이며, 기준과 결과는
[00_DOCS/lpc-phase1-subset.md](../lpc-phase1-subset.md) 에 있다.

**share-alike asset 을 의도적으로 배제했다.** 선택 필터가 CC0 / OGA-BY / CC-BY 를
제공하는 asset 만 통과시킨다. 그 결과:

| 선택된 라이선스 | 항목 수 |
|---|---:|
| `OGA-BY 3.0` | 15 |
| `CC0` | 4 |
| `OGA-BY 3.0+` | 1 |
| `CC-BY 3.0` | 1 |

- 고유 저자 **16명**, 고유 source URL **28개**
- `share_alike_required` 항목: **0**
- 상위 저장소 전체 기준으로는 14.7% 가 share-alike 전용이며, 그것들은 이 subset 에
  들어오지 않았다.

## 허용 / 금지

- [x] 게임 내 상업적 사용 — OGA-BY / CC-BY / CC0 전부 허용
- [x] 수정 (파츠 조합 / 리사이즈)
- [x] 재배포
- [x] **저자 표기 필요** — CC0 항목을 제외한 전 항목
- [ ] AI 학습: 라이선스 원문에 언급 없음 → `unknown`. 명시적 허용이 아니므로
      이 저장소에서는 금지로 취급한다. (파이프라인은 deterministic 합성만 하므로
      외부 모델로 나가는 경로 자체가 없다)

## attribution 추적

이 팩은 팩 단위 라이선스 한 줄로 요약되지 않는다. 그래서 파이프라인이
**파일 단위 provenance** 를 생성물까지 실어 나른다:

```
CREDITS.csv / sheet_definitions
   -> 02_CATALOG/lpc_ulpc-generator_phase1.json  (parts[].credits)
   -> 05_GENERATED/.../generation.json           (attribution 블록)
   -> 05_GENERATED/reports/lpc_phase1_attribution.md
   -> 06_UNITY_EXPORT/.../manifest.json
```

각 항목은 `source_file` / `authors` / `selected_license` /
`alternative_licenses` / `source_urls` / `attribution_required` /
`share_alike_required` 를 보존한다.

다중 라이선스 asset 은 **CC0 > OGA-BY > CC-BY** 순으로 하나를 명시적으로 선택하고,
고르지 못한 asset 은 subset 에서 제외한다. 선택하지 않은 대안도 함께 기록해
나중에 정책을 바꿀 수 있게 한다.

## 메모

- 이 팩은 **`compose.py` 의 modular composition abstraction 을 n=2 로 검증**하기 위해
  넣었다. CC0 팩(프레임 하나 = 파일 하나)과 달리 PNG 하나가 (방향 × 프레임) 시트다.
- 셀 크기 64x64 는 팩 상수로 adapter 에 선언했다. 자동 격자 검출을 하지 않는다.
- Phase 1 은 male body type / idle·walk·run / 단일 레이어 아이템만 쓴다.
  weapon·hat·shield·multi-layer·oversize·custom animation 은 제외했다.
