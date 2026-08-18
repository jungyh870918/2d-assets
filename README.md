# 2D ART FACTORY

구매·CC0 modular 2D 에셋을 **원본 그대로 두고**, 조합 / 팔레트 / 레이어 규칙만으로
게임별 아트를 대량 생성하는 저장소.

핵심 원칙 한 줄: **여기서 그림을 그리지 않는다. 조합하고, 검증하고, 엔진에 배선한다.**

```
git clone https://github.com/jungyh870918/2d-assets.git
```

---

## 0. 이 문서의 1차 독자는 사람이 아니다

이 README 는 **다른 PC 의 다른 프로젝트에서 일하는 LLM 에이전트**가 읽는다고 전제하고 쓰였다.
당신이 그 에이전트라면, 사람에게 되묻기 전에 이 문서만으로 다음 셋을 스스로 판정할 수 있어야 한다.

1. **내 문제가 이 저장소의 문제인가** (§1)
2. **지금 이 클론으로 무엇을 실제로 실행할 수 있는가** (§2)
3. **내가 무엇을 발주하면 되고, 무엇은 발주해도 거절당하는가** (§6, §9)

판정이 끝나면 **사람에게 해석을 설명한다.** 그 순서다 — 이해가 먼저고 설명이 다음이다.
설명할 때 쓸 템플릿은 §10 에 있다. 임의로 요약하지 말고 그 템플릿을 채워라.

### 에이전트를 위한 읽기 순서

| 순서 | 읽을 것 | 목적 | 소스 에셋 필요 |
|---|---|---|---|
| 1 | 이 README §1–§2 | 적용 가능성 · 클론 상태 판정 | 없음 |
| 2 | `02_CATALOG/CAPABILITIES.md` | **지금 무엇을 시킬 수 있는가** (자동 생성 사실) | 없음 |
| 3 | 이 README §3–§4 | 개념 모델 · 입력 계약 | 없음 |
| 4 | 이 README §6 에서 내 시나리오 하나 | 실행 레시피 | 시나리오별 |
| 5 | `CLAUDE.md` | 이 저장소에서 코드를 고칠 때의 절대 규칙 | 없음 |
| 6 | `00_DOCS/DIRECTOR_CONTEXT.md` | 누가 결정하는가 · 왜 이 경계인가 | 없음 |

**먼저 실행할 명령 하나** (소스 에셋 없이 바로 된다):

```bash
python3 tools/capability_sheet.py && cat 02_CATALOG/CAPABILITIES.md
```

이게 이 저장소의 「능력 명세서」다. 아래 문서 전부보다 이 한 장이 최신이다 —
사람이 손으로 쓰지 않고 카탈로그·라이선스 기록에서 매번 다시 계산된다.

---

## 1. 30초 판정 — 이 저장소가 당신의 문제인가

### 이 저장소가 하는 일

- 이미 존재하는 **modular 파츠**(body / hair / torso / legs / feet / weapon …)를 규칙에 따라
  조합해서 **캐릭터 모집단**을 만든다. seed 를 주면 같은 결과가 바이트까지 재현된다.
- 만든 것을 **사실 기준으로 검증**한다 (치수 · 알파 · 중복 · 소스 불변 · 재현성 · 라이선스).
- **Unity 로 배선**한다 (Sprite Library / Sprite Resolver / AnimatorController / prefab 빌더 포함).
- 라이선스·출처를 산출물 끝까지 **전파**한다 (상업 출시 가능 여부가 manifest 에 실려 나간다).

### 이 저장소가 하지 않는 일

| 안 하는 것 | 이유 · 대신 |
|---|---|
| 그림을 새로 그리기 | 생성형 이미지 모델을 쓰지 않는다. 구매 에셋을 AI 입력으로 넣는 것은 §9 의 불변식 위반이다 |
| **어느 결과가 더 좋은지 판정** | 미적 판단은 사람이 한다. 그래서 `picks/` · `approved/` 폴더가 **일부러 없다** |
| 완성된 캐릭터 시트를 파츠로 분해 | `composed_sheet` 팩은 조합 불가. 스캔·기록만 된다 (§3.3) |
| 타일맵 / 레벨 / 배경 생성 | environment 팩은 스캔까지만. `generation_mode: unsupported` |
| 라이선스 판단을 대신해 주기 | 라이선스 기록이 없으면 생성 자체를 **거부**한다 (§9) |
| 게임의 아트 정책을 정하기 | Factory 는 능력을 주고, 게임이 그중 무엇을 쓸지 정한다 (§8) |

### 판정표 — 당신의 상황에 맞는 줄을 찾아라

| 당신의 상황 | 판정 | 가야 할 곳 |
|---|---|---|
| 파츠가 슬롯별 개별 PNG 로 분리돼 있고 같은 원점·같은 캔버스다 | **✅ 정확히 여기다** | §6-B → §6-A |
| 이미 이 저장소가 카탈로그를 가진 팩(LPC / CC0)을 쓰고 싶다 | **✅ 바로 가능** | §6-A |
| Unity 게임에 NPC 20명을 결정적으로 세우고 싶다 | **✅ 가능** | §6-C, §8 |
| 완성 캐릭터 시트(walk.png 한 장에 전부)만 갖고 있다 | **⚠️ 조합 불가** | §6-D |
| 배경 타일셋 / 인테리어 팩이다 | **⚠️ 스캔만** | §6-D |
| 캐릭터 컨셉·주인공·보스·UI 언어를 만들고 싶다 | **❌ 여기가 아니다** | §11 art-studio |
| "AI 로 스프라이트를 생성해 줘" | **❌ 거절된다** | §9 |
| 어느 조합이 제일 예쁜지 골라 줘 | **❌ 이 저장소는 고르지 않는다** | §10 사람에게 |

