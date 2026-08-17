# tools/

`01_SOURCE` → `02_CATALOG` → `05_GENERATED` → `06_UNITY_EXPORT` 파이프라인.
Python 3.9+ / Pillow 외에 의존성 없음.

## 한 번에 돌리기

```bash
python3 tools/run_pipeline.py 04_RULES/cc0_test_population.json
```

처음부터 완전히 다시 만들려면:

```bash
rm -rf 02_CATALOG/*.json 02_CATALOG/*.md 05_GENERATED/characters 05_GENERATED/reports 06_UNITY_EXPORT/characters
python3 tools/run_pipeline.py 04_RULES/cc0_test_population.json --rescan
```

## 단계별

| 명령 | 하는 일 | 출력 |
|---|---|---|
| `python3 tools/scan_pack.py <팩 폴더>` | 소스 스캔 + 추론 | `02_CATALOG/<pack>.json`, `.summary.md` |
| `python3 tools/capability_sheet.py` | 팩·팔레트·규칙의 가용 능력을 한 장으로 | `02_CATALOG/CAPABILITIES.md` |
| `python3 tools/generate_characters.py <규칙>` | seed 기반 조합 + 합성 | `05_GENERATED/characters/<profile>/<seed>/` |
| `python3 tools/make_contact_sheet.py <profile>` | 결과 한 장에 모으기 | `05_GENERATED/reports/<profile>.png` |
| `python3 tools/validate_generated.py <규칙>` | 10종 검사 + 분포 관측 | `05_GENERATED/reports/<profile>_validation.{json,md}` + `_attribution.md` |
| `python3 tools/order_brief.py <규칙>` | 회신 한 장 (재현 좌표·출시 신호·못 한 것) | `05_GENERATED/reports/<profile>_brief.{json,md}` |
| `python3 tools/export_unity.py <규칙>` | Unity 용 패키지 | `06_UNITY_EXPORT/characters/<profile>/` |
| `python3 tools/ingest_lpc_subset.py <LPC repo>` | LPC subset 결정적 선택 + ingest | `01_SOURCE/characters/lpc_...`, `00_DOCS/lpc-phase1-subset.md` |
| `python3 tools/tests/test_pipeline.py` | 자동 테스트 전량 (개수는 실행이 출력) | — |

발주를 받기 전에 읽는 것은 `02_CATALOG/CAPABILITIES.md` 하나다 — 팩마다 흩어진
슬롯 후보 수 · 애니메이션 · 방향 축 · 라이선스 3상태를 모아 둔다. 자동 생성이라
손으로 고치지 않는다.

`run_pipeline.py` 는 이 둘을 마지막 두 단계로 자동 실행한다.

environment 팩처럼 조합 가능한 `character_part` 가 없는 팩은 scan 까지만 돌린다.
generation 단계는 규칙을 쓸 소재가 없어서 애초에 성립하지 않는다:

```bash
python3 tools/scan_pack.py 01_SOURCE/environments/limezu_modern-interiors-free_v2.2
```

## 모듈

```
ap2d/
  paths.py         저장소 경로. 01_SOURCE 쓰기 시도를 PermissionError 로 차단
  licensing.py     라이선스 게이트. 00_DOCS/licenses/<pack>.md frontmatter 검사
  catalog.py       스캐너. 경로/파일명에서 category·part·animation·frame 추론
  summary.py       02_CATALOG/<pack>.summary.md 작성
  rules.py         04_RULES/*.json 로딩 + 참조 무결성 검증
  palette.py       03_PALETTES/*.json 로딩 + multiply tint recolor
  compose.py       레이어 alpha-over 합성, crop 캐시
  generate.py      결정적 생성기 (sha256 기반 슬롯별 난수 스트림)
  contactsheet.py  contact sheet + 방향 정렬 확인 시트
  validate.py      검증 + 리포트
  attribution.py   파일 단위 provenance 집계 + attribution 리포트
  unity_export.py  06_UNITY_EXPORT 패키징
  packs/           팩별 adapter (pack-specific 지식은 여기에만)
    lpc.py         Universal LPC — sheet_definitions / CREDITS.csv 파서
unity/
  GeneratedCharacter.cs          ScriptableObject (런타임)
  GeneratedCharacterImporter.cs  Editor 임포터
```

## 두 개의 분류 축 (섞지 않는다)

스캐너는 서로 독립된 두 어휘를 쓴다. **합치지 마라** — 합치는 순간 environment 팩
단어가 character 분류를 오염시킨다.

| 축 | 어휘 | 채우는 필드 | 예 |
|---|---|---|---|
| 신체 파츠 | `BODY_PART_VOCAB` | `category` | body, head, hair, weapon |
| asset 종류 | `KIND_VOCAB` | `kind_hint` → `asset_kind` | character, tileset, prop |

