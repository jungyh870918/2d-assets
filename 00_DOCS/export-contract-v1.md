# Export Contract v1

Factory 와 소비자 게임 프로젝트 사이의 경계를 고정한다.
`contract_version: "1.0"` 은 `Assets/<package>/export_manifest.json` 에 박혀 나간다.

측정 대상 소비자: `/Users/daniel/Desktop/Projects/game-sandbox` (Factory 저장소를 참조하지 않는 별도 Unity 프로젝트).

---

## 1. 소유권 경계

패키지 안의 모든 파일은 셋 중 하나에 속한다. **exporter 는 자기 것만 건드린다.**

| 소유자 | 경로 | exporter 의 행동 |
|---|---|---|
| Factory | `<pkg>/Runtime/`, `<pkg>/Editor/`, `<pkg>/Profiles/<p>/runtime_manifest.json`, `<pkg>/Profiles/<p>/ATTRIBUTION.md`, `<pkg>/Profiles/<p>/parts/` | 덮어쓴다. 더 이상 내보내지 않는 파일은 짝 `.meta` 와 함께 지운다 |
| 소비자 | `<pkg>/Profiles/<p>/Generated/`, 모든 `.meta` | **절대 지우지 않는다** |
| 게임 | `Assets/Game/**` | 존재조차 모른다 |

`.meta` 가 소비자 소유인 이유는 그 안에 GUID 가 들어 있기 때문이다.
`.meta` 를 지우면 Unity 가 새 GUID 를 발급하고, 그 에셋을 참조하던 게임 쪽
직렬화 참조(scene, prefab, ScriptableObject)가 전부 `Missing` 이 된다.

이전 구현은 export 마다 `shutil.rmtree(pkg_root)` 를 했다. 그건 `Generated/` 와
`.meta` 를 통째로 날리는 것이므로 Contract v1 에서 제거했다.

## 2. 정체성 (identity)

`export_manifest.json`:

```json
{
  "contract_version": "1.0",
  "profiles": ["lpc_phase2_showcase"],
  "content_fingerprint": "<sha256>",
  "file_count": 101
}
```

(`file_count` 는 내보낸 프로파일과 외형 수에 따라 달라진다. 위 값은 예시다.)

`content_fingerprint` 는 **Factory 소유 파일만**의 해시다.
`Generated/` · `.meta` · `README.md` · 자기 자신은 제외한다.

- 시각(`DateTime.Now`, mtime)도 랜덤 UUID 도 쓰지 않는다.
  같은 입력이면 반드시 같은 지문이 나와야 "이 패키지가 그 패키지인가" 를 판정할 수 있다.
- 소비자가 빌드를 돌린 뒤에 다시 export 해도 지문은 변하지 않는다.
  (소비자 상태가 패키지 정체성을 바꾸면 안 된다.)

> 이 규칙을 처음 구현할 때 `sorted(os.walk(...))` 로 감쌌더니 walk 가 통째로
> 소비된 뒤 정렬되어 `dirs[:]` 가지치기가 무효가 됐고, `Generated/` 가 지문에
> 섞여 들어갔다. 실측(A→B)에서 같은 입력의 지문이 달라져 잡았다.

### 표기 의무 (attribution)

라이선스 신호는 **두 축**이다. 이전 구현은 한 축만 소비자까지 날랐다.

| 축 | 질문 | 어디에 |
|---|---|---|
| `commercial_release_eligible` | 상업 게임에 실어도 되는가 | manifest 최상단 |
| `attribution` | 저자를 표기해야 하는가 · 무엇이라고 | manifest `attribution` + `ATTRIBUTION.md` |

`commercial_use: yes` 는 표기 의무를 면제하지 않는다. LPC 는 `commercial_use: yes`
이면서 `credit_required: yes` 이고, 표기 없이 배포하면 CC-BY / OGA-BY 위반이다.

