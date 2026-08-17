# limezu_modern-interiors-free_v2.2 — 카탈로그 요약

자동 생성됨: `tools/scan_pack.py`. 손으로 고치지 않는다.

> ⛔ **NON-COMMERCIAL SOURCE — generated outputs are not approved for commercial game use.**
>
> 라이선스: `LimeZu Free Version License (proprietary)` · `commercial_use: no` · 기록: `00_DOCS/licenses/limezu_modern-interiors-free_v2.2.md`

| 항목 | 값 |
|---|---|
| 소스 경로 | `01_SOURCE/environments/limezu_modern-interiors-free_v2.2` |
| 총 파일 수 | 67 |
| 이미지 수 | 64 |
| character_part 프레임 수 | 0 |
| 라이선스 | `LimeZu Free Version License (proprietary)` |
| 상업적 사용 | `no` |
| commercial_release_eligible | **false** |
| 팩 표준 캔버스 | 일관되지 않음 |
| pre-aligned (단순 합성 가능) | 아니오 |
| 내용 bbox (전 파츠 합집합) | - |
| 중복 hash 그룹 | 0 |
| 선언된 타일 크기 | `16x16`×42, `32x32`×10, `48x48`×10 |

## generation capability

generator 가 암묵적으로 전제하던 조건을 명시적으로 계산한 값이다. 증명할 수 없으면 `no` 가 아니라 `unknown` 이다.

| capability | 값 | 뜻 |
|---|---|---|
| `parts_separable` | `no` | 조합할 파츠가 개별 주소로 존재하는가 |
| `shared_canvas` | `no` | 합성 대상 이미지가 한 캔버스를 쓰는가 |
| `pre_aligned` | `unknown` | 파츠가 사전 정렬되어 alpha-over 만으로 합성되는가 |
| `shared_origin` | `unknown` | 파츠가 원점을 공유하는가 |
| `animation_compatible` | `unknown` | 모든 파츠가 같은 애니메이션 집합을 갖는가 |
| `directional` | `unknown` | 방향 변형이 있는가 |
| `composable` | `no` | **modular composition 이 가능한가** (위 셋의 곱) |
| `origin_policy` | `unknown` | pivot 의 근거. 자동 검출은 하지 않는다 |

### generation_mode: `unsupported`

캐릭터 생성 대상이 아니다.

```
generation_mode: unsupported
reason: atlas_only_no_individual_props
```

전부 아틀라스라 개별 주소를 가진 오브젝트가 없다. `compose.py` 는 modular composition 전용 엔진이라 이 팩을 받으면 `UnsupportedModeError` 로 즉시 멈춘다 — 실패가 아니라 명시적 SKIP 이다. 이미 합성된 시트를 통과시키기 위한 예외 코드는 넣지 않는다.

### direction 축

| 항목 | 값 |
|---|---|
| `present` | `unknown` |
| `encoding` | `unknown` |
| `values` | — |

파일명에서 방향을 찾지 못했다. **이는 '방향이 없다'는 뜻이 아니다** — 방향을 시트의 행에 담는 팩이 실제로 존재하고, 그런 팩은 파일명만 봐서는 알 수 없다. 그래서 `no` 가 아니라 `unknown` 이다.

## asset kind

| asset_kind | 파일 수 | 뜻 |
|---|---:|---|
| `character_part` | 0 | 조합 가능한 신체 파츠 (generation 후보) |
| `composed_character` | 36 | 캐릭터 전체가 그려진 완성 이미지 |
| `environment_tile` | 21 | 타일 격자 기반 환경/타일셋 이미지 |
| `prop` | 0 | 단품 오브젝트 이미지 |
| `animation_frame` | 0 | 시퀀스의 한 프레임이지만 파츠 의미는 미확정 |
| `spritesheet` | 6 | 격자는 확인됐으나 내용 미상 |
| `source_document` | 3 | 라이선스/README/레이어 소스 등 비이미지 |
| `unknown` | 1 | 판단 불가 — 추측하지 않고 남겨둔 것 |
| **합계** | **67** | |

`character_part` 만 조합(generation) 후보다. 나머지는 카탈로그에 기록만 된다.

### packaging (sheet / individual / sequence)

| packaging | 이미지 수 |
|---|---:|
| `sheet` | 62 |
| `individual` | 2 |

### 배율본 후보 (scale_variant_candidate)

