# Game Art Profile — 게임별 art policy 경계

Export Contract v1 이 "Factory 산출물이 소비자에서 안 깨지는가" 였다면,
이 문서는 그 다음 질문이다: **"이 게임은 Factory 가 주는 것 중 무엇을 쓰는가."**

측정 대상: `/Users/daniel/Desktop/Projects/game-sandbox` 의 20 NPC sandbox.

---

## 1. 두 profile

| | CharacterProfile | GameArtProfile |
|---|---|---|
| 질문 | 이 Factory runtime profile 을 Unity 에서 **어떻게 실행**하는가 | 이 게임에서는 그중 **무엇을 쓸** 것인가 |
| 소유 | Factory (`SpriteLibraryBuilder` 가 생성) | 게임 (`Assets/Game/**`) |
| 위치 | `Assets/ArtFactory/Profiles/<p>/Generated/` | `Assets/Game/Art/Profiles/SandboxNpcTest.asset` |
| 내용 | prefab · appearances · AnimatorController · motion 매핑 · direction 축 · topology | 허용 외형 · 허용 동작 · population 정책 |
| exporter | 갱신한다 | **모른다** |

Factory 는 게임의 art policy 를 만들지도, 덮어쓰지도, 읽지도 않는다.
반대로 게임은 라벨 규약 · Animator 파라미터 이름 · 시트 좌표 · 소스 경로를 모른다.

## 2. GameArtProfile 이 실제로 들고 있는 것

sandbox 에 **실제로 필요해서** 넣은 것만 있다.

```csharp
string                   id                 // "sandbox_npc_test"
CharacterProfile         characterProfile   // 실제 오브젝트 참조 (경로/id 아님)
CharacterAppearance[]    allowedAppearances // Factory 가 주는 것의 부분집합
string[]                 allowedMotions     // { "idle", "walk" } — run 은 안 쓴다
int                      populationSeed     // 12345
int                      npcCount           // 20
string                   initialMotion      // "walk"
InitialDirectionPolicy   directionPolicy    // DeterministicPerNpc | Fixed
string                   fixedDirection     // Fixed 일 때만
```

**spawn area 는 여기 없다.** 그건 art policy 가 아니라 씬 geometry 라서
`SandboxBootstrap` (씬 컴포넌트)이 들고 있다. 하나의 schema 에 억지로 합치지 않는다.

## 3. 게임 코드에서의 쓰임

```csharp
spawner.SetArtProfile(artProfile);
spawner.SpawnPopulation(areaSize, transform);      // seed/수는 policy 가 안다
```

spawner 내부에서만 이렇게 연결된다:

```
GameArtProfile → characterProfile → allowedAppearances[i] → prefab/library
```

동작 지정은 여전히 Factory 의 공개 API 다:

```csharp
characterProfile.SetMotion(animator, npc.motion);   // 이름만 넘긴다
```

## 4. 외형 선택

```
appearance = allowedAppearances[ FNV1a(populationSeed, npcIndex, "appearance")
                                 % allowedAppearanceCount ]
```

(구현은 `NpcPopulationFactory` — 아래 7절)

- 색인은 **허용 목록** 기준이다. `CharacterProfile.appearances` 를 보지 않는다.
- 기존 sandbox 의 FNV-1a 스트림을 그대로 쓴다. 새 난수 프레임워크를 만들지 않았다.
- weight 는 만들지 않았다. 지금 필요한 것은 균등 선택이고, 필요해지면 그때 넣는다.
- `UnityEngine.Random` · seed 없는 `System.Random` · `DateTime.Now` · `Guid.NewGuid` 없음.

## 5. validation

`GameArtProfile.Validate(out errors, out warnings)` 가 보는 것:

1. `characterProfile` 참조 존재
2. `allowedAppearances` 비어 있지 않음 · null 원소 없음
3. 모든 허용 외형이 `characterProfile.Contains()` 를 통과 — **stale 검출**
4. 중복 외형 · 중복 동작
5. 모든 허용 동작이 `characterProfile.HasAnimation()` 을 통과
6. `npcCount > 0`, `initialMotion ∈ allowedMotions`
7. `Fixed` 정책이면 `fixedDirection` 이 profile 의 방향 중 하나