> **핵심 구분선**: 이 저장소는 **모집단**(주민 · 잡몹 · 병사 · 색 변형)을 담당하고,
> **정체성**(주인공 · 보스 · 랜드마크 · UI)은 담당하지 않는다.
> 구매 팩 파츠를 그대로 게임에 실으면 그 게임의 아트 방향을 **팩 제작자가 정한 것**이 된다.
> 프로토타입 · 플레이스홀더 · 기계 검증까지가 안전한 사용 범위다.

---

## 2. 클론하면 무엇을 받는가 — 그리고 무엇을 받지 **못**하는가

**이것을 먼저 이해하지 못하면 다음 판단이 전부 틀린다.**

이 저장소는 **기계**를 배포하고 **재료**를 배포하지 않는다.

```
받는다 ✅                          받지 못한다 ❌ (.gitignore)
────────────────────────────       ────────────────────────────
tools/          파이프라인 전체     01_SOURCE/**    원본 아트 (라이선스·용량)
00_DOCS/        계약 · 라이선스 기록  05_GENERATED/** 생성물 (재생성 가능)
02_CATALOG/     팩 카탈로그 + 요약   06_UNITY_EXPORT/** 내보낸 패키지 (재생성 가능)
03_PALETTES/    팔레트 정의
04_RULES/       생성 규칙
CLAUDE.md       작업 지침
```

### 왜 이 설계가 당신에게 유리한가

`02_CATALOG/*.json` 은 **커밋되어 있다.** 카탈로그는 아트가 아니라 **파일명 · 치수 · sha256 ·
추론 결과의 목록**이라 재배포 제한에 걸리지 않는다. 그래서 에이전트는

- **에셋을 하나도 갖지 않은 상태에서** 이 팩으로 무엇이 가능한지 전부 읽을 수 있고,
- 나중에 같은 팩을 직접 받았을 때 **바이트 단위로 같은 팩인지 증명**할 수 있다.

```bash
# 소스 없이 즉시 실행됨 — 능력 명세서 재생성
python3 tools/capability_sheet.py

# 카탈로그가 요구하는 소스 파일 목록과 해시 (내 사본과 대조용)
python3 -c "
import json
c = json.load(open('02_CATALOG/lpc_ulpc-generator_phase1.json'))
print('pack root:', c['pack']['root'])
for e in c['entries'][:5]:
    print(e['sha256'][:12], e['bytes'], e['path'])
print('... 총', len(c['entries']), '개')
"
```

### 소스 없이 실행하면 어떻게 되는가

조용히 잘못된 결과를 내지 않는다. 정확한 파일을 지목하고 멈춘다.

```
ap2d.compose.ComposeError: 소스 에셋이 없다:
  01_SOURCE/characters/lpc_ulpc-generator_phase1/spritesheets/body/bodies/male/walk.png
```

| 명령 | 소스 없는 클론에서 |
|---|---|
| `tools/capability_sheet.py` | ✅ 된다 |
| `tools/tests/test_pipeline.py` | ⚠️ 부분 — 대부분 자체 픽스처로 돌지만 실소스가 필요한 8개는 fail/error 하고 38개는 skip 된다 (§13) |
| `tools/scan_pack.py` | ❌ 스캔 대상이 없다 |
| `tools/run_pipeline.py` | ❌ `ComposeError: 소스 에셋이 없다` |
| `tools/source_fingerprint.py` | ❌ `01_SOURCE` 가 없다 |

### 그래서 당신이 재료를 얻는 방법은 셋뿐이다

1. **카탈로그에 있는 팩을 직접 받는다** — 출처 URL 은 `00_DOCS/licenses/<pack>.md` 의
   `source_url` 에 있다. 받아서 `01_SOURCE/<domain>/<pack>/` 에 그대로 푼다.
2. **당신 팩을 새로 넣는다** — §6-B.
3. **직접 만든 파츠를 넣는다** — 입력 계약(§4)만 지키면 출처가 어디든 같은 코드가 돈다.

---

## 3. 개념 모델 — 이 기계가 세상을 보는 방식

에이전트가 이 넷을 알면 리포트의 거의 모든 필드를 해석할 수 있다.

### 3.1 모든 능력은 3상태다 — `yes` / `no` / `unknown`

**`unknown` 을 `yes` 로 반올림하지 않는다.** "못 찾았다"와 "없다"는 다르다.

예: HD Survivor 팩은 방향 8개를 **시트의 행**에 담고 있어서 파일명만으로는 방향 축이
있는지조차 알 수 없다. 그래서 `direction_axis.present: unknown` 이고 `no` 가 아니다.

> 에이전트 규칙: 리포트에서 `unknown` 을 봤을 때 "없는 것"으로 요약하지 마라.
> **"증명되지 않았다"** 로 사람에게 전달해야 한다.

### 3.2 `composable` — 조합 가능성의 정의

```
composable = parts_separable ∧ pre_aligned ∧ animation_compatible
```

| capability | 뜻 |
|---|---|
| `parts_separable` | 파츠가 슬롯별로 분리된 파일/셀로 존재하는가 |
| `shared_canvas` / `shared_cell` | 겹칠 레이어들이 같은 캔버스 또는 같은 논리 셀인가 |
| `pre_aligned` | 좌표 보정 없이 그대로 겹쳐도 맞는가 |
| `shared_origin` | 원점이 같은가 |
| `animation_compatible` | 슬롯 간 애니메이션·프레임 수가 맞는가 |
| `directional` | 방향 축이 읽혔는가 |
| `origin_policy` | pivot 의 근거 (`shared_canvas` / `logical_cell` / `unknown`) |

