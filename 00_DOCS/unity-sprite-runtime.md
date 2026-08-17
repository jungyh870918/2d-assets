# Unity sprite runtime architecture

파이프라인이 만든 deterministic `character.json` 이 Unity 에서 **재사용 가능한 런타임
외형**으로 어떻게 동작하는지. Sprite Library / Resolver POC 의 설계 문서다.

기존 baked export 는 **대체되지 않았다.** 두 경로가 공존한다.

---

## 1. 데이터 흐름

```
                        01_SOURCE  (읽기 전용 원본)
                            │  scan / adapter
                            ▼
                        02_CATALOG  parts[slot][asset].animations[anim]
                            │        · frame 파일 목록  (CC0)
                            │        · sheet + cell + directions  (LPC)
                            │  rule + seed  (결정적)
                            ▼
              05_GENERATED  character.json   ← **source of truth**
                            │
              ┌─────────────┴──────────────┐
              │                            │
   export_unity.py                export_unity_runtime.py
   (baked, 기존)                   (resolver, 이번 단계)
              │                            │
              ▼                            ▼
  06_UNITY_EXPORT/characters/   06_UNITY_EXPORT/runtime/<profile>/
    캐릭터마다 합성 시트            parts/<slot>/<asset>/<anim>[_<dir>].png
    manifest.json                  runtime_manifest.json
              │                            │
              ▼                            ▼
  GeneratedCharacterImporter     SpriteLibraryBuilder  (Unity Editor)
              │                            │
              ▼                            ▼
   GeneratedCharacter            SpriteLibraryAsset  (appearance 마다 1개)
   (구운 스프라이트 참조)          CharacterAppearance (ScriptableObject)
                                 프리팹: 슬롯마다 SpriteRenderer + SpriteResolver
                                          │
                                          ▼
                              Animator  ──►  CharacterView.SetState()
                                          │   (animation / direction / frame)
                                          ▼
                                   SpriteResolver  ──►  현재 스프라이트
                                          │
                                          ▼
                                   Rendered Character
```

`06_UNITY_EXPORT/runtime/<profile>/` 은 아직 Factory 안이다. 실제 게임으로는
`export_consumer_package.py` 가 복사해 넘기고, 그 경계의 소유권 규칙이
`export-contract-v1.md` 다.

### composed_sheet 경로는 어디서 갈리는가

```
02_CATALOG  pack.capabilities.generation_mode
    │
    ├── "modular_composition"  → compose.py → character.json → 위 두 경로
    │      CC0 · LPC
    │
    ├── "composed_sheet"       → compose.py 입력이 **아님** (UnsupportedModeError)
    │      HD Survivor              Unity 에서는 Animator + 시트 슬라이싱 경로
    │                               파츠 교체 불가 → Sprite Library 대상 아님
    │
    └── "unsupported"          → 캐릭터 생성 대상 아님
           Modern Interiors
```

분기는 **카탈로그 capability 단계**에서 일어난다. Unity 쪽에서 분기하지 않는다.
`runtime_manifest.json` 의 `runtime_mode` 가 그 결정을 그대로 실어 나른다.

---

## 2. 논리 모델: 두 ecosystem 이 공통으로 제공하는 축

| 논리 축 | CC0 (RGS_Dev) | LPC (ULPC) |
|---|---|---|
| character definition | `character.json` | `character.json` (동일) |
| slot | 규칙의 slot 이름 (`hair`, `wing_l`) | adapter 가 `type_name` 매핑 (`torso`, `feet`) |
| selected asset | `parts[slot]` = `hair2` | `parts[slot]` = `hair_afro` |
| animation | 파일명 `<anim>_<n>.png` | 정의의 `animations` 목록 |
| direction | **없음** (`unknown`) | 시트의 **행** 4개 |
| frame | 파일 1개 = 프레임 1개 | 시트의 **열** |
| origin policy | `shared_canvas` (2048 캔버스 공유) | `logical_cell` (64×64 셀) |
| z-order | 규칙의 `layer_order` (실측으로 정함) | 소스가 `zPos` **선언** |
| palette metadata | 규칙의 palette 그룹 + ramp | 정의의 `recolors` (material/palettes) |
| provenance | 팩 단위 라이선스 기록 | **파일 단위** `CREDITS.csv` |
| license/attribution | CC0 — 표기 불필요 | OGA-BY / CC-BY / CC0 — **표기 필수** |

이 표가 Sprite Library 설계의 입력이다. 특정 팩 구조가 아니라 이 논리 모델 위에 얹는다.

---

## 3. Sprite Library 를 쓰는 이유

