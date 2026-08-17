# lpc_ulpc-generator_phase1 — 카탈로그 요약

자동 생성됨: `tools/scan_pack.py`. 손으로 고치지 않는다.

| 항목 | 값 |
|---|---|
| 소스 경로 | `01_SOURCE/characters/lpc_ulpc-generator_phase1` |
| 총 파일 수 | 829 |
| 이미지 수 | 59 |
| character_part 프레임 수 | 59 |
| 라이선스 | `per-asset (OGA-BY 3.0 / CC-BY 3.0 / CC0-1.0)` |
| 상업적 사용 | `yes` |
| commercial_release_eligible | **true** |
| 팩 표준 캔버스 | 64x64 |
| pre-aligned (단순 합성 가능) | 예 |
| 내용 bbox (전 파츠 합집합) | [0, 0, 64, 64] |
| 중복 hash 그룹 | 12 |
| 선언된 타일 크기 | `64x64`×59 |

## generation capability

generator 가 암묵적으로 전제하던 조건을 명시적으로 계산한 값이다. 증명할 수 없으면 `no` 가 아니라 `unknown` 이다.

| capability | 값 | 뜻 |
|---|---|---|
| `parts_separable` | `yes` | 조합할 파츠가 개별 주소로 존재하는가 |
| `shared_canvas` | `no` | 합성 대상 이미지가 한 캔버스를 쓰는가 |
| `pre_aligned` | `yes` | 파츠가 사전 정렬되어 alpha-over 만으로 합성되는가 |
| `shared_origin` | `yes` | 파츠가 원점을 공유하는가 |
| `animation_compatible` | `partial` | 모든 파츠가 같은 애니메이션 집합을 갖는가 |
| `directional` | `yes` | 방향 변형이 있는가 |
| `composable` | `yes` | **modular composition 이 가능한가** (위 셋의 곱) |
| `origin_policy` | `logical_cell` | pivot 의 근거. 자동 검출은 하지 않는다 |

### generation_mode: `modular_composition`

파츠를 골라 합성한다. compose.py 의 입력이 된다.

### direction 축

| 항목 | 값 |
|---|---|
| `present` | `yes` |
| `encoding` | `sheet_row` |
| `values` | `east`, `north`, `south`, `west` |

## asset kind

| asset_kind | 파일 수 | 뜻 |
|---|---:|---|
| `character_part` | 59 | 조합 가능한 신체 파츠 (generation 후보) |
| `composed_character` | 0 | 캐릭터 전체가 그려진 완성 이미지 |
| `environment_tile` | 0 | 타일 격자 기반 환경/타일셋 이미지 |
| `prop` | 0 | 단품 오브젝트 이미지 |
| `animation_frame` | 0 | 시퀀스의 한 프레임이지만 파츠 의미는 미확정 |
| `spritesheet` | 0 | 격자는 확인됐으나 내용 미상 |
| `source_document` | 770 | 라이선스/README/레이어 소스 등 비이미지 |
| `unknown` | 0 | 판단 불가 — 추측하지 않고 남겨둔 것 |
| **합계** | **829** | |

`character_part` 만 조합(generation) 후보다. 나머지는 카탈로그에 기록만 된다.

### packaging (sheet / individual / sequence)

| packaging | 이미지 수 |
|---|---:|
| `sheet` | 59 |

## 발견된 파츠 (조합 가능)