이 값들은 스캐너가 **계산한 사실**이고 사람이 선언하는 값이 아니다.

### 3.3 `generation_mode` — 팩이 갈라지는 지점

| mode | 뜻 | 조합 | Unity 소비 경로 |
|---|---|---|---|
| `modular_composition` | 파츠를 골라 합성 | **가능** | Sprite Library (runtime) 또는 구운 시트 |
| `composed_sheet` | 이미 완성된 캐릭터 시트 | **불가** | Animator + 시트 슬라이싱 (게임 쪽에서) |
| `unsupported` | 캐릭터 생성 대상 아님 (타일셋 등) | 불가 | — |

조합 불가 팩을 생성기에 넣으면 곁가지 오류가 아니라 **명시적 SKIP** 으로 즉시 멈춘다:

```python
from ap2d import catalog, generate
generate.generation_status(catalog.load_catalog("02_CATALOG/<pack>.json"))
# -> {"status": "skipped", "generation_mode": "composed_sheet",
#     "reason": "composed_sheets_only", "capabilities": {...}}
```

**이건 실패가 아니다.** 사람에게 "실패했다"고 보고하지 마라 — "이 팩은 애초에 조합 대상이
아니고, 근거는 `reason` 이다"로 보고해야 한다.

### 3.4 물리 배치 ≠ 논리 좌표

서로 완전히 다르게 저장된 두 팩이 같은 파이프라인을 탄다:

| | CC0 (벡터 만화풍) | LPC (64px 도트) |
|---|---|---|
| 물리 단위 | PNG 1장 = 프레임 1개 | PNG 1장 = (방향 × 프레임) 시트 |
| 좌표 | `(slot, asset, animation, frame)` | `(slot, asset, animation, direction, frame)` |
| resolve | 파일 열어 애니메이션 bbox 로 crop | 시트 열어 논리 셀로 crop |

`compose.resolve_layer()` 가 이 차이를 흡수하는 **유일한 지점**이고, 그 뒤 합성 루프는
두 팩이 같은 코드를 탄다. 이게 "출처가 어디든 계약만 지키면 된다"의 근거다.

---

## 4. 입력 계약 — 당신의 에셋이 여기 들어올 수 있는가

에이전트가 **새 팩 / 외주 파츠 / 직접 만든 파츠**를 평가할 때 쓰는 체크리스트다.
아래를 만족하면 팩의 화풍·출처와 무관하게 같은 파이프라인이 돈다.

| # | 요구 | 어기면 |
|---|---|---|
| 1 | 슬롯마다 **별도 PNG** (또는 규칙적인 시트 셀) | `composed_sheet` 로 떨어져 조합 불가 |
| 2 | 겹칠 파츠가 **같은 논리 셀 · 같은 원점** | `pre_aligned: unknown` → `composable: no` |
| 3 | 애니메이션 이름과 프레임 수가 슬롯 간 **일치** | `animation_compatible` 하락 (부분 허용 시 `allow_subset` 선언) |
| 4 | **z 순서를 소스가 선언** (또는 규칙에 명시) | 사람이 베껴 적다 어긋난다 |
| 5 | 색이 **램프 구조**를 따름 | 팔레트 교체 품질이 보장되지 않음 |
| 6 | `00_DOCS/licenses/<pack>.md` 의 **frontmatter 존재** | 생성기 진입 자체가 차단됨 |

라이선스 frontmatter 필수 필드 (`tools/ap2d/licensing.py` 의 `REQUIRED_FIELDS`):

```markdown
---
pack: <01_SOURCE 아래 팩 폴더명과 동일>
license: CC0-1.0
commercial_use: yes        # yes / no / unknown
modification: yes          # no 면 조합 자체가 라이선스 위반
redistribution: yes
ai_training: yes
pipeline_approved: yes     # yes 가 아니면 생성기가 진입을 거부한다
acquired: 2026-08-16
source_url: https://...
---
```

라이선스 상태가 파이프라인에 미치는 영향:

| 상태 | scan | generate | export | 상업 출시 |
|---|---|---|---|---|
| `pipeline_approved: yes` + `commercial_use: yes` | ○ | ○ | ○ | ○ |
| `pipeline_approved: yes` + `commercial_use: no` | ○ | ○ | ○ | **×** |
| `pipeline_approved: no` / `modification: no` / 기록 없음 | ○ | **차단** | — | × |

`commercial_use: no` 는 생성을 막는 hard gate 가 **아니다.** 대신
`commercial_release_eligible: false` 가 계산되어 catalog summary → generation.json →
Unity manifest → validation report 까지 **전부 따라 나가고** 리포트에 경고 배너가 붙는다.

---

## 5. 파이프라인 6단계와 산출물

```
01_SOURCE  ──(scan)──>  02_CATALOG  ──>  CAPABILITIES.md   "무엇을 시킬 수 있나"
                            │
        03_PALETTES + 04_RULES
                            │
                        (generate)          seed 결정적
                            ↓
                       05_GENERATED  ──>  <profile>_brief.md   "무엇을 했나"
                            │
                        (validate)
                            ↓
                      06_UNITY_EXPORT
                            │
                    (export_consumer_package)
                            ↓
                    별도 Unity 게임 프로젝트
```

한 번에:

```bash
python3 tools/run_pipeline.py 04_RULES/<규칙>.json
```

단계별:

