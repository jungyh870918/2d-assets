# LPC Phase 1 subset — 선택 기준과 결과

자동 생성됨: `tools/ingest_lpc_subset.py`. 손으로 고치지 않는다.

- 원본 저장소: https://github.com/LiberatedPixelCup/Universal-LPC-Spritesheet-Character-Generator
- 팩 폴더: `01_SOURCE/characters/lpc_ulpc-generator_phase1`
- body type: **male** 한 종류
- 애니메이션: `idle`, `run`, `walk`
- 논리 셀: **64x64** (팩 상수. 자동 격자 검출을 하지 않는다)
- 방향 행 순서: `north`, `west`, `south`, `east`

## 선택 기준

사람이 파일명을 보고 고르지 않는다. 아래 기준을 순서대로 적용하고, 통과한 후보를 **정의 파일 경로순**으로 정렬해 앞에서 취한다.

1. type_name 이 이 저장소의 슬롯(body/head/hair/torso/legs/feet)에 대응한다
2. layer_ 키가 정확히 1개다 (다중 zPos 아이템은 Phase 1 에서 제외)
3. layer_1 에 male 경로가 있다 (body type 은 male 하나만 사용)
4. custom_animation 이 없다
5. animations 가 idle/walk/run 을 모두 포함한다
6. idle/walk/run 시트가 <base><animation>.png 형태로 실재한다
7. 세 시트 모두 표준 64px 격자 규격이다 (idle 2x4 / walk 9x4 / run 8x4)
8. 실제 사용 경로의 credits 가 전부 CC0 / OGA-BY / CC-BY 중 하나를 제공한다
9. 위를 만족하는 후보를 정의 파일 경로순으로 정렬해 슬롯별 목표 수만큼 앞에서 취한다
10. multi_layer: layer_ 키가 2개 이상이고 각 레이어가 제 zPos 를 갖는다
11. multi_layer: Phase 1 슬롯에 매핑되고 idle/walk/run 을 모두 지원한다
12. animation_subset: layer_ 가 1개이고 idle/walk/run 중 일부만 지원한다
13. animation_subset: 최소 1개는 지원하고 최소 1개는 미지원이어야 한다
14. animation_subset: body 슬롯은 제외한다 — 몸통이 숨겨지면 '해당 레이어만 사라지고 나머지는 계속 재생' 을 검증할 수 없다
15. 공통: male 경로 · custom_animation 없음 · 표준 64px 격자 · 허용 라이선스
16. 공통: 조건을 만족하는 후보를 정의 파일 경로순으로 정렬해 앞에서 취한다

## 선택 결과

| slot | 목표 | 후보 | 선택된 asset | zPos | selected license |
|---|---:|---:|---|---:|---|
| `body` | 1 | 1 | `body` (Body Color) | 10 | `OGA-BY 3.0` |
| `feet` | 3 | 9 | `feet_boots_basic` (Basic Boots) | 25 | `OGA-BY 3.0` |
| `feet` | 3 | 9 | `feet_boots_fold` (Folded Rim Boots) | 25 | `OGA-BY 3.0+` |
| `feet` | 3 | 9 | `feet_boots_revised` (Revised Boots) | 25 | `OGA-BY 3.0` |
| `hair` | 4 | 37 | `hair_afro` (Afro) | 120 | `CC0` |
| `hair` | 4 | 37 | `hair_cornrows` (Cornrows) | 120 | `CC0` |
| `hair` | 4 | 37 | `hair_dreadlocks_long` (Dreadlocks long) | 120 | `CC0` |
| `hair` | 4 | 37 | `hair_dreadlocks_short` (Dreadlocks short) | 120 | `CC0` |
| `hair` | 4 | 37 | `hair_braid` (Braid) | 120 | `OGA-BY 3.0` |
| `head` | 2 | 25 | `heads_boarman` (Boarman) | 100 | `CC-BY 3.0` |
| `head` | 2 | 25 | `heads_wartotaur` (Wartotaur) | 100 | `OGA-BY 3.0` |
| `legs` | 3 | 12 | `legs_hose` (Hose) | 20 | `OGA-BY 3.0` |
| `legs` | 3 | 12 | `legs_leggings` (Leggings) | 20 | `OGA-BY 3.0` |
| `legs` | 3 | 12 | `legs_leggings2` (Leggings 2) | 20 | `OGA-BY 3.0` |
| `legs` | 3 | 12 | `legs_armour` (Armour) | 20 | `OGA-BY 3.0` |
| `torso` | 4 | 21 | `torso_clothes_longsleeve` (Longsleeve) | 35 | `OGA-BY 3.0` |
| `torso` | 4 | 21 | `torso_clothes_longsleeve2` (Longsleeve 2) | 35 | `OGA-BY 3.0` |
| `torso` | 4 | 21 | `torso_clothes_longsleeve2_buttoned` (Longsleeve 2 Buttoned) | 35 | `OGA-BY 3.0` |
| `torso` | 4 | 21 | `torso_clothes_longsleeve2_cardigan` (Cardigan) | 35 | `OGA-BY 3.0` |

## 제외 사유별 정의 수

| 사유 | 수 |
|---|---:|
| `animation_subset` | 11 |
| `license_not_permissive` | 35 |
| `multi_layer` | 26 |
| `no_male_body_type` | 28 |
| `nonstandard_topology` | 1 |
| `sheet_missing` | 1 |

`license_not_permissive` 는 CC-BY-SA / GPL 만 제공하는 asset 이다. Phase 1 은 share-alike 를 배제한다.

## 라이선스 선택 정책

다중 라이선스 asset 은 **CC0 > OGA-BY > CC-BY** 순으로 하나를 명시적으로 고르고, 고르지 못하면 제외한다. 고른 값과 나머지 선택지를 둘 다 기록한다.