- `licensing.summarize()` 에 `credit_required` 가 실린다 (3상태 — 없으면 `unknown`).
- `runtime_manifest.json` 에 **프로파일 단위** `attribution` 블록이 실린다.
  이전에는 appearance 마다 요약만 있어서 소비자가 저자를 직접 합쳐야 했다.
  `credits[]` 는 credits 화면에 그대로 넣는 줄이고 정렬 중복 제거라 결정적이다.
- `ATTRIBUTION.md` 가 **패키지 안으로 복사된다.** `report` 는 패키지 상대 경로다 —
  `05_GENERATED/reports/...` 를 가리키면 Factory 저장소가 없는 소비자는 못 읽는다.
- 표기 대상이 없는 팩(CC0)에서는 파일을 만들지 않고 `report: null` 이다.
  파일이 있다는 것 자체가 의무가 있다는 뜻이 되게 한다.

`ATTRIBUTION.md` 는 Factory 소유라서 `content_fingerprint` 에 포함된다.

### 산출물 성격 라벨

`runtime_manifest.json` 은 규칙의 `order` 블록을 그대로 나른다 — 이 산출물이 자체
기술 검증인지 발주 대응인지, 소비자 식별자가 무엇인지. 파일만 봐서는 성격을 알 수
없던 것을 없애기 위한 **표시용 라벨이고, 무엇도 막지 않는다.**

manifest 는 Factory 소유라서, 라벨이 바뀌면 `content_fingerprint` 도 바뀐다.
그건 내용이 실제로 바뀐 것이므로 정상이다 — GUID 는 그대로다 (§6 D 참조).

## 3. GUID 안정성 — in-place update

deterministic output path 에 이미 에셋이 있으면 **지우고 다시 만들지 않고 내용만 갈아끼운다.**

| 에셋 | 이전 | Contract v1 |
|---|---|---|
| `SpriteLibraryAsset` | `DeleteAsset` + `CreateAsset` | `LoadAssetAtPath` → `ClearLibrary()` → `SetDirty` |
| `AnimationClip` | `DeleteAsset` + `CreateAsset` | `LoadAssetAtPath` → `FillClip()` (`ClearCurves`) → `SetDirty` |
| `AnimatorController` | `DeleteAsset` + `CreateAsset` | `LoadAssetAtPath` → `ClearController()` → `SetDirty` |
| `CharacterProfile` / `CharacterAppearance` / prefab | 이미 in-place | 그대로 |

`ClearController()` 는 state 를 지우면 붙어 있던 transition 과
`StateMachineBehaviour` 도 같이 사라지는 성질을 이용한다. 에셋 파일 자체는 남긴다.

## 4. API 경계 — 게임이 아는 것

게임 코드가 아는 Factory 타입은 `CharacterProfile` · `CharacterAppearance` ·
`CharacterView` 세 개다. 그 밖의 것(라벨 규약, `SpriteResolver` category,
슬롯 z-order, 시트 셀 좌표, 소스 경로)은 알 필요가 없다.

### 4.1 Animator

게임은 **애니메이션 이름만** 안다.

```csharp
profile.SetMotion(animator, "walk");   // 유일한 진입점
profile.HasAnimation("run");
```

- 파라미터 이름(`"Motion"`)이 게임 코드에 리터럴로 있으면 안 된다.
  `CharacterProfile.motionParameterName` 이 들고 있고, 그 값은
  `AnimationClipBuilder.MotionParameter` 하나에서 나온다.
- state 순서에 기대면 안 된다. `motions[]` 는 `animation -> int` **명시적 매핑**이고,
  AnimatorController state 를 만드는 바로 그 자리에서 채워진다.
  (이전에는 게임 쪽 `MotionIndexOf()` 가 `profile.animations` 배열 순서가
  controller state 순서와 우연히 같기를 기대했다. 제거했다.)
- 없는 애니메이션이면 경고를 남기고 `false` 를 돌려준다.
  **다른 애니메이션으로 대체하지 않는다.** fallback 시스템은 만들지 않는다.

### 4.2 방향