파일명의 타일 크기 토큰만 다르고 치수 비율이 정확히 일치하는 그룹이다. **픽셀을 비교한 것이 아니므로 내용이 같다고 증명된 것은 아니다.**

- `Modern tiles_Free/Interiors_free/*/Interiors_free_*.png` — 3개: `Interiors_free_16x16.png`, `Interiors_free_32x32.png`, `Interiors_free_48x48.png`
- `Modern tiles_Free/Interiors_free/*/Room_Builder_free_*.png` — 3개: `Room_Builder_free_16x16.png`, `Room_Builder_free_32x32.png`, `Room_Builder_free_48x48.png`
- `Modern tiles_Free/Old/Tileset_*_1.png` — 3개: `Tileset_16x16_1.png`, `Tileset_32x32_1.png`, `Tileset_48x48_1.png`
- `Modern tiles_Free/Old/Tileset_*_16.png` — 3개: `Tileset_16x16_16.png`, `Tileset_32x32_16.png`, `Tileset_48x48_16.png`
- `Modern tiles_Free/Old/Tileset_*_2.png` — 3개: `Tileset_16x16_2.png`, `Tileset_32x32_2.png`, `Tileset_48x48_2.png`
- `Modern tiles_Free/Old/Tileset_*_3.png` — 3개: `Tileset_16x16_3.png`, `Tileset_32x32_3.png`, `Tileset_48x48_3.png`
- `Modern tiles_Free/Old/Tileset_*_9.png` — 3개: `Tileset_16x16_9.png`, `Tileset_32x32_9.png`, `Tileset_48x48_9.png`
- `Modern tiles_Free/Old/idle_*_2.png` — 3개: `idle_16x16_2.png`, `idle_32x32_2.png`, `idle_48x48_2.png`
- `Modern tiles_Free/Old/mv/Character_2_*_RPGMAKER.png` — 3개: `Character_2_16x16_RPGMAKER.png`, `Character_2_32x32_RPGMAKER.png`, `Character_2_48x48_RPGMAKER.png`
- `Modern tiles_Free/Old/run_horizontal_*_2.png` — 3개: `run_horizontal_16x16_2.png`, `run_horizontal_32x32_2.png`, `run_horizontal_48x48_2.png`

## 발견된 파츠 (조합 가능)

**없음.** 이 팩에서는 조합 가능한 modular character part 를 하나도 찾지 못했다. generation 규칙을 쓸 수 있는 소재가 없다는 뜻이다.

## 분포

### category (body part 어휘 전용)

| category | 이미지 수 |
|---|---:|
| `unknown` | 64 |

### direction

| direction | 이미지 수 |
|---|---:|
| `unknown` | 64 |

### side

| side | 이미지 수 |
|---|---:|
| `unknown` | 64 |

### 해상도

| 해상도 | 이미지 수 |
|---|---:|
| `384x32` | 17 |
| `64x32` | 5 |
| `144x32` | 4 |
| `160x160` | 4 |
| `192x32` | 4 |
| `320x320` | 4 |
| `384x224` | 4 |
| `480x480` | 4 |
| `1152x96` | 1 |
| `128x64` | 1 |
| `144x384` | 1 |
| `1886x1792` | 1 |
| `192x224` | 1 |
| `192x96` | 1 |
| `256x1424` | 1 |
| `272x368` | 1 |
| `384x448` | 1 |
| `48x128` | 1 |
| `512x2848` | 1 |
| `544x736` | 1 |
| `576x672` | 1 |
| `576x768` | 1 |
| `768x4272` | 1 |
| `768x64` | 1 |
| `816x1104` | 1 |
| `96x256` | 1 |

### 파일 타입

| file_type | 파일 수 |
|---|---:|
| `image` | 64 |
| `text` | 3 |

### unknown 분류 수

| 필드 | unknown 이미지 수 |
|---|---:|
| category | 64 |
| part | 0 |
| animation | 64 |
| direction | 64 |
| side | 64 |

## naming anomaly / 잠재 문제

- **파츠로 확정하지 않은 이미지 36장 (character_part 후보에서 제외)**
  - `Modern tiles_Free/Characters_free`
  - `Modern tiles_Free/Characters_free/RPGMAKERMV`
  - `Modern tiles_Free/Old/mv`