`chair` / `desk` / `wall` / `lamp` 같은 단어를 `BODY_PART_VOCAB` 에 넣지 않는다.
그건 카테고리가 아니라 팩별 semantic tag 이고, 파일명이 실제로 그렇게 말할 때만
`tags` 에 원시 토큰으로 들어간다 (분류가 아니라 색인이다).

### asset_kind

`character_part` `composed_character` `environment_tile` `prop`
`animation_frame` `spritesheet` `source_document` `unknown`

**`character_part` 만 generation 후보다.** 나머지는 카탈로그에 기록만 된다.
근거가 없으면 `unknown` 으로 남긴다 — 억지로 채우지 않는다.

### packaging

`sequence` (검증된 연속 프레임) · `sheet` (셀 격자) · `individual` (단품)

프레임 시퀀스 판정은 **파일 하나가 아니라 형제 파일들을 보고** 한다.
`Old/Tileset_16x16_1.png` 의 `_1` 은 프레임이 아니라 타일셋 번호다. 번호가
{1,2,3,9,16} 처럼 끊겨 있으면 시퀀스가 아니고, `variant_index` 로 되돌린다.

### animation_source

애니메이션 이름을 **어디서 읽었는지**. 두 형태를 구분한다.

| 값 | 예 | 뜻 |
|---|---|---|
| `frame_sequence` | `walk_0.png`, `walk_1.png` | 프레임 번호가 붙은 시퀀스 |
| `sheet_name` | `Walk.png`, `Attack1.png` | 파일 하나가 애니메이션 하나 |
| `unknown` | | 근거 없음 |

**모든 PNG 파일명을 애니메이션으로 보지 않는다.** `sheet_name` 승격은 다음이
전부 갖춰진 **팩 단위** 판정일 때만 일어난다: 저장소가 `01_SOURCE/characters/` 에
두었고 · `character_part` 가 0개고 · 이미지 2장 이상이 같은 캔버스고 ·
프레임 번호가 하나도 없다. 하나라도 어긋나면 `unknown` 을 유지한다.

### side ≠ direction

`side` 는 **신체/파츠의 좌우**에만 쓴다 (`Left feet`, `footL1`, `wing_l`).
같은 이름 안에 신체 파츠 어휘가 없으면 그 left/right 는 side 가 아니다.

```
Left feet     -> side=left     (feet 가 파츠 어휘)
footL1        -> side=left     (foot 가 파츠 어휘)
StrafeLeft    -> side=unknown  (이동 방향이다)
RunBackwards  -> side=unknown
```

### direction 축

좌표축은 **(animation, direction, frame)** 이다. 다만 방향이 증명되지 않은 팩에서는
`parts` 인덱스에 direction 단계를 만들지 않는다 — 축이 늘면 규칙과 generator 가
한 단계 깊어지는데 방향 없는 팩에서는 순수한 비용이기 때문이다. 방향이 실제로
읽힌 애니메이션에만 `directions` 가 붙는다.

`pack.direction_axis` 는 `{present, encoding, values}` 다. 파일명에서 못 찾으면
`present: unknown` 이고 **`no` 가 아니다** — HD Survivor 는 방향 8개를 시트의
행에 담고 있어 파일명만으로는 있는지조차 알 수 없다. "못 찾았다"와 "없다"는 다르다.

## generation capability

generator 가 **암묵적으로** 전제하던 조건(`pre_aligned` / 동일 canvas / 동일 크기)을
카탈로그가 명시적으로 계산한다. `02_CATALOG/<pack>.json` 의 `pack.capabilities`.

값은 라이선스와 같은 3상태다 — **증명 못 하면 `no` 가 아니라 `unknown`**.

| capability | CC0 | LPC | Modern Interiors | HD Survivor |
|---|---|---|---|---|
| `parts_separable` | yes | **yes** | no | no |
| `shared_canvas` | yes | **no** | no | yes |
| `shared_cell` | — | **yes** | — | — |
| `pre_aligned` | yes | **yes** | unknown | unknown |
| `shared_origin` | yes | **yes** | unknown | unknown |
| `animation_compatible` | yes | **yes** | unknown | unknown |
| `directional` | unknown | **yes** | unknown | unknown |
| `composable` | **yes** | **yes** | no | no |
| `generation_mode` | modular_composition | **modular_composition** | unsupported | composed_sheet |
| `origin_policy` | shared_canvas | **logical_cell** | unknown | unknown |
| `reason` | — | — | `atlas_only_no_individual_props` | `composed_sheets_only` |

