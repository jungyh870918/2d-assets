# unknown_free-hd-survivor-w-bike_v1 — 카탈로그 요약

자동 생성됨: `tools/scan_pack.py`. 손으로 고치지 않는다.

> ⛔ **NON-COMMERCIAL SOURCE — generated outputs are not approved for commercial game use.**
>
> 라이선스: `unknown` · `commercial_use: unknown` · 기록: `00_DOCS/licenses/unknown_free-hd-survivor-w-bike_v1.md`

| 항목 | 값 |
|---|---|
| 소스 경로 | `01_SOURCE/characters/unknown_free-hd-survivor-w-bike_v1` |
| 총 파일 수 | 24 |
| 이미지 수 | 23 |
| character_part 프레임 수 | 0 |
| 라이선스 | `unknown` |
| 상업적 사용 | `unknown` |
| commercial_release_eligible | **false** |
| 팩 표준 캔버스 | 일관되지 않음 |
| pre-aligned (단순 합성 가능) | 아니오 |
| 내용 bbox (전 파츠 합집합) | - |
| 중복 hash 그룹 | 0 |

## generation capability

generator 가 암묵적으로 전제하던 조건을 명시적으로 계산한 값이다. 증명할 수 없으면 `no` 가 아니라 `unknown` 이다.

| capability | 값 | 뜻 |
|---|---|---|
| `parts_separable` | `no` | 조합할 파츠가 개별 주소로 존재하는가 |
| `shared_canvas` | `yes` | 합성 대상 이미지가 한 캔버스를 쓰는가 |
| `pre_aligned` | `unknown` | 파츠가 사전 정렬되어 alpha-over 만으로 합성되는가 |
| `shared_origin` | `unknown` | 파츠가 원점을 공유하는가 |
| `animation_compatible` | `unknown` | 모든 파츠가 같은 애니메이션 집합을 갖는가 |
| `directional` | `unknown` | 방향 변형이 있는가 |
| `composable` | `no` | **modular composition 이 가능한가** (위 셋의 곱) |
| `origin_policy` | `unknown` | pivot 의 근거. 자동 검출은 하지 않는다 |

### generation_mode: `composed_sheet`

완성 캐릭터 시트다. 파츠 교체 불가 — compose.py 입력이 아니다.

```
generation_mode: composed_sheet
reason: composed_sheets_only
```

파츠가 없고 완성 캐릭터 시트만 있다. `compose.py` 는 modular composition 전용 엔진이라 이 팩을 받으면 `UnsupportedModeError` 로 즉시 멈춘다 — 실패가 아니라 명시적 SKIP 이다. 이미 합성된 시트를 통과시키기 위한 예외 코드는 넣지 않는다.

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
| `composed_character` | 23 | 캐릭터 전체가 그려진 완성 이미지 |
| `environment_tile` | 0 | 타일 격자 기반 환경/타일셋 이미지 |
| `prop` | 0 | 단품 오브젝트 이미지 |
| `animation_frame` | 0 | 시퀀스의 한 프레임이지만 파츠 의미는 미확정 |
| `spritesheet` | 0 | 격자는 확인됐으나 내용 미상 |
| `source_document` | 1 | 라이선스/README/레이어 소스 등 비이미지 |
| `unknown` | 0 | 판단 불가 — 추측하지 않고 남겨둔 것 |
| **합계** | **24** | |

`character_part` 만 조합(generation) 후보다. 나머지는 카탈로그에 기록만 된다.

### packaging (sheet / individual / sequence)

| packaging | 이미지 수 |
|---|---:|
| `individual` | 23 |

## 발견된 파츠 (조합 가능)

**없음.** 이 팩에서는 조합 가능한 modular character part 를 하나도 찾지 못했다. generation 규칙을 쓸 수 있는 소재가 없다는 뜻이다.

## 분포

### category (body part 어휘 전용)

| category | 이미지 수 |
|---|---:|
| `unknown` | 23 |

### direction

| direction | 이미지 수 |
|---|---:|
| `unknown` | 23 |

### side

| side | 이미지 수 |
|---|---:|
| `unknown` | 23 |

### 해상도

| 해상도 | 이미지 수 |
|---|---:|
| `1792x1024` | 23 |

### 파일 타입

| file_type | 파일 수 |
|---|---:|
| `image` | 23 |
| `text` | 1 |

### unknown 분류 수

| 필드 | unknown 이미지 수 |
|---|---:|
| category | 23 |
| part | 0 |
| animation | 0 |
| direction | 23 |
| side | 23 |

## naming anomaly / 잠재 문제

- **파츠로 확정하지 않은 이미지 23장 (character_part 후보에서 제외)**
  - `FREE Character HD Survivor W Bike`

## 중복 hash

없음.

## 파이프라인 적용 시 주의

- **조합 가능한 character part 가 0개다.** 이 팩은 현재 generator 의 입력이 될 수 없다. character_part 는 (신체 파츠 어휘 확정 + 검증된 프레임 시퀀스) 두 조건을 모두 만족해야 하는데 하나도 만족하지 못했다.
- 완성된 캐릭터 이미지 23장이 섞여 있다. 조합 소스가 아니라 참조용이므로 generator 후보에서 제외된다.

## variation 생성 가능성

| 축 | 필요한 것 | 이 팩 | 판정 |
|---|---|---:|---|
| character variation | 조합 가능한 character_part | 0종 | **불가** |
| environment variation | 개별 주소를 가진 prop | 0개 | **불가** |