| 명령 | 하는 일 | 출력 |
|---|---|---|
| `tools/scan_pack.py <팩 폴더>` | 소스 스캔 + 추론 | `02_CATALOG/<pack>.json`, `.summary.md` |
| `tools/capability_sheet.py` | 팩·팔레트·규칙 능력을 한 장으로 | `02_CATALOG/CAPABILITIES.md` |
| `tools/generate_characters.py <규칙>` | seed 조합 + 합성 | `05_GENERATED/characters/<profile>/<seed>/` |
| `tools/make_contact_sheet.py <profile>` | 한 장에 모아 보기 | `05_GENERATED/reports/<profile>.png` |
| `tools/validate_generated.py <규칙>` | 검사 10종 + 분포 관측 | `..._validation.{json,md}` · `..._attribution.md` |
| `tools/order_brief.py <규칙>` | 회신 한 장 | `..._brief.{json,md}` |
| `tools/export_unity.py <규칙>` | Unity 패키지 (baked) | `06_UNITY_EXPORT/characters/<profile>/` |
| `tools/export_unity_runtime.py <규칙>` | Unity 패키지 (Sprite Library) | `06_UNITY_EXPORT/runtime/<profile>/` |
| `tools/export_consumer_package.py <Assets 경로> --profiles <p>` | 외부 Unity 프로젝트로 복사 | 소비자 `Assets/ArtFactory/` |
| `tools/tests/test_pipeline.py` | 자동 테스트 전량 | 200 tests |
| `tools/source_fingerprint.py` | 소스 변조 확인 | 트리 sha256 |

`run_pipeline.py` 는 scan → generate → contact sheet → export → validate → brief
순서로 돌고, 마지막에 `CAPABILITIES.md` 를 다시 만든다.
**검증이 실패해도 회신(brief)은 쓴다** — 무엇이 왜 안 됐는지가 회신의 ⑥ 이다.

---

## 6. 시나리오별 실행 레시피

### A. 나는 게임 프로젝트의 에이전트다 — NPC 모집단이 필요하다

```bash
# 1. 무엇이 가능한지 읽는다 (소스 없어도 됨)
python3 tools/capability_sheet.py && cat 02_CATALOG/CAPABILITIES.md

# 2. composable: yes 인 팩을 고르고, 그 팩의 소스를 받아 01_SOURCE 에 푼다
#    출처 URL 은 00_DOCS/licenses/<pack>.md 의 source_url

# 3. 기존 규칙을 복사해 내 규칙을 만든다
cp 04_RULES/lpc_phase1_population.json 04_RULES/mygame_villagers.json
#    최소한 이 다섯을 바꾼다: id · profile · seeds · slots 의 allow/deny · order 블록

# 4. 돌린다
python3 tools/run_pipeline.py 04_RULES/mygame_villagers.json

# 5. 회신 한 장을 읽고 사람에게 §10 템플릿으로 보고한다
cat 05_GENERATED/reports/mygame_villagers_brief.md
```

규칙 파일에서 에이전트가 실제로 만지는 필드:

```jsonc
{
  "schema": "ap2d.rule/1",
  "id": "mygame_villagers",
  "profile": "mygame_villagers",          // 산출물 폴더 이름이 된다
  "pack": "lpc_ulpc-generator_phase1",
  "catalog": "02_CATALOG/lpc_ulpc-generator_phase1.json",

  "order": {                               // 표시용 라벨. 아무것도 막지 않는다
    "purpose": "order_response",           // self_verification | order_response
    "consumer": "unknown",                 // ← 지어내지 마라. 발급받지 못했으면 unknown
    "request": "요구 원문 또는 요약",
    "not_done": [{"요구": "...", "근거": "..."}]
  },

  "animations": ["idle", "walk", "run"],
  "directions": ["south", "west", "east", "north"],
  "slots": {
    "body":  { "required": true,  "from": "body" },
    "hair":  { "required": false, "from": "hair", "none_weight": 0.2,
               "deny": ["hair_braid"] }    // allow / deny 로 후보를 좁힌다
  },
  "layer_order": "by_z_pos",               // 소스가 z 를 선언하면 베껴 적지 않는다
  "unity": { "pixels_per_unit": 64, "filter_mode": "Point", "pivot": "BottomCenter",
             "frame_rate": 8 },
  "archetypes": [
    { "name": "villager", "seeds": { "from": 4001, "to": 4010 } }
  ],
  "global": { "no_duplicate_combinations": true, "deterministic": true }
}
```

> **`order.consumer` 를 지어내지 마라.** 게임 저장소 디렉터리 이름이나 축약형을
> 소비자 식별자로 승격시키면 한 게임에 이름이 셋이 된다. 발급받지 못했으면
> `unknown` 이 **정당한 값**이다.

### B. 새 팩을 넣고 싶다

```bash
# 1. 원본 그대로 푼다 (수정 금지)
#    01_SOURCE/<domain>/<vendor>_<pack>_<version>/    + SOURCE.md
# 2. 라이선스 기록 작성 — frontmatter 필수 (§4)
#    00_DOCS/licenses/<pack>.md
# 3. 스캔
python3 tools/scan_pack.py 01_SOURCE/characters/<pack>
# 4. summary 의 "generation capability" 표를 **먼저** 본다
cat 02_CATALOG/<pack>.summary.md
#    composable: no 면 여기서 멈춘다 — 규칙을 쓸 필요가 없고 reason 이 이유를 말한다
# 5. summary 의 "발견된 파츠" 표를 보고 규칙을 쓴다 → §6-A 3번으로
```