**용량이 아니다.** 실측으로 확인했다 (§7 표). 이유는 다음으로 한정한다.

1. 런타임 외형 교체
2. 애니메이션 재사용 (여러 외형이 같은 AnimationClip 공유)
3. character definition 과 visual asset 분리
4. NPC variation 을 정의 데이터로 표현
5. 생성 텍스처 수 폭증 방지 (캐릭터 수가 커질 때)

이 목적을 만족하지 못하면 baked 경로를 유지하는 것도 유효한 선택이다.

---

## 4. Sprite Library 매핑

```
category = 정규 슬롯 이름            body · head · hair · torso · legs · feet · ...
label    = "<animation>__<direction>__<frame:02d>"     방향 있는 팩
           "<animation>__<frame:02d>"                  방향 없는 팩
library  = appearance 1개당 SpriteLibraryAsset 1개
```

### 왜 이 매핑인가

§8 의 세 안 중 **A 변형**을 골랐다. 판단 기준은 "Unity 기능이 가장 잘하는 축이 무엇인가"다.

- Sprite Library 가 잘하는 것: **같은 이름에 다른 스프라이트를 매다는 것**
- Animator 가 잘하는 것: **시간에 따라 상태를 바꾸는 것**

category/label 이름을 appearance 마다 **동일하게** 두면, 외형 교체가
`SpriteLibraryAsset` 교체 한 줄로 끝나고 AnimationClip 은 손대지 않는다.
반대로 label 에 asset 이름을 넣으면 (Option A 원안) appearance 마다 label 이 달라져
clip 을 공유할 수 없다. asset 이름은 label 이 아니라 **어느 라이브러리에 들어 있는가**로
표현된다.

Option C(라이브러리는 외형만, 프레임은 별도 테이블)는 지금 구조에서 Resolver 를
쓰지 않게 되어 Sprite Library 의 이점이 사라진다.

### 프리팹 구조는 프로파일 단위다

프리팹은 **프로파일 전체 슬롯**으로 만든다. appearance 마다가 아니다.

CC0 는 `horn` / `weapon` / `wing_l` 이 선택 슬롯이라 캐릭터마다 슬롯 집합이 다르다.
프리팹을 appearance 별 슬롯으로 만들면 구조가 캐릭터마다 달라져 clip 공유가 깨진다.
그래서 프리팹은 항상 전체 슬롯을 갖고, 안 쓰는 슬롯은 라이브러리에 category 가 없어
스프라이트가 null → 그 레이어만 숨는다.

이 POC 를 짜면서 실제로 이 문제로 테스트가 깨졌고, 그래서 고쳤다.

---

## 5. 책임 분리

```
CharacterAppearance   어떤 파츠를 입었는가          (frame 을 저장하지 않는다)
        │
Animator              지금 어떤 animation/direction/frame 인가
        │
CharacterView         둘을 합쳐 label 문자열을 만든다
        │
SpriteResolver        그 (category, label) 의 스프라이트를 라이브러리에서 찾는다
        │
SpriteRenderer        그린다 (sortingOrder = z-order)
```

`CharacterAppearance` 에 frame 을 두면 외형 교체 때마다 애니메이션이 리셋된다.
그게 정확히 Sprite Library 로 피하려는 문제라 **의도적으로 넣지 않았다.**

---

## 6. 정책 결정

### missing animation → `hide_layer`

파츠가 특정 애니메이션을 지원하지 않으면 그 label 이 라이브러리에 **아예 없다**.
LPC 768 정의 중 147 개가 애니메이션 서브셋만 지원하므로 실제로 발생하는 상황이다.

채택: **그 레이어만 숨기고 몸통 애니메이션은 계속 진행한다.**

- fallback sprite → 엉뚱한 포즈가 섞여 더 나쁘다
- item 사용 금지 → 조합 가능성이 크게 줄어든다
- 레이어 숨김 → 최악의 경우 장비가 잠깐 사라질 뿐, 캐릭터는 정상 동작

`CharacterView.Apply()` 가 라이브러리를 먼저 조회해 없으면 명시적으로 `sprite = null`
을 넣는다. Resolver 는 못 찾으면 직전 스프라이트를 그대로 두기 때문에, 이 처리를
Unity 내부 동작에 맡기지 않는다. (이것도 POC 테스트로 잡은 실제 버그다.)

같은 메커니즘이 "이 appearance 가 안 쓰는 슬롯"에도 그대로 적용된다.

### direction 은 애니메이션별 topology

`walk` 4방향 / `hurt` 1방향처럼 방향 수가 애니메이션마다 다르다.
전역 enum 하나로 고정하지 않고 `topology[animation].directions` 로 기록한다.
방향이 없는 팩(CC0)은 label 에서 direction 조각이 빠질 뿐 같은 코드를 탄다.

