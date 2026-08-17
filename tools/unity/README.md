# Unity 쪽 스크립트

`06_UNITY_EXPORT/characters/<profile>/manifest.json` 을 읽어 Unity 에셋으로 만드는
최소 임포터. 이 두 파일이 전부다.

| 파일 | Unity 프로젝트에서의 위치 | 역할 |
|---|---|---|
| `GeneratedCharacter.cs` | `Assets/Scripts/` (아무 데나, Editor 폴더만 아니면 됨) | 조합 정의 + 스프라이트 참조를 담는 ScriptableObject |
| `GeneratedCharacterImporter.cs` | `Assets/Editor/` (**반드시** Editor 폴더) | manifest 읽기 → 텍스처 설정/슬라이스 → 에셋 생성 |

`GeneratedCharacterImporter.cs` 는 `UnityEditor` 를 참조하므로 `Editor/` 폴더 밖에
두면 빌드가 깨진다.

## 순서

1. `06_UNITY_EXPORT/characters/<profile>/` 폴더를 Unity 프로젝트 `Assets/` 아래로 복사
2. 위 표대로 두 스크립트를 배치
3. 메뉴 **2D Art Factory > Import Generated Characters** → 복사한 폴더의 `manifest.json` 선택

임포터가 하는 일:

- `import_settings` 대로 텍스처 설정 적용 (PPU / filter / compression / mesh type / pivot)
- `preview.png` → Sprite Mode **Single**
- `sheet_<anim>.png` → Sprite Mode **Multiple**, `cell_width` 폭으로 가로 슬라이스,
  스프라이트 이름은 `<seed>_<anim>_<프레임2자리>`
- 캐릭터마다 `character_<seed>.asset` (`GeneratedCharacter`) 생성 + 스프라이트 연결

## 여기서 하지 않는 것

Animator / AnimationClip 생성, Addressables 등록, prefab factory,
Sprite Library 구성 — 아직 만들지 않는다. 임포터는 위 세 가지에서 멈춘다.

## Sprite Library 설계 입력 (실측값, 아직 구현 안 함)

두 번째·세 번째 팩을 재면서 확인된 것만 적는다. 추정은 넣지 않는다.

### 1. baked sheet 중복은 현재 규모에서 손해가 아니다

| | 프레임 수 |
|---|---:|
| 지금 방식 (캐릭터마다 idle+walk 굽기) | 20명 × 14 = **280** |
| 파츠 공유 방식 (파츠별 프레임 1벌) | 36파츠 × 14 = **504** |

**손익분기는 약 36명**이다. 그 아래에서는 굽는 쪽이 프레임 수가 적다.
"baked sheet 는 중복이라 무조건 낭비"라는 통념이 이 팩·이 규모에서는 성립하지 않는다.
Sprite Library 의 실제 근거는 용량이 아니라 **런타임 교체 가능성**이어야 한다.
(면적 비교는 원본 2048px 과 축소본 256px 을 섞어 재게 되므로 성립하지 않아 넣지 않았다.)

### 2. direction 이 1급 축이어야 한다

CC0 팩은 방향 변형이 없고, HD Survivor 는 **행(row)에 방향 8개**가 들어 있다.
현재 export 의 스프라이트 좌표계는 `(animation, frame)` 뿐이라 방향을 표현할 수 없다.
Sprite Resolver 의 category/label 은 최소 `(animation, direction, frame)` 이어야 한다.

### 3. pivot 은 팩마다 근거가 다르다

| 팩 | 원점의 근거 |
|---|---|
| CC0 | 전 파츠가 같은 2048 캔버스에 사전 정렬 → 캔버스 자체가 원점 |
| HD Survivor | 128px 셀 안 고정 위치 (발끝 y 중앙값 90/128, 표준편차 3.4px) |

지금은 규칙 파일의 `unity.pivot` 상수 하나로 처리한다. 팩별 원점 근거가 다르므로
**pivot 을 팩 metadata 로 내려야** 한다.

### 4. 완성 시트 전용 팩은 Sprite Library 대상이 아니다

`generation_mode: composed_sheet` 인 팩은
파츠 교체 자체가 불가능하다. Sprite Library 가 아니라 일반 Animator + 시트 경로로
가야 하므로, export 층은 **두 모드**를 갖게 된다. 한 모드로 통일하려 하면 안 된다.

## 메모

- 시트 슬라이스에 쓰는 `TextureImporter.spritesheet` / `SpriteMetaData` 는 Unity 2021+
  에서 deprecated 지만 여전히 동작한다. 임포터를 최소로 유지하려고 신형
  `SpriteDataProviderFactories` 대신 이걸 쓴다. 나중에 Unity 가 완전히 제거하면
  `ConfigureSheet` 한 곳만 고치면 된다.
- `manifest.json` 의 `parts` / `palette.groups` 가 dictionary 가 아니라 배열인 이유는
  Unity 의 `JsonUtility` 가 dictionary 를 역직렬화하지 못하기 때문이다.
  정본(dictionary 형태)은 각 캐릭터 폴더의 `character.json` 에 그대로 있다.