스캐너가 파츠를 못 알아보면 `tools/ap2d/catalog.py` 의 `BODY_PART_VOCAB` 에 **단어만**
추가한다. 어휘에 없는 것은 `unknown` 으로 남고 summary 의 anomaly 절에 보고되므로,
**조용히 잘못 조합되는 일은 없다.**

팩이 권위 metadata 를 직접 제공하는 경우(LPC 의 `sheet_definitions` 등)에만 adapter 를 쓴다:

```bash
python3 tools/scan_pack.py 01_SOURCE/characters/<pack> --adapter lpc
```

**pack-specific 지식은 `tools/ap2d/packs/` 안에만 둔다.** generic 모듈에
`if "lpc" in pack_name` 같은 분기를 넣으면 **AST 테스트가 실패한다.**

### C. Unity 게임에 붙이고 싶다

```bash
# Factory 쪽
python3 tools/export_unity_runtime.py 04_RULES/<규칙>.json --seeds 4101 4102 --cell-size 64
python3 tools/export_consumer_package.py /path/to/MyGame/Assets --profiles <profile>
```

그 다음은 **소비자 Unity 프로젝트 안에서** 에디터 빌더가 한다
(`SpriteLibraryBuilder` → 라이브러리 · prefab · `CharacterProfile`,
`AnimationClipBuilder` → clip · controller). 게임 코드가 아는 타입은 셋뿐이다 — §8.

```csharp
profile.SetMotion(animator, "walk");   // 게임 코드의 유일한 진입점
profile.HasAnimation("run");
```

### D. 내 팩이 `composable: no` 다

정상이다. 실패가 아니다. 선택지는 셋이다.

| 상황 (`reason`) | 뜻 | 할 수 있는 것 |
|---|---|---|
| `composed_sheets_only` | 완성 시트만 있다 | 조합은 포기. Unity 에서 시트를 직접 슬라이싱해 Animator 로 쓴다. 카탈로그는 그래도 유용하다 (애니메이션·프레임·치수 목록) |
| `atlas_only_no_individual_props` | 아틀라스만 있고 파츠가 분리 안 됨 | 타일맵/환경 용도로만. 캐릭터 생성 대상 아님 |
| `pre_aligned: unknown` | 정렬이 증명 안 됨 | 소스 제작자에게 §4 계약대로 재요청하거나, 직접 파츠를 분리해 별도 계층에 둔다 |

**하지 말 것**: 조합을 억지로 통과시키려고 `compose.py` 에 예외를 넣는 것.
`compose.require_modular()` 가 `UnsupportedModeError` 로 막는 것은 버그가 아니라 설계다.

### E. 결과가 마음에 들지 않는다

이 저장소에는 "더 좋게" 하는 손잡이가 없다. 검증은 **사실만** 본다.
당신이 조정할 수 있는 것은 **입력**뿐이다:

| 증상 (리포트 「관측된 분포」에서 읽는다) | 손댈 곳 |
|---|---|
| 10명이 사실상 한 명처럼 보인다 | 슬롯의 `사용됨` 수를 본다 → `deny` 를 줄이거나 팩 subset 을 넓힌다 |
| 특정 파츠만 계속 나온다 (`최빈 비율` 높음) | `none_weight` · `allow` 조정, seed 범위 확대 |
| 색이 다 비슷하다 | 팔레트 규칙 추가 (`03_PALETTES/`). 단 현재 엔진은 multiply tint 다 |
| 화풍이 게임과 안 맞는다 | **파이프라인 문제가 아니다.** 팩 교체 또는 §11 art-studio 의 문제다 |

**검증에 미적 기준을 추가하지 마라.** 톤 거리·색 분포로 합격선을 만들면
좋은 결과가 숫자 때문에 버려진다.

### F. 무엇이 바뀌었는지 확인하고 싶다 (회귀 점검)

```bash
python3 tools/source_fingerprint.py     # 소스가 변조됐는가
python3 tools/tests/test_pipeline.py    # 200 tests
python3 tools/run_unity_tests.py        # Unity EditMode + PlayMode (Unity 필요)
```

같은 seed · 같은 규칙 · 같은 카탈로그면 결과는 **바이트까지 같아야 한다.**
다르면 그 자체가 버그 신호다.

---

## 7. 산출물 읽는 법 — 어떤 질문에 어떤 파일

에이전트는 PNG 를 보지 말고 **JSON 을 파싱하라.** 모든 `.md` 는 같은 사실의 사람용 표현이다.

| 알고 싶은 것 | 읽을 파일 | 기계 판독 |
|---|---|---|
| 지금 무엇을 시킬 수 있나 | `02_CATALOG/CAPABILITIES.md` | 팩별 `.json` 의 `pack.capabilities` |
| 이 팩에 뭐가 들어 있나 | `02_CATALOG/<pack>.summary.md` | `02_CATALOG/<pack>.json` (`entries[]`, `parts{}`) |
| 이번 발주에 무엇을 했나 | `05_GENERATED/reports/<profile>_brief.md` | `..._brief.json` |
| 통과했나 | `..._validation.md` | `..._validation.json` (`checks[]`, `status`) |
| 출처를 어떻게 표기하나 | `..._attribution.md` | `character.json` 옆의 `sources.json` |
| 이 캐릭터는 무엇으로 만들어졌나 | — | `05_GENERATED/characters/<profile>/<seed>/character.json` |
| 재현 좌표 (승인 대상) | brief 의 ② | `generation.json` (`rule_sha256` · `catalog_sha256` · `seed`) |
| Unity 가 소비할 것 | — | `06_UNITY_EXPORT/runtime/<profile>/runtime_manifest.json` |

