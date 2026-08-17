# rgsdev_free-cc0-modular-vector-characters_v1 — 카탈로그 요약

자동 생성됨: `tools/scan_pack.py`. 손으로 고치지 않는다.

| 항목 | 값 |
|---|---|
| 소스 경로 | `01_SOURCE/characters/rgsdev_free-cc0-modular-vector-characters_v1` |
| 총 파일 수 | 2001 |
| 이미지 수 | 1995 |
| character_part 프레임 수 | 1512 |
| 라이선스 | `CC0-1.0` |
| 상업적 사용 | `yes` |
| commercial_release_eligible | **true** |
| 팩 표준 캔버스 | 2048x2048 |
| pre-aligned (단순 합성 가능) | 예 |
| 내용 bbox (전 파츠 합집합) | [376, 223, 1521, 2048] |
| 중복 hash 그룹 | 8 |

## generation capability

generator 가 암묵적으로 전제하던 조건을 명시적으로 계산한 값이다. 증명할 수 없으면 `no` 가 아니라 `unknown` 이다.

| capability | 값 | 뜻 |
|---|---|---|
| `parts_separable` | `yes` | 조합할 파츠가 개별 주소로 존재하는가 |
| `shared_canvas` | `yes` | 합성 대상 이미지가 한 캔버스를 쓰는가 |
| `pre_aligned` | `yes` | 파츠가 사전 정렬되어 alpha-over 만으로 합성되는가 |
| `shared_origin` | `yes` | 파츠가 원점을 공유하는가 |
| `animation_compatible` | `yes` | 모든 파츠가 같은 애니메이션 집합을 갖는가 |
| `directional` | `unknown` | 방향 변형이 있는가 |
| `composable` | `yes` | **modular composition 이 가능한가** (위 셋의 곱) |
| `origin_policy` | `shared_canvas` | pivot 의 근거. 자동 검출은 하지 않는다 |

### generation_mode: `modular_composition`

파츠를 골라 합성한다. compose.py 의 입력이 된다.

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
| `character_part` | 1512 | 조합 가능한 신체 파츠 (generation 후보) |
| `composed_character` | 468 | 캐릭터 전체가 그려진 완성 이미지 |
| `environment_tile` | 0 | 타일 격자 기반 환경/타일셋 이미지 |
| `prop` | 3 | 단품 오브젝트 이미지 |
| `animation_frame` | 3 | 시퀀스의 한 프레임이지만 파츠 의미는 미확정 |
| `spritesheet` | 0 | 격자는 확인됐으나 내용 미상 |
| `source_document` | 6 | 라이선스/README/레이어 소스 등 비이미지 |
| `unknown` | 9 | 판단 불가 — 추측하지 않고 남겨둔 것 |
| **합계** | **2001** | |

`character_part` 만 조합(generation) 후보다. 나머지는 카탈로그에 기록만 된다.

### packaging (sheet / individual / sequence)

| packaging | 이미지 수 |
|---|---:|
| `sequence` | 1983 |
| `individual` | 12 |

## 발견된 파츠 (조합 가능)

| category | part | side | 애니메이션 | 총 프레임 |
|---|---|---|---|---:|
| `body` | `body1` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `eyes` | `eyes1` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `eyes` | `eyes2` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `eyes` | `eyes3` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `eyes` | `eyes4` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `eyes` | `eyes5` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `eyes` | `eyes6` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `eyes` | `eyes7` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `foot` | `footL1` | left | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `foot` | `footR1` | right | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `hair` | `hair1` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `hair` | `hair2` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `hair` | `hair3` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `hand` | `handL1` | left | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `hand` | `handR1` | right | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `head` | `head1` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `head` | `head2` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `head` | `head3` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `horn` | `horn1` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `horn` | `horn2` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `horn` | `horn3` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `horn` | `horn4` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `horn` | `horn5` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `mouth` | `mouth1` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `mouth` | `mouth2` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `mouth` | `mouth3` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `mouth` | `mouth4` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `mouth` | `mouth5` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `mouth` | `mouth6` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `mouth` | `mouth7` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `mouth` | `mouth8` | unknown | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `weapon` | `weaponR1` | right | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `weapon` | `weaponR2` | right | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `weapon` | `weaponR3` | right | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `wing` | `wingL1` | left | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |
| `wing` | `wingR1` | right | death, fall, hit, idle, jumpEnd, jumpStart, roll, walk | 42 |

## 분포

### category (body part 어휘 전용)

| category | 이미지 수 |
|---|---:|
| `unknown` | 480 |
| `mouth` | 336 |
| `eyes` | 294 |
| `horn` | 210 |
| `weapon` | 129 |
| `hair` | 126 |
| `head` | 126 |
| `foot` | 84 |
| `hand` | 84 |
| `wing` | 84 |
| `body` | 42 |

### animation (character_part 만)