- **파일명 끝 번호가 프레임이 아니었던 이미지 21장 (번호가 연속이 아니라 variant_index 로 되돌림)**
  - `Modern tiles_Free/Old`

- **정체 미상 시트 6장 (격자는 확인됐으나 무엇의 격자인지 추론 불가)**
  - `Modern tiles_Free/Old/idle_16x16_2.png`
  - `Modern tiles_Free/Old/idle_32x32_2.png`
  - `Modern tiles_Free/Old/idle_48x48_2.png`
  - `Modern tiles_Free/Old/run_horizontal_16x16_2.png`
  - `Modern tiles_Free/Old/run_horizontal_32x32_2.png`
  - `Modern tiles_Free/Old/run_horizontal_48x48_2.png`

## 중복 hash

없음.

## 파이프라인 적용 시 주의

- **조합 가능한 character part 가 0개다.** 이 팩은 현재 generator 의 입력이 될 수 없다. character_part 는 (신체 파츠 어휘 확정 + 검증된 프레임 시퀀스) 두 조건을 모두 만족해야 하는데 하나도 만족하지 못했다.
- **개별 prop 이미지가 0개다** (environment_tile 21장 / spritesheet 6장). 환경 오브젝트가 전부 아틀라스 안에 들어 있어서, 개별 주소를 가진 소품이 존재하지 않는다. floor/wall/table/chair 조합을 하려면 아틀라스 slicing 과 격자 칸 semantic labeling 이 선행되어야 한다 — 둘 다 현재 범위 밖이다.
- 팩이 파일명에 타일 크기를 직접 적어두었다 (16x16, 32x32, 48x48). 추론이 아니라 팩이 선언한 값이므로 그대로 신뢰해 격자 정합을 검사했다. 향후 slicing 이나 Sprite Library 전환에 필요한 격자 정보(columns/rows/cells)는 각 엔트리의 `inferred.grid` 에 이미 들어 있다.
- 같은 내용의 배율본이 10 그룹 있다. SHA 가 다르므로 중복 hash 검사에는 걸리지 않는다. 한 배율만 골라 쓰고 나머지는 파이프라인에서 제외해야 카탈로그와 아틀라스가 3배로 부풀지 않는다.
- 완성된 캐릭터 이미지 36장이 섞여 있다. 조합 소스가 아니라 참조용이므로 generator 후보에서 제외된다.

## variation 생성 가능성

| 축 | 필요한 것 | 이 팩 | 판정 |
|---|---|---:|---|
| character variation | 조합 가능한 character_part | 0종 | **불가** |
| environment variation | 개별 주소를 가진 prop | 0개 | **불가** |

### Environment variation POC: `SKIPPED`

> `SKIPPED — source pack does not expose individually addressable semantic props without atlas slicing/manual labeling`

**어떤 구조 때문에 불가능한가**

- 환경 이미지 27장이 전부 아틀라스/시트다 (environment_tile 21, spritesheet 6). packaging 이 `individual` 인 환경 이미지가 없다.
- 개별 prop PNG 가 **0개**다. 조합 슬롯(floor / wall / table / chair / decoration)에 넣을 수 있는 주소 단위가 존재하지 않는다.
- 아틀라스를 잘라도 격자 칸 하나가 의자인지 책상인지는 파일명·폴더명에 적혀 있지 않다. 알아내려면 사람이 눈으로 보고 칸마다 라벨을 붙여야 한다.

**따라서 필요한 두 가지가 모두 이번 범위 밖이다**

1. atlas 자동 slicing
2. 격자 칸 semantic labeling (수동 매핑)

억지로 만들면 카탈로그에 근거 없는 분류가 들어간다. 하지 않는다.

**어떤 조건이면 POC 가 가능한가**

- prop 이 개별 PNG 로 분리되어 있고 (`packaging: individual`),
- 파일명이나 폴더명이 종류를 말해주며 (`chairs/office_chair_01.png` 처럼),
- 같은 종류 안에 변형이 2개 이상 있을 것.

세 조건을 만족하면 현재 generator 의 slot/rule/seed 구조를 거의 그대로 재사용할 수 있다. 슬롯 이름만 다르고 메커니즘은 동일하다.

격자 정보(`inferred.grid`: columns/rows/cells)와 선언된 타일 크기는 이미 카탈로그에 기록해 두었다. 나중에 slicing 단계를 만들 때 다시 스캔할 필요는 없다.