스키마 식별자: `ap2d.rule/1` · `ap2d.character/1` · `ap2d.unity_runtime/1`

### 회신(brief) 여섯 절의 뜻

| 절 | 내용 | 에이전트가 주의할 것 |
|---|---|---|
| ① 무엇을 요청받았나 | 성격 · 소비자 · 프로파일 · 팩 | `self_verification` 이면 발주 대응이 아니다 |
| ② 재현 좌표 | 규칙/카탈로그 sha256 · seed · 팔레트 | **승인은 PNG 가 아니라 여기에 건다** |
| ③ 기술 검증 | 10종 검사 결과 | **PASS = 파이프라인 정합성. 채택도 출시 허가도 아니다** |
| ④ 출시 신호 | `commercial_release_eligible` · 표기 필요 여부 | `false` 면 상업 출시 불가를 **명시적으로** 보고하라 |
| ⑤ 관측된 분포 | 후보 중 몇 개가 실제로 나왔나 | **검사가 아니다.** 임계값도 등급도 없다 |
| ⑥ 못 한 것 · 거절한 것 | 근거와 함께 | 비어 있으면 정말로 없는 것이다 |

### 검증 10종 (전부 사실 검사, 미적 판단 없음)

생성 개수 일치 · `01_SOURCE` 원본 불변(hash 대조) · 카탈로그에 없는 asset 참조 금지 ·
소스 asset 존재 · 생성물 파일 존재 · 이미지 치수 일치 · 알파 채널 유효 ·
중복 조합 없음 · 라이선스 제한 전파 · 동일 seed 재생성 결과 일치.

---

## 8. Unity 소비자 경계 (Export Contract v1)

### 게임이 아는 타입은 셋뿐

`CharacterProfile` · `CharacterAppearance` · `CharacterView`.
라벨 규약 · `SpriteResolver` category · 슬롯 z-order · 시트 셀 좌표 · 소스 경로는
**게임이 알 필요가 없고, 알면 안 된다.**

### 소유권 경계 — exporter 는 자기 것만 건드린다

| 소유자 | 경로 | exporter |
|---|---|---|
| Factory | `<pkg>/Runtime/`, `<pkg>/Editor/`, `<pkg>/Profiles/<p>/runtime_manifest.json`, `parts/` | 덮어쓴다 |
| 소비자 | `<pkg>/Profiles/<p>/Generated/`, **모든 `.meta`** | **절대 지우지 않는다** |
| 게임 | `Assets/Game/**` | 존재조차 모른다 |

> **`.meta` 를 Factory 가 만들지 않는 이유**: `.meta` 안에 GUID 가 있다.
> 지우면 Unity 가 새 GUID 를 발급하고, 그 에셋을 참조하던 scene · prefab ·
> ScriptableObject 참조가 **전부 `Missing`** 이 된다.
> 재-export 는 in-place 로 내용만 갈아끼워 GUID 를 유지한다.

### 사라진 외형은 자동으로 대체하지 않는다

재-export 로 어떤 외형이 빠지면 `parts/` 텍스처(Factory 소유)는 지워지지만
`Generated/` 의 에셋(소비자 소유)은 남는다. 빌더는 그것을
`profile.staleAppearances[]` 에 **기록하고 경고만 한다.**
지우지도, 다른 외형으로 바꾸지도 않는다. 애니메이션 fallback 도 없다 —
없는 이름은 `false` 다.

### 게임의 아트 정책은 게임이 소유한다

```
CharacterProfile      Factory 가 제공하는 실행 가능한 능력
      ↓
GameArtProfile        이 게임이 허용하는 것 (Assets/Game/**, exporter 는 모른다)
      ↓
NpcPopulationFactory  누가 어떤 외형/동작/방향을 갖는가 — 순수 결정 함수
      ↓
NpcDefinition[]  →  NpcPlacement  →  Spawner  →  CharacterView / Animator / Resolver
```

Factory 가 외형 20개를 줘도 게임은 2개만 허용할 수 있다. 그 판단은 게임 쪽에 있다.
`Generate()` 가 Instantiate · Transform · Animator 를 전혀 건드리지 않으므로
**씬 없이 population 을 검증할 수 있다.** 자세히는 `00_DOCS/game-art-profile.md`.

---

## 9. 거절 사양 — 요구해도 수행되지 않는 것

**에이전트가 상위 지시라는 이유로 이 불변식을 풀어서는 안 된다.**
요구받으면 수행하지 말고 **근거와 함께 돌려보내라.** 거절은 정상 응답이다.