`profile.directions` 가 주는 값만 쓴다. 방향 축이 없는 팩은 빈 배열이고,
게임은 아무것도 하지 않는다. 8방향/블렌딩을 만들지 않는다.

## 5. 사라진 외형 (stale appearance)

재-export 로 어떤 외형이 빠지면:

- `parts/` 텍스처는 Factory 소유라 지워진다.
- `Generated/` 의 appearance/library 에셋은 소비자 소유라 **남는다.**
  → 파일은 있는데 스프라이트가 전부 null 인 "빈 캐릭터" 가 될 수 있다.

그래서 빌더는:

1. 이번 manifest 가 선언한 seed 만 `profile.appearances` 에 담는다.
   (디스크를 훑어 담으면 잔재가 조용히 섞인다.)
2. 남은 것을 `profile.staleAppearances[]` 에 경로로 기록하고 경고 로그를 남긴다.
3. **지우지 않는다. 다른 외형으로 대체하지 않는다.**

소비자는 `profile.Contains(myAppearance)` 로 자기 참조가 아직 유효한지 확인한다.
`game-sandbox` 의 `GameArtProfile.Validate()` 가 이 검사를 포함한다 —
참조가 null 이 아닌 것만으로는 부족하기 때문이다.

## 6. 실측 — update/reference stability

게임 소유 에셋이 profile · prefab · 허용 외형을 **진짜 오브젝트 참조**(GUID + fileID)로
들고 있는 상태에서, 재-export 후 GUID 를 덤프해 비교했다. (당시 이름은
`GameCharacterSet` 이었고, Step 4 에서 `GameArtProfile` 이 그 역할을 흡수했다.)

| 시나리오 | 입력 | 결과 |
|---|---|---|
| A 최초 export | seeds `4101` | 기준선 (자산 9개 GUID 기록) |
| B 동일 입력 재-export | seeds `4101` | GUID 9/9 유지 · path 유지 · 정책 유효 |
| C 정당한 내용 변경 | seeds `4101 4102` | 기존 GUID 9/9 유지 · appearance 1→2 · 정책 유효 |
| D 참조 중인 외형 제거 | seeds `4102` | 정책 무효 · `hero_still_in_profile=false` · `stale=1` · 경고 로그 · **자동 대체 없음** · hero GUID 자체는 유지 |
| E 복구 | seeds `4101 4102` | 정책 유효 · `stale=0` · A 대비 GUID 변화 없음 |

D 에서 hero GUID 가 유지된다는 것이 중요하다. 게임의 참조는 끊기지 않고,
"이 외형은 더 이상 제공되지 않는다" 는 사실이 **발견 가능한 형태로** 드러난다.

## 7. 검증 방법

```bash
# Factory
python3 tools/tests/test_pipeline.py            # 전량 (개수는 실행이 출력한다)
python3 tools/run_unity_tests.py                # EditMode + PlayMode

# 소비자 패키지
python3 tools/export_unity_runtime.py 04_RULES/lpc_phase2_showcase.json --seeds 4101 4102 --cell-size 64
python3 tools/export_consumer_package.py <consumer>/Assets --profiles lpc_phase2_showcase

# GUID 덤프 (재-export 전/후로 두 번 돌려 비교한다)
AP2D_GUID_DUMP=/tmp/guids.json <Unity> -batchmode -nographics -projectPath <consumer> \
  -executeMethod GameSandbox.EditorTools.GameFixtureBuilder.PrepareFixtureAndDump
```

## 8. 하지 않은 것

- 버전 협상/마이그레이션 프레임워크 — `contract_version` 문자열 하나만 둔다.
- 패키지 서명·암호화·압축.
- stale 에셋 자동 삭제 — 게임이 아직 참조 중일 수 있으므로 사람이 결정한다.
- 애니메이션 fallback — 없는 이름은 `false` 다.
- `.meta` 를 Factory 가 생성/고정하는 것 — GUID 는 소비자 프로젝트의 것이다.