LPC 의 `shared_canvas: no` 는 애니메이션마다 시트 크기가 다르기 때문이다
(walk 576×256 / run 512×256). 합성에 필요한 건 팩 전체 이미지 크기가 아니라
겹쳐지는 레이어들의 **논리 셀**이 같은지이고, 그건 `shared_cell` 이 답한다.

`origin_policy` 는 pivot 의 근거다 (`shared_canvas` / `unknown`).
**자동 검출하지 않는다** — alpha 기반 pivot 검출도, foot detection 도 하지 않고,
사람이 실측한 값(HD Survivor 의 y=90 등)을 generic default 로 넣지도 않는다.
자리만 만들어 두고 팩이 근거를 제공할 때 채운다.

`composable = parts_separable ∧ pre_aligned ∧ animation_compatible` 이고,
이게 modular composition 이 가능한 조건이다.

### generation_mode 가 갈라놓는 것

| mode | 뜻 | compose.py 입력 | Unity 소비 경로 |
|---|---|---|---|
| `modular_composition` | 파츠를 골라 합성 | **가능** | 구운 시트 |
| `composed_sheet` | 완성 캐릭터 시트 | **불가** | Animator + 시트 슬라이싱 |
| `unsupported` | 캐릭터 생성 대상 아님 | 불가 | — |

**`compose.py` 는 modular composition 전용 엔진이다.** 이미 합성된 시트를
통과시키기 위한 예외 코드를 넣지 않는다 — `compose.require_modular()` 가
`UnsupportedModeError` 로 즉시 막는다. composed-sheet 렌더러가 필요해지면
별도 모듈이어야 한다.

`compose.animation_box()` 의 `animation_bbox` 의존성은 CC0 전용 가정이 아니라
pre-aligned 합성 자체의 요구사항이고, 입력 계약(`pre_aligned: yes`)과 같은 조건이라
계약을 통과한 팩에는 항상 존재한다.

조합 불가 팩을 generator 에 넣으면 곁가지 오류가 아니라 `UnsupportedPackError` 로
즉시 멈추고 `reason` 을 들고 있는다. **실패가 아니라 명시적 SKIP** 이다:

```python
from ap2d import catalog, generate
generate.generation_status(catalog.load_catalog("02_CATALOG/<pack>.json"))
# -> {"status": "skipped", "generation_mode": "composed_sheet",
#     "reason": "composed_sheets_only", "capabilities": {...}}
```

`directional` 이 CC0 도 `unknown` 인 이유: 스캐너는 파일명에서 방향을 못 찾았을 뿐,
**방향이 없다는 것을 증명한 적은 없다.** HD Survivor 는 실제로 방향 8개를 시트의
행에 담고 있어서 파일명만 봐서는 알 수 없다.

## pack adapter

경로/파일명 추론으로는 읽을 수 없지만 팩이 **권위 metadata 를 직접 제공**하는 경우에만
adapter 를 쓴다. adapter 는 표준 카탈로그 스키마를 만들어 돌려주고, 그 뒤 단계는 전부
generic 이다.

```bash
python3 tools/scan_pack.py 01_SOURCE/characters/lpc_ulpc-generator_phase1 --adapter lpc
```

adapter 이름은 카탈로그의 `pack.adapter` 에 남아서 재스캔 때 자동으로 다시 쓰인다.

**pack-specific 지식은 `ap2d/packs/` 안에만 둔다.** generic 모듈에
`if "lpc" in pack_name` 같은 분기를 뿌리지 않는다 — 테스트가 AST 로 이걸 강제한다
(주석에서 예로 드는 건 허용, 실행 코드가 아는 건 금지).

### physical layout ≠ logical topology

두 modular 팩이 물리적으로 전혀 다르게 저장돼 있지만 같은 논리 좌표를 갖는다:

| | CC0 | LPC |
|---|---|---|
| 물리 단위 | PNG 1장 = 프레임 1개 | PNG 1장 = **(방향 × 프레임) 시트** |
| 좌표 | `(slot, asset, animation, frame)` | `(slot, asset, animation, direction, frame)` |
| resolve | 파일 열어 애니메이션 bbox 로 crop | 시트 열어 셀로 crop |
| 캔버스 | 2048² 전체 | 64×64 논리 셀 |

`compose.resolve_layer()` 가 이 차이를 흡수하는 **유일한 지점**이고,
그 뒤 `compose_frame()` 의 alpha-over 루프는 두 팩이 같은 코드를 탄다.

## 라이선스 capability

`commercial_use` 는 `yes` / `no` / `unknown` 3상태다. `unknown` 은 `yes` 로
반올림하지 않는다.