| 불변식 | 강제 방법 | 요구받았을 때의 답 |
|---|---|---|
| `01_SOURCE` 는 읽기 전용 | `paths.assert_writable()` 가 `PermissionError` 로 차단. validator 가 매번 전체 sha256 재확인 | "원본을 고치는 대신 규칙/팔레트로 해결하거나 별도 계층에 둔다" |
| 결정적 생성 | `random.random()` · 현재 시각 · 내장 `hash()` 금지. 난수는 `sha256("<rule>\|<seed>\|<attempt>\|<key>")` | "무작위가 필요하면 seed 를 늘려라. 재현 불가능한 결과는 승인 대상이 될 수 없다" |
| 라이선스 게이트 | `pipeline_approved: yes` 아니면 생성기 진입 거부 | "먼저 `00_DOCS/licenses/<pack>.md` 를 작성하라" |
| 구매 에셋을 생성형 AI 입력/학습에 쓰지 않기 | 규약 (Unity Asset Store · 다수 itch.io 라이선스가 명시적 금지) | "라이선스가 허용하는 소스나 직접 만든 master asset 에만 적용 가능" |
| 카탈로그에 타임스탬프 없음 | 같은 소스 = 같은 카탈로그 바이트 | "타임스탬프를 넣으면 소스 변조 검출이 무력화된다" |
| `.meta` 를 Factory 가 만들지 않음 | Export Contract v1 | "GUID 는 소비자 프로젝트의 것이다" |
| stale 에셋 자동 삭제 안 함 | 빌더가 기록만 | "게임이 아직 참조 중일 수 있다. 사람이 결정한다" |
| 애니메이션 fallback 없음 | `SetMotion` 이 `false` 반환 | "없는 이름을 다른 애니메이션으로 조용히 대체하지 않는다" |
| 검증에 미적 기준 없음 | validator 는 사실만 | "좋고 나쁨은 사람이 정한다. 이 저장소에 `picks/` 가 없는 이유다" |
| `unknown` 을 `yes` 로 반올림 안 함 | 3상태 유지 | "증명되지 않은 것을 증명된 것으로 만들지 않는다" |
| `order.consumer` 를 지어내지 않음 | — | "발급받지 못했으면 `unknown` 이 정당한 값이다" |

또한 **문서와 구현이 어긋나면 같은 변경 안에서 함께 고친다.**
이 문서들은 다음 세션이 처음 읽는 것이라, 틀린 설명은 그 위에 쌓이는 작업을 전부 틀리게 만든다.

---

## 10. 사람에게 보고할 때 — 에이전트용 템플릿

판정이 끝났으면 **사람에게 당신의 해석을 설명한다.** 아래를 채워라.
빈칸을 추측으로 메우지 말고 `unknown` 으로 남겨라.

```markdown
### 2D Art Factory 적용 판정

**결론**: 이 저장소는 우리 문제의 [전부 / 일부 / 해당 없음] 을 담당한다.

**우리가 시킬 수 있는 것**
- (CAPABILITIES.md 에서 composable: yes 인 팩과 슬롯 수 · 조합 상한 인용)

**우리가 시킬 수 없는 것**
- (composable: no 인 팩과 그 reason, 또는 §1 의 "하지 않는 일" 중 해당 항목)

**지금 막혀 있는 것**
- 소스 에셋: [보유 / 미보유 — 출처 URL 은 00_DOCS/licenses/<pack>.md]
- 라이선스 기록: [있음 / 없음 — 없으면 생성 자체가 차단됨]
- 상업 출시: [가능 / 불가 — commercial_release_eligible 값 인용]

**내가 제안하는 다음 한 걸음**
- (§6 의 시나리오 하나를 지목하고, 실행할 명령을 그대로 적는다)

**사람이 결정해야 하는 것** (이 저장소는 판정하지 않는다)
- 어느 조합을 채택할지 — contact sheet: 05_GENERATED/reports/<profile>.png
- 이 화풍이 게임 아트 방향과 맞는지
- (분포 관측 결과가 있으면 인용하되, 좋다/나쁘다고 말하지 말 것)
```

> **보고할 때 하지 말 것**
> - 검증 PASS 를 "채택 승인"으로 옮겨 적기 (③ 은 파이프라인 정합성일 뿐이다)
> - `unknown` 을 "없음"으로 요약하기
> - `composable: no` 를 "실패"로 보고하기 (명시적 SKIP 이다)
> - 관측된 분포에 임의의 합격선을 붙이기

---

## 11. 함께 쓰는 저장소