### origin / pivot

자동 검출하지 않는다. `runtime_manifest.origin` 이 팩이 선언한 값을 그대로 나른다.

| | CC0 | LPC |
|---|---|---|
| policy | `shared_canvas` | `logical_cell` |
| logical cell | — | 64×64 |
| pivot | BottomCenter | BottomCenter |
| PPU | 128 | 64 |

### multi-layer item

LPC 에 한 item 이 두 zPos 를 갖는 사례가 168개 있다 (곤봉 = 앞 140 + 뒤 9).
그래서 `CharacterAppearance.layers` 는 **배열이지 사전이 아니다** — 같은 slot 이
여러 번 나올 수 있다. Phase 1 은 단일 레이어 아이템만 쓰지만 구조가 막지 않는다.

---

## 7. baked vs resolver 실측

같은 셀 크기로 내보내 비교했다 (CC0 256px / LPC 64px). 추정이 아니라 실제 파일 계측이다.

| profile | path | textures | sprites | disk | pixels |
|---|---|---:|---:|---:|---:|
| CC0 (20명) | baked | 40 | 280 | 5,005 KB | 16.3 M |
| | resolver | **70** | **490** | **1,544 KB** | 28.5 M |
| LPC (10명) | baked | 120 | 760 | 478 KB | 3.1 M |
| | resolver | **204** | **1,292** | **267 KB** | 5.3 M |

**작은 population 에서 resolver 는 텍스처가 더 많다.** 파츠를 애니메이션·방향마다
따로 굽기 때문이다. 디스크는 반대로 작은데, 파츠 시트가 대부분 투명이라 잘 압축된다.

텍스처 수 손익분기:

- CC0: **35명** (baked 2.0 tex/명 vs resolver 70 고정)
- LPC: **17명** (baked 12.0 tex/명 vs resolver 204 고정)

메모리/런타임 오브젝트 수는 정확한 profiling 을 하지 않았다 — **추정**:
resolver 경로는 캐릭터마다 슬롯 수만큼 GameObject + SpriteRenderer + SpriteResolver 가
생기므로(CC0 13개 / LPC 6개) baked 단일 렌더러보다 오브젝트가 많다. 교체 비용은
`SpriteLibraryAsset` 참조 교체 + 슬롯 수만큼의 사전 조회이므로 프레임당이 아니라
교체 시점 1회다.

결론: **용량은 Sprite Library 도입의 근거가 되지 못한다.** 근거는 런타임 교체와
clip 공유다.

---

## 8. 재현 방법

```bash
# 1) resolver 용 export (baked 와 별개)
python3 tools/export_unity_runtime.py 04_RULES/cc0_test_population.json --cell-size 256
python3 tools/export_unity_runtime.py 04_RULES/lpc_phase1_population.json --cell-size 64
python3 tools/export_unity_runtime.py 04_RULES/lpc_phase2_showcase.json --cell-size 64

# 2) 스크래치 Unity 프로젝트 조립 + EditMode/PlayMode 테스트까지 한 번에
python3 tools/run_unity_tests.py            # --only editmode / --only playmode
```

`run_unity_tests.py` 가 임시 프로젝트를 만들고 `tools/unity/` 의 C#(런타임 4 +
에디터 2 + 테스트)과 `06_UNITY_EXPORT/runtime/` 을 복사한 뒤 테스트를 돌린다.
손으로 프로젝트를 만들 필요가 없다. PlayMode 는 EditMode 가 만든 프리팹·라이브러리를
쓰므로 **EditMode 가 먼저** 돌아야 한다 — 결함이 아니라 의도된 순서 의존성이다.

실제 게임 프로젝트에 넣을 때는 스크래치 프로젝트가 아니라 소비자 패키지를 쓴다:

```bash
python3 tools/export_consumer_package.py <소비자>/Assets --profiles <profile>
# 그 다음 에디터 메뉴: 2D Art Factory > Build Sprite Libraries
```

경계와 소유권은 `export-contract-v1.md`, 게임 쪽 정책은 `game-art-profile.md`.

Unity 프로젝트 자체는 저장소에 두지 않는다 (`Library/` 등 대용량 산출물 때문).
소스는 `tools/unity/` 에만 두고, export 결과와 조합해 언제든 재구성한다.

---

## 9. Phase 2 — AnimationClip / multi-layer / animation subset

### AnimationClip 이 담는 것: `frame` 정수 하나