| animation | 프레임 수 |
|---|---:|
| `death` | 360 |
| `walk` | 288 |
| `idle` | 216 |
| `fall` | 180 |
| `roll` | 180 |
| `hit` | 108 |
| `jumpEnd` | 108 |
| `jumpStart` | 72 |

### direction

| direction | 이미지 수 |
|---|---:|
| `unknown` | 1995 |

### side

| side | 이미지 수 |
|---|---:|
| `unknown` | 1614 |
| `right` | 255 |
| `left` | 126 |

### 해상도

| 해상도 | 이미지 수 |
|---|---:|
| `2048x2048` | 1993 |
| `64x64` | 1 |
| `762x735` | 1 |

### 파일 타입

| file_type | 파일 수 |
|---|---:|
| `image` | 1995 |
| `text` | 6 |

### unknown 분류 수

| 필드 | unknown 이미지 수 |
|---|---:|
| category | 480 |
| part | 0 |
| animation | 12 |
| direction | 1995 |
| side | 1614 |

## naming anomaly / 잠재 문제

- **파츠로 확정하지 않은 이미지 471장 (character_part 후보에서 제외)**
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Char 1/no hands`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Char 1/with hands`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Char 2/no hands`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Char 2/with hands`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Char 3/no hands`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Char 3/with hands`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Char 4/no hands`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Char 4/with hands`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Enemies/Enemy 1`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Enemies/Enemy 2`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Enemies/Enemy 3`
  - `Free 2D Animated Vector Game Character Sprites/Full body animated characters/Enemies/Enemy 4`
  - `… 외 1개 폴더`

- **팩 표준 캔버스 2048x2048 와 다른 이미지**
  - `Free 2D Animated Vector Game Character Sprites/Environment/ground3_white.png (762x735)`
  - `Free 2D Animated Vector Game Character Sprites/Extras/crosshair.png (64x64)`

## 중복 hash

바이트가 동일한 파일 그룹 8개. 프레임이 실제로 안 움직이는 구간이라는 뜻이라 반드시 오류는 아니다.

- `6341d36bc0ff…` × 20 — `Free 2D Animated Vector Game Character Sprites/Animated body parts/Bodies/body1/fall_0.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Bodies/body1/fall_1.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Bodies/body1/fall_2.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Bodies/body1/fall_3.png` …
- `6a12951e4dc8…` × 18 — `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right feet/footR1/fall_0.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right feet/footR1/hit_0.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right feet/footR1/hit_1.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right feet/footR1/hit_2.png` …
- `637c7f98a468…` × 16 — `Free 2D Animated Vector Game Character Sprites/Animated body parts/Left feet/footL1/hit_0.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Left feet/footL1/hit_1.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Left feet/footL1/hit_2.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Left feet/footL1/idle_0.png` …
- `21409cce0ec1…` × 4 — `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR1/hit_1.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR1/hit_2.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR1/idle_0.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR1/roll_0.png`
- `69fee30229c9…` × 4 — `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR2/hit_1.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR2/hit_2.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR2/idle_0.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR2/roll_0.png`
- `845b2e53ef39…` × 4 — `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR3/hit_1.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR3/hit_2.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR3/idle_0.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right weapons/weaponR3/roll_0.png`
- `5cbc57a72aa6…` × 3 — `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right wings/wingR1/hit_1.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right wings/wingR1/hit_2.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Right wings/wingR1/idle_0.png`
- `ec906a4b1298…` × 2 — `Free 2D Animated Vector Game Character Sprites/Animated body parts/Left wings/wingL1/walk_4.png`, `Free 2D Animated Vector Game Character Sprites/Animated body parts/Left wings/wingL1/walk_6.png`

## 파이프라인 적용 시 주의

- 모든 modular part 가 2048x2048 동일 캔버스에 사전 정렬되어 있다. pivot 계산 없이 alpha-over 합성만으로 캐릭터가 만들어진다.
- 실제 내용은 캔버스의 1145×1825 영역([376, 223, 1521, 2048])에만 있다. 합성 전에 이 사각형으로 잘라야 메모리/시간이 2배 절약된다.
- 변형이 1개뿐인 category: `body` — 이 슬롯들은 variation 에 기여하지 못한다.
- 방향 변형이 없다(direction 전부 unknown). 좌우 반전이 필요하면 flip 으로 만들어야 하며, 팩이 side-view 라 8방향 게임에는 그대로 못 쓴다.
- 중복 hash 그룹 8개. 스프라이트 아틀라스에서 중복 프레임을 합치면 용량이 줄어든다.
- 완성된 캐릭터 이미지 468장이 섞여 있다. 조합 소스가 아니라 참조용이므로 generator 후보에서 제외된다.

## variation 생성 가능성

| 축 | 필요한 것 | 이 팩 | 판정 |
|---|---|---:|---|
| character variation | 조합 가능한 character_part | 36종 | 가능 |
| environment variation | 개별 주소를 가진 prop | 3개 | 가능 |

character variation 은 `04_RULES/` 에 규칙을 쓰면 바로 생성 가능하다.