경고(에러 아님): 우리가 참조하지 않는 stale 잔재가 profile 에 남아 있는 경우.

실패하면 `CharacterSpawner` 는 **NPC 를 하나도 만들지 않는다.**
자동 대체·fallback·migration 은 없다. Export Contract v1 의 stale 정책과 같은 태도다.

## 6. 실측

| 검사 | 결과 |
|---|---|
| 같은 policy + seed 12345 두 번 | population 동일 (외형/방향/동작/속도/waypoint) |
| seed 12346 | 달라짐 |
| Factory 2 외형 · policy 1 허용 | 20 NPC 전원이 그 1개만 사용 |
| spawn 후 실제 `CharacterView.Appearance` | 전원 허용 목록 안 |
| stale 외형 참조 policy | `Validate` 실패 · 메시지에 이름과 `stale` 명시 · 자동 대체 없음 · spawn 0명 |
| 없는 동작 `backflip` | `Validate` 실패 · `initialMotion` 그대로 (대체 없음) |
| Factory 재-export | `Assets/Game/**` 바이트 변화 0 · art profile GUID 유지 · 참조 유지 |

## 7. population 경계 (Step 5)

정책에서 NPC 집단을 정하는 일과, 그것을 씬에 세우는 일을 나눴다.

```
GameArtProfile + seed + count
        ↓  NpcPopulationFactory.Generate()      순수 결정 함수
NpcDefinition[]  { index, appearance, motion, direction }
        ↓  CharacterSpawner.Spawn()             씬 생성
GameObject[]
```

`Generate()` 는 Unity 씬 오브젝트를 만들지도 만지지도 않는다 —
Instantiate · Transform · Animator · SpriteResolver 모두 없다.
그래서 "같은 seed 면 같은 집단인가" 를 씬 없이 확인할 수 있고, 그게 이 분리의 이유다.

**위치·속도·waypoint 는 definition 에 없다.** 그건 씬 크기에 의존하는 배치라서
`NpcPlacement` 가 따로 만든다. 같은 집단을 다른 크기의 씬에 세울 수 있어야 한다.

결정 축마다 태그가 다르다 (`"appearance"`, `"direction"`, 배치 쪽은 `"x"`/`"y"`/
`"speed"`/`"waypoints"`). 전역 RNG 를 순차 소비하지 않으므로 허용 외형을 하나 늘려도
방향은 그대로다 — 실측으로 확인했다(외형 10/20 변화, 방향 변화 0).

동작은 전원 `initialMotion` 이다. sandbox 가 요구하지 않는 무작위화를 넣지 않았다.

`NpcPopulationFactory.Fingerprint()` 는 회귀·디버그용 sha256 이다
(`index|appearanceSeed|motion|direction` 줄들). 런타임 identity 가 아니고 저장 포맷도
아니다. 현재 값: `8ca2a408a3449a5f1951360ed99cc85f091344c62b6c9085476a20f57e97637f`
(seed 12345, 20명) — 독립적으로 빌드한 격리 사본에서도 같은 값이 나온다.

파일: `Assets/Game/Population/` (`NpcDefinition` · `NpcPopulationFactory` ·
`NpcPlacement` · `DeterministicHash`). 전부 game-owned 다.

## 8. 이번 단계에서 일부러 만들지 않은 것

범용 art profile DSL · YAML schema · 게임 간 상속 · role taxonomy(student/teacher/…) ·
직업/성별/연령/희귀도 · 장비 · palette 런타임 · weight 시스템 · migration · save id ·
population 저장 포맷(JSON/YAML) · population 편집 도구 · Addressables/AssetBundle/UPM.

필요해진 시점에 만든다. 지금 sandbox 가 요구하지 않는다.
