# 가용 능력 — 지금 무엇을 시킬 수 있는가

자동 생성됨: `python3 tools/capability_sheet.py`. 손으로 고치지 않는다.

여기 있는 값은 전부 스캐너와 라이선스 기록이 **이미 계산한 사실**이다.
좋다/나쁘다는 판정은 없다 — 무엇이 가능한지만 적는다.

## 팩

| 팩 | 도메인 | generation_mode | composable | 셀 | 슬롯 | 조합 상한 |
|---|---|---|---|---|---:|---:|
| `limezu_modern-interiors-free_v2.2` | environments | unsupported | **no** | — | 0 | — |
| `lpc_ulpc-generator_phase1` | characters | modular_composition | yes | 64×64 | 6 | 480 |
| `rgsdev_free-cc0-modular-vector-characters_v1` | characters | modular_composition | yes | — | 10 | 60,480 |
| `unknown_free-hd-survivor-w-bike_v1` | characters | composed_sheet | **no** | — | 0 | — |

`composable: no` 인 팩은 규칙을 써도 조합이 되지 않는다. 이유는 각 팩 절에 적혀 있다.

### `limezu_modern-interiors-free_v2.2`

> 이 팩은 **조합 대상이 아니다** (`composable: no`, `generation_mode: unsupported`). 발주 대상에서 제외한다.

모듈 슬롯 없음 — 파츠가 분리되지 않는다.

| 축 | 값 |
|---|---|
| 애니메이션 | unknown |
| 방향 | unknown |
| animation_compatible | unknown |
| origin_policy | unknown |

**라이선스**

| license | commercial_use | pipeline_approved | commercial_release_eligible |
|---|---|---|---|
| `LimeZu Free Version License (proprietary)` | **no** | yes | **false** |

> ⛔ 이 팩에서 나온 결과물은 **상업 출시 대상이 아니다.** 생성은 막지 않지만 신호는 산출물까지 따라간다.

### `lpc_ulpc-generator_phase1`

**슬롯별 후보**

| body | feet | hair | head | legs | torso |
|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 5 | 2 | 4 | 4 |

파츠 19개 · 제약 없이 곱하면 **480 조합**.
이 카탈로그는 팩 전체가 아니라 **선별된 subset** 이다 (기준은 카탈로그의 `subset.criteria`).

| 축 | 값 |
|---|---|
| 애니메이션 | `idle` · `run` · `walk` |
| 방향 | 4개 — east · north · south · west |
| animation_compatible | partial |
| origin_policy | logical_cell |

**라이선스**

| license | commercial_use | pipeline_approved | commercial_release_eligible |
|---|---|---|---|
| `per-asset (OGA-BY 3.0 / CC-BY 3.0 / CC0-1.0)` | yes | yes | **true** |

### `rgsdev_free-cc0-modular-vector-characters_v1`

**슬롯별 후보**

| body | eyes | foot | hair | hand | head | horn | mouth | weapon | wing |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7 | 2 | 3 | 2 | 3 | 5 | 8 | 3 | 2 |

파츠 36개 · 제약 없이 곱하면 **60,480 조합**.

| 축 | 값 |
|---|---|
| 애니메이션 | `death` · `fall` · `hit` · `idle` · `jumpEnd` · `jumpStart` · `roll` · `walk` |
| 방향 | unknown |
| animation_compatible | yes |
| origin_policy | shared_canvas |

**라이선스**

| license | commercial_use | pipeline_approved | commercial_release_eligible |
|---|---|---|---|
| `CC0-1.0` | yes | yes | **true** |

### `unknown_free-hd-survivor-w-bike_v1`

> 이 팩은 **조합 대상이 아니다** (`composable: no`, `generation_mode: composed_sheet`). 발주 대상에서 제외한다.

모듈 슬롯 없음 — 파츠가 분리되지 않는다.

| 축 | 값 |
|---|---|
| 애니메이션 | unknown |
| 방향 | unknown |
| animation_compatible | unknown |
| origin_policy | unknown |

**라이선스**

| license | commercial_use | pipeline_approved | commercial_release_eligible |
|---|---|---|---|
| `unknown` | unknown | **no** | **false** |

> ⛔ 이 팩에서 나온 결과물은 **상업 출시 대상이 아니다.** 생성은 막지 않지만 신호는 산출물까지 따라간다.

## 팔레트

| 파일 | 램프 | 그룹 | 램프 길이 |
|---|---:|---|---:|
| `03_PALETTES/_example_korean_90s.json` (예시) | 4 | unknown 4 | 5 |
| `03_PALETTES/cc0_creature.json` | 18 | hair 6 · skin 6 · weapon 3 · wing 3 | 5 |

팔레트는 팩에 묶여 있지 않다. 규칙이 골라 쓴다.

## 이미 있는 규칙

| 규칙 | 프로파일 | 팩 | seed | 애니메이션 | 성격 | 소비자 |
|---|---|---|---|---|---|---|
| `cc0_test_population.json` | `cc0_test_population` | `rgsdev_free-cc0-modular-vector-characters_v1` | 1001–1010 · 1011–1020 | idle · walk · roll · fall · hit · jumpStart · jumpEnd · death | self_verification | unknown |
| `lpc_phase1_population.json` | `lpc_phase1_population` | `lpc_ulpc-generator_phase1` | 4001–4010 | idle · walk · run | self_verification | unknown |
| `lpc_phase2_showcase.json` | `lpc_phase2_showcase` | `lpc_ulpc-generator_phase1` | 4101–4102 | idle · walk · run | self_verification | unknown |

`성격` 은 이 산출물이 자체 기술 검증인지 발주 대응인지를 뜻한다 (`04_RULES/<규칙>.json` 의 `order.purpose`). `unknown` 은 규칙이 아직 선언하지 않았다는 뜻이고, 그 자체로 정당한 값이다.