| category | part | side | 애니메이션 | 총 프레임 |
|---|---|---|---|---:|
| `body` | `body` | unknown | idle, run, walk | 76 |
| `feet` | `feet_boots_basic` | unknown | idle, run, walk | 76 |
| `feet` | `feet_boots_fold` | unknown | idle, run, walk | 76 |
| `feet` | `feet_boots_revised` | unknown | idle, run, walk | 76 |
| `hair` | `hair_afro` | unknown | idle, run, walk | 76 |
| `hair` | `hair_braid` | unknown | idle, run, walk | 76 |
| `hair` | `hair_cornrows` | unknown | idle, run, walk | 76 |
| `hair` | `hair_dreadlocks_long` | unknown | idle, run, walk | 76 |
| `hair` | `hair_dreadlocks_short` | unknown | idle, run, walk | 76 |
| `head` | `heads_boarman` | unknown | idle, run, walk | 76 |
| `head` | `heads_wartotaur` | unknown | idle, run, walk | 76 |
| `legs` | `legs_armour` | unknown | idle, walk | 44 |
| `legs` | `legs_hose` | unknown | idle, run, walk | 76 |
| `legs` | `legs_leggings` | unknown | idle, run, walk | 76 |
| `legs` | `legs_leggings2` | unknown | idle, run, walk | 76 |
| `torso` | `torso_clothes_longsleeve` | unknown | idle, run, walk | 76 |
| `torso` | `torso_clothes_longsleeve2` | unknown | idle, run, walk | 76 |
| `torso` | `torso_clothes_longsleeve2_buttoned` | unknown | idle, run, walk | 76 |
| `torso` | `torso_clothes_longsleeve2_cardigan` | unknown | idle, run, walk | 76 |

## 분포

### category (body part 어휘 전용)

| category | 이미지 수 |
|---|---:|
| `hair` | 18 |
| `torso` | 12 |
| `legs` | 11 |
| `feet` | 9 |
| `head` | 6 |
| `body` | 3 |

### animation (character_part 만)

| animation | 프레임 수 |
|---|---:|
| `idle` | 20 |
| `walk` | 20 |
| `run` | 19 |

### direction

| direction | 이미지 수 |
|---|---:|
| `multi` | 59 |

### side

| side | 이미지 수 |
|---|---:|
| `unknown` | 59 |

### 해상도

| 해상도 | 이미지 수 |
|---|---:|
| `128x256` | 20 |
| `576x256` | 20 |
| `512x256` | 19 |

### 파일 타입

| file_type | 파일 수 |
|---|---:|
| `text` | 770 |
| `image` | 59 |

### unknown 분류 수

| 필드 | unknown 이미지 수 |
|---|---:|
| category | 0 |
| part | 0 |
| animation | 0 |
| direction | 0 |
| side | 59 |

## naming anomaly / 잠재 문제

- **팩 표준 캔버스 64x64 와 다른 이미지**
  - `spritesheets/body/bodies/male/idle.png (128x256)`
  - `spritesheets/body/bodies/male/run.png (512x256)`
  - `spritesheets/body/bodies/male/walk.png (576x256)`
  - `spritesheets/feet/boots/basic/male/idle.png (128x256)`
  - `spritesheets/feet/boots/basic/male/run.png (512x256)`
  - `spritesheets/feet/boots/basic/male/walk.png (576x256)`
  - `spritesheets/feet/boots/fold/male/idle.png (128x256)`
  - `spritesheets/feet/boots/fold/male/run.png (512x256)`
  - `spritesheets/feet/boots/fold/male/walk.png (576x256)`
  - `spritesheets/feet/boots/revised/male/idle.png (128x256)`
  - `spritesheets/feet/boots/revised/male/run.png (512x256)`
  - `spritesheets/feet/boots/revised/male/walk.png (576x256)`
  - `spritesheets/hair/afro/adult/idle.png (128x256)`
  - `spritesheets/hair/afro/adult/run.png (512x256)`
  - `spritesheets/hair/afro/adult/walk.png (576x256)`
  - `spritesheets/hair/braid/adult/bg/idle.png (128x256)`
  - `spritesheets/hair/braid/adult/bg/run.png (512x256)`
  - `spritesheets/hair/braid/adult/bg/walk.png (576x256)`
  - `spritesheets/hair/braid/adult/fg/idle.png (128x256)`
  - `spritesheets/hair/braid/adult/fg/run.png (512x256)`

## 중복 hash

바이트가 동일한 파일 그룹 12개. 프레임이 실제로 안 움직이는 구간이라는 뜻이라 반드시 오류는 아니다.