| 상태 | scan | generation | export | 상업 출시 |
|---|---|---|---|---|
| `pipeline_approved: yes` + `commercial_use: yes` | ○ | ○ | ○ | ○ |
| `pipeline_approved: yes` + `commercial_use: no` | ○ | ○ (비상업 검증) | ○ | **×** |
| `pipeline_approved: no` / `modification: no` / 기록 없음 | ○ | **차단** | — | × |

`commercial_use: no` 는 generation 을 막는 hard gate 가 **아니다**. 대신
`commercial_release_eligible: false` 가 계산되어
catalog summary → generation.json → Unity manifest → validation report
전부에 실려 나가고, markdown 리포트 상단에 경고 배너가 붙는다.

## 지켜지는 불변식

- **01_SOURCE 는 읽기 전용.** `paths.assert_writable()` 이 모든 쓰기 경로를 지나가고,
  `01_SOURCE` 아래면 `PermissionError` 로 죽는다. validator 는 매번 소스 전체를
  sha256 으로 다시 확인한다.
- **결정적 생성.** `random.random()` / 현재 시각 / 파이썬 내장 `hash()` 를 쓰지 않는다.
  난수 스트림은 `sha256("<rule>|<seed>|<attempt>|<key>")` 로 만든다. 슬롯마다 독립
  스트림이라 규칙에 슬롯을 추가해도 기존 슬롯의 결과가 밀리지 않는다.
- **라이선스 게이트.** `pipeline_approved: yes` 가 아니면 generator 가 진입 자체를 거부한다.
- **카탈로그에 타임스탬프 없음.** 같은 소스 = 같은 카탈로그 바이트여야 소스 변조를 잡을 수 있다.
- **Export Contract v1.** 소비자 패키지는 `Generated/` 와 `.meta` 를 절대 지우지 않고,
  같은 입력이면 같은 `content_fingerprint` 가 나온다. Unity 에셋은 in-place 로 갱신해
  GUID 를 유지한다 — 재-export 가 게임 쪽 참조를 끊으면 안 된다.
  → `00_DOCS/export-contract-v1.md`
- **소스 지문은 한 가지 방법으로만 낸다.** `ap2d.integrity.tree_fingerprint()` —
  상대경로 + 바이트, 명시적 정렬, mtime/절대경로 없음, `.DS_Store` 등 제외.
  `python3 tools/source_fingerprint.py` 로 확인한다.
  현재 `01_SOURCE` baseline: `7efe94e67e9ec190c08bf5f026ca07c5f2e89b0aed17cbbee95b71db50c314eb`
- **분포는 세되 판정하지 않는다.** 리포트의 「관측된 분포」는 후보 중 몇 개가 실제로
  나왔는지를 셀 뿐이다. 임계값도 등급도 자동 보정도 없다 — 좋은지 나쁜지는 사람이 정한다.
- **소비자 식별자를 지어내지 않는다.** `order.consumer` 는 발주한 쪽이 발급한다.
  못 받았으면 `unknown` 이 정당한 값이다.
- **게임 정책은 게임이 소유한다.** Factory 가 20개 외형을 줘도 게임이 2개만 허용할 수 있다.
  그 판단은 `Assets/Game/**` 의 GameArtProfile 에 있고 exporter 는 그 존재를 모른다.
  집단 결정(`NpcPopulationFactory` → `NpcDefinition[]`)과 씬 생성(`CharacterSpawner`)도
  게임 쪽에서 분리돼 있다.
  → `00_DOCS/game-art-profile.md`

## 새 팩 추가하기

1. `01_SOURCE/<domain>/<vendor>_<pack>_<version>/` 에 원본 그대로 풀고 `SOURCE.md` 작성
2. `00_DOCS/licenses/<pack>.md` 작성 (frontmatter 필수 — `licensing.REQUIRED_FIELDS` 참고)
3. `python3 tools/scan_pack.py <팩 폴더>` → `.summary.md` 를 사람이 읽고 확인
4. summary 의 "발견된 파츠" 표를 보고 `04_RULES/<이름>.json` 작성
5. `python3 tools/run_pipeline.py 04_RULES/<이름>.json`

3단계에서 summary 의 `generation capability` 표를 먼저 본다.
`composable: no` 면 규칙을 쓸 필요가 없다 — `reason` 이 왜인지 말해준다.

스캐너가 파츠를 못 알아보면 `catalog.py` 의 `BODY_PART_VOCAB` 에 단어만 추가한다.
어휘에 없으면 `composed_character` / `spritesheet` / `unknown` 으로 남고 summary 의
anomaly 절에 보고되므로, 조용히 잘못 조합되는 일은 없다.