```
state(Walk)   -> CharacterAnimationState.OnStateEnter -> view.SetAnimation("walk")
clip(walk)    -> CharacterView.frame = 0,1,2,...        (step 커브)
게임 로직      -> view.SetDirection("south")
                          ↓
                 label = "walk__south__03"  -> SpriteResolver
```

clip 은 외형을 **전혀** 키프레임하지 않는다. 커브가 1개(`frame`)뿐이라
같은 profile 의 모든 appearance 가 clip 을 공유하고, 외형 교체는
`SpriteLibraryAsset` 만 갈아끼우면 된다. 테스트가 이걸 강제한다
(커브 수 == 1, propertyName == "frame", path == "").

### direction 을 clip 에 넣지 않은 이유 (§4 비교 결과)

| 방식 | LPC 기준 clip 수 | 방향 예외(hurt=1방향) |
|---|---:|---|
| 방향별 clip | 3 애니메이션 × 4 방향 = **12** | 조합이 더 늘어난다 |
| **frame 만 clip, 방향은 라벨** | **3** | 라벨에서 빠질 뿐 구조 변화 없음 |

**더 작은 쪽을 골랐다.** 방향 정보는 라벨·manifest·`topology.directions` 에 그대로 남고,
`CharacterView.SetDirection()` 이 라벨을 만들 때 합친다. 2D Blend Tree 는 만들지 않았다.

### multi-layer logical item

`hair_braid` (LPC) 는 한 아이템이 zPos 두 개를 갖는다: **fg 120 / bg 9**.
body 가 10 이므로 bg 레이어는 **몸통보다 뒤**에 그려져야 한다.

```
CharacterAppearance.layers 는 배열이다 (사전이 아니다)
  hair#1  z=9    ← 같은 logical item
  body    z=10
  legs    z=20
  ...
  hair    z=120  ← 같은 logical item
```

- category 는 render layer 마다 달라야 한다 (`hair`, `hair#1`) — 같은 category 에
  넣으면 라벨이 정확히 겹쳐 서로를 덮어쓴다.
- **label 형식은 바꾸지 않았다.** appearance 간 label namespace 가 그대로라 clip 공유가 유지된다.
- `character.json` 의 선택은 여전히 `parts.hair = "hair_braid"` **하나**다.
  여러 레이어는 카탈로그가 펼치고, generator 가 z 로 재정렬한다.

`generate.layers_for()` 가 z 로 전체를 다시 정렬한다 — 슬롯 순서만으로는
"한 아이템의 뒤 레이어가 몸통보다 뒤" 를 표현할 수 없기 때문이다.

### animation subset

`legs_armour` (LPC) 는 idle/walk 만 지원하고 run 이 없다.

| 층 | 처리 |
|---|---|
| rule | `animation_policy: allow_subset` (기본은 `require_all`) |
| capability | `animation_compatible: partial` — 합성 가능성을 막지 않는다 |
| compose | 미지원 레이어만 건너뛴다 |
| runtime export | 미지원 애니메이션의 시트/라벨을 만들지 않는다 |
| Unity | 라벨이 없으니 sprite = null → 그 레이어만 숨김 |
| validator | 실패가 아니라 **경고**로 기록 |

정책은 **`hide_layer`** 하나로 통일했다. 생성 단계와 런타임이 같은 규칙을 쓴다.
required 슬롯이라도 그 애니메이션을 지원하는 후보가 하나도 없으면 여전히 오류다.

사람 확인용:
[lpc_phase2_multilayer.png](../05_GENERATED/reports/lpc_phase2_multilayer.png) ·
[lpc_phase2_subset.png](../05_GENERATED/reports/lpc_phase2_subset.png)

### runtime topology (§17)

| profile | appearance | slots/renderer/resolver | clips | controller | libraries |
|---|---:|---:|---:|---:|---:|
| cc0_test_population | 2 | 11 | 2 | 1 | 2 |
| lpc_phase1_population | 2 | 6 | 3 | 1 | 2 |
| lpc_phase2_showcase | 2 | **7** (logical 6) | 3 | 1 | 2 |

Phase 2 는 logical item 6개가 render layer 7개를 만든다 — multi-layer 하나 때문이다.
prefab GameObject = 루트 1 + 슬롯 수.

## 10. 아직 하지 않은 것

- Sprite Library 를 **모든** 캐릭터에 적용 (POC 는 프로파일당 2명으로 검증)
- multi-layer **weapon** (앞/뒤 무기). 검증한 것은 hair 계열 1종이다
- animation subset 자산 1종 외의 나머지 (LPC 에 147개)
- ramp palette / multiply tint 런타임
- composed_sheet 런타임 (HD Survivor)
- Addressables / AssetBundle
- 런타임 장비 교체 시스템