| 저장소 | 역할 | 공개 |
|---|---|---|
| **[2d-assets](https://github.com/jungyh870918/2d-assets)** (여기) | **증폭** — 조합 · 팔레트 · 검증 · 엔진 배선 | 공개 |
| [art-studio](https://github.com/jungyh870918/art-studio) | **결정과 기억** — 아트 방향 · 승인 · 기록. 이 저장소를 에셋 팩토리로 쓰는 상위 계층 | 공개 |
| [game-sandbox](https://github.com/jungyh870918/game-sandbox) | 소비자 쪽 경계를 실측하는 별도 Unity 프로젝트 (Factory 저장소 없이도 열리고 돈다) | 비공개 |

```
art-studio/     결정 — 무엇을 만들 것인가 · 무엇을 채택하는가
     │  발주 (CAPABILITIES.md 를 읽고)
     ▼
2d-assets/      증폭 — 조합 · 검증 · export        ← 여기
     │  회신 (<profile>_brief.md)
     ▼
게임 프로젝트     소비 — GameArtProfile 로 무엇을 쓸지 정한다
```

에셋 팩은 계속 추가되며, 추가될 때마다 `02_CATALOG/CAPABILITIES.md` 가 자동으로 갱신된다.
**팩 목록의 최신 사실은 이 README 가 아니라 그 파일에 있다.**

---

## 12. 자주 하는 오해

| 오해 | 사실 |
|---|---|
| "클론하면 에셋도 같이 온다" | 아니다. `01_SOURCE` 는 gitignore 다. 기계만 온다 (§2) |
| "검증 PASS 면 써도 된다" | 파이프라인 정합성만 통과한 것이다. 채택도 출시 허가도 아니다 |
| "`05_GENERATED` 를 손으로 고치면 된다" | 언제든 삭제·재생성 가능해야 한다. 손으로 고치는 순간 재현성이 죽는다 |
| "PNG 를 승인하면 된다" | 승인은 **팩 해시 + 규칙 파일 + seed** 에 건다. PNG 는 언제든 재생성된다 |
| "분포 리포트에 합격선이 있다" | 없다. 세기만 하고 판정하지 않는다 |
| "`unknown` 은 사실상 `no` 다" | 아니다. "증명되지 않았다"이며 나중에 `yes` 가 될 수 있다 |
| "새 팩마다 코드를 고쳐야 한다" | 대부분 어휘(`BODY_PART_VOCAB`)에 단어만 추가한다. adapter 는 팩이 권위 metadata 를 줄 때만 |
| "Factory 가 Unity prefab 을 만든다" | 아니다. manifest·시트·C# 을 주고, prefab·SpriteLibrary·clip 은 소비자 에디터 빌더가 만든다 |
| "이걸로 주인공을 만들 수 있다" | 모집단용이다. 정체성은 디렉팅 루프의 몫이다 (§1) |

---

## 13. 환경 · 검증

```
Python 3.9+ · Pillow    (그 외 의존성 없음)
Unity 쪽은 선택 — 소비자 프로젝트에서만 필요
```

```bash
python3 tools/tests/test_pipeline.py     # 소스 팩 보유 시: 200 tests 통과, 약 60초
python3 tools/source_fingerprint.py      # 01_SOURCE 트리 sha256
python3 tools/run_unity_tests.py         # EditMode + PlayMode (Unity 설치 필요)
```

**소스 팩이 없는 클론에서 테스트를 돌리면 전부 통과하지 않는다.** 실측값:

| 상태 | 결과 |
|---|---|
| 소스 팩 보유 | `Ran 200 tests ... OK` (약 57초) |
| 소스 없는 클론 | `Ran 193 tests ... FAILED (failures=2, errors=6, skipped=38)` (1초 미만) |

실패하는 8개는 전부 **실제 소스 파일 또는 이전 산출물을 요구하는 검사**다 —
`test_every_source_file_exists` · `test_rendered_images_are_byte_identical` ·
`test_catalog_build_is_deterministic` · `test_generated_outputs_preserve_direction` 등.
**코드가 깨진 것이 아니다.** 재료가 없는 것이고, §2 와 같은 이유다.
소스를 받아 `01_SOURCE` 에 놓으면 전량 통과해야 한다 — 그러지 않으면 그때가 진짜 회귀다.

Unity 기본 규격 (규칙이 지정하지 않을 때):

```
Pixels Per Unit   : 팩의 타일/셀 크기와 일치 (LPC = 64, LimeZu = 16)
Filter Mode       : Point (no filter)
Compression       : None
Pivot             : Bottom Center (캐릭터) / Center (프롭)
Sprite Mode       : Multiple (시트) / Single (개별 PNG)
Mesh Type         : Full Rect
```

---

## 14. 폴더 구조 · 문서 색인

```
00_DOCS/          라이선스 기록 · 계약 문서 · 결정 기록
01_SOURCE/        구매/다운로드 원본. 절대 수정 금지 (read-only, gitignored)
  _INBOX/         다운로드한 zip 임시 보관
02_CATALOG/       스캔 결과 (JSON) · 사람이 읽는 요약 · CAPABILITIES.md
03_PALETTES/      팔레트 정의 (램프 구조)
04_RULES/         생성 규칙 (조합 제약 · 확률 · 금지 조합 · order 블록)
05_GENERATED/     정의 · PNG · 검증 리포트 · 발주 회신 (gitignored, 재생성 가능)
06_UNITY_EXPORT/  Unity 로 넘길 패키지 (baked / runtime 두 갈래, gitignored)
tools/            스캐너 · 생성기 · 검증 · 익스포터
  ap2d/           파이프라인 라이브러리 (팩 이름을 모른다)
    packs/        팩별 adapter — pack-specific 지식은 여기에만
  unity/          소비자 프로젝트로 복사되는 C#
```

| 문서 | 무엇 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 이 저장소에서 작업할 때의 지침 · 절대 규칙 |
| [tools/README.md](tools/README.md) | 명령 전체 · 모듈 구조 · 분류 어휘 · capability 계산 상세 |
| [02_CATALOG/CAPABILITIES.md](02_CATALOG/CAPABILITIES.md) | **자동 생성 — 지금 무엇을 시킬 수 있는가** |
| [00_DOCS/DIRECTOR_CONTEXT.md](00_DOCS/DIRECTOR_CONTEXT.md) | 누가 결정하는가 · 고정된 경계 · 발주 입출력 |
| [00_DOCS/export-contract-v1.md](00_DOCS/export-contract-v1.md) | Factory ↔ 소비자 소유권 경계 · GUID 안정성 · 실측 |
| [00_DOCS/game-art-profile.md](00_DOCS/game-art-profile.md) | 게임이 허용하는 것 · population 결정 경계 |
| [00_DOCS/unity-sprite-runtime.md](00_DOCS/unity-sprite-runtime.md) | Sprite Library / Resolver 런타임 |
| [00_DOCS/naming-convention.md](00_DOCS/naming-convention.md) | 팩 · 파일 네이밍 |
| [00_DOCS/licenses/](00_DOCS/licenses/) | 팩별 라이선스 기록 (생성 게이트의 입력) |

---

## 라이선스

이 저장소의 **코드와 문서**(`tools/` · `00_DOCS/` · `02_CATALOG/` · `03_PALETTES/` · `04_RULES/`)에
대한 것이다. **에셋 원본은 여기 포함되지 않으며**, 각 팩의 라이선스는 그 팩의 것이다 —
`00_DOCS/licenses/<pack>.md` 를 반드시 직접 확인하라.
생성물의 상업적 사용 가능 여부는 소스 팩 라이선스를 따르고,
`commercial_release_eligible` 로 계산되어 산출물까지 전파된다.