- `2641f6dde5ba…` × 8 — `sheet_definitions/body/meta_body.json`, `sheet_definitions/head/heads/meta_head.json`, `sheet_definitions/headwear/coverings/hoods/meta_hoods.json`, `sheet_definitions/headwear/hats/caps/meta_caps.json` …
- `2a575ae28526…` × 7 — `sheet_definitions/body/wings/monarch/meta_monarch.json`, `sheet_definitions/hair/afro/meta_afro.json`, `sheet_definitions/head/eyebrows/meta_eyebrows.json`, `sheet_definitions/headwear/meta_headwear.json` …
- `6f5953f26078…` × 7 — `sheet_definitions/head/meta_head.json`, `sheet_definitions/headwear/coverings/bandana/meta_bandana.json`, `sheet_definitions/headwear/hats/meta_hats.json`, `sheet_definitions/headwear/hats/tricorne/meta_tricorne.json` …
- `7705a218dba0…` × 6 — `sheet_definitions/hair/extensions/meta_extensions.json`, `sheet_definitions/hair/meta_hair.json`, `sheet_definitions/headwear/coverings/headbands/meta_headbands.json`, `sheet_definitions/headwear/helmets/accessories/meta_accessories.json` …
- `89cafaebad45…` × 6 — `sheet_definitions/arms/meta_arms.json`, `sheet_definitions/body/wings/pixie/meta_pixie.json`, `sheet_definitions/hair/curly/meta_curly.json`, `sheet_definitions/head/ears/meta_ears.json` …
- `87dd762517ef…` × 5 — `sheet_definitions/body/wings/meta_wings.json`, `sheet_definitions/hair/short/meta_short.json`, `sheet_definitions/head/nose/meta_nose.json`, `sheet_definitions/headwear/hats/holiday/meta_holiday.json` …
- `e8cecb2192db…` × 4 — `sheet_definitions/body/wings/dragonfly/meta_dragonfly.json`, `sheet_definitions/headwear/hats/formal/meta_formal.json`, `sheet_definitions/torso/meta_torso.json`, `sheet_definitions/weapons/magic/meta_magic.json`
- `8ceb7df5f3d0…` × 3 — `sheet_definitions/body/lizard/meta_lizard.json`, `sheet_definitions/hair/pigtails/meta_pigtails.json`, `sheet_definitions/head/appendages/meta_appendages.json`
- `7f249dc15d4e…` × 2 — `sheet_definitions/body/wounds/meta_wounds.json`, `sheet_definitions/head/faces/meta_faces.json`
- `7fd856aa9944…` × 2 — `sheet_definitions/tools/meta_tools.json`, `sheet_definitions/torso/waist/meta_waist.json`
- `ef66f4d442e2…` × 2 — `sheet_definitions/body/tails/meta_tails.json`, `sheet_definitions/hair/spiky/meta_spiky.json`
- `f7b4134ec45f…` × 2 — `sheet_definitions/legs/shorts/meta_shorts.json`, `sheet_definitions/torso/aprons/meta_aprons.json`

## 파이프라인 적용 시 주의

- 팩이 파일명에 타일 크기를 직접 적어두었다 (64x64). 추론이 아니라 팩이 선언한 값이므로 그대로 신뢰해 격자 정합을 검사했다. 향후 slicing 이나 Sprite Library 전환에 필요한 격자 정보(columns/rows/cells)는 각 엔트리의 `inferred.grid` 에 이미 들어 있다.
- 모든 modular part 가 64x64 동일 캔버스에 사전 정렬되어 있다. pivot 계산 없이 alpha-over 합성만으로 캐릭터가 만들어진다.
- 실제 내용은 캔버스의 64×64 영역([0, 0, 64, 64])에만 있다. 합성 전에 이 사각형으로 잘라야 메모리/시간이 1배 절약된다.
- 변형이 1개뿐인 category: `body` — 이 슬롯들은 variation 에 기여하지 못한다.
- 중복 hash 그룹 12개. 스프라이트 아틀라스에서 중복 프레임을 합치면 용량이 줄어든다.

## variation 생성 가능성

| 축 | 필요한 것 | 이 팩 | 판정 |
|---|---|---:|---|
| character variation | 조합 가능한 character_part | 19종 | 가능 |
| environment variation | 개별 주소를 가진 prop | 0개 | **불가** |

character variation 은 `04_RULES/` 에 규칙을 쓰면 바로 생성 가능하다.
