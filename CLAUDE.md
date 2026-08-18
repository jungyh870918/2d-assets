# Claude 작업 지침 — 2D ART FACTORY

## 이 저장소의 목적

구매한 modular 2D 에셋을 기반으로 조합(combinatorial) variation을 대량 생성한다.
그림을 새로 그리는 게 아니라 **파츠 조합 / 팔레트 교체 / 레이어 합성**으로 만든다.

## 절대 규칙

- `01_SOURCE/` 아래는 **읽기만 한다.** 이동/이름변경/수정/삭제 금지.
- 결과물은 전부 `05_GENERATED/` 아래에만 쓴다.
- 생성은 **seed 기반 결정적**이어야 한다. `Math.random()` / `random.random()` 금지,
  항상 seed를 받아 `random.Random(seed)` 형태로 쓴다.
- 구매 에셋 이미지를 외부 이미지 생성 AI에 학습/입력 소스로 보내지 않는다.
  (Unity Asset Store 및 대부분 itch.io 에셋 라이선스가 금지)
- 라이선스가 불확실한 에셋은 `00_DOCS/licenses/` 에 확인 전까지 생성 파이프라인에 넣지 않는다.
- 구현이 바뀌어 `CLAUDE.md` · `README.md` · `00_DOCS/` 의 **사실 설명이 달라지면 같은 변경 안에서 함께 고친다.**
  이 문서들은 다음 세션이 처음 읽는 것이라, 틀린 설명은 그 위에 쌓이는 작업을 전부 틀리게 만든다.
- 이 저장소는 **공개**이고 `README.md` 의 1차 독자는 **다른 프로젝트의 LLM 에이전트**다.
  그래서 `README.md` 만 **영문**이고 나머지 문서(`CLAUDE.md` · `00_DOCS/` · `tools/README.md` ·
  생성 리포트)는 한글이다. 이 갈래를 유지한다 — README 를 한글로 되돌리지도, 나머지를
  영문으로 옮기지도 않는다. 사람용 소개문으로 되돌리지 않는다. 에이전트가 스스로 판정해야 하는 것 — 적용 가능성 ·
  클론 상태(재료는 gitignore 라 오지 않는다) · 입력 계약 · 거절 사양 — 을 계속 유지한다.
  README 에 쓴 실행 결과(테스트 수, 실패 목록 등)는 **추측하지 말고 실제로 돌려 보고 적는다.**

## 작업 순서

1. **Scan** — `01_SOURCE/<pack>/` 을 스캔해 `02_CATALOG/<pack>.json` 생성.
   파일명 패턴에서 category / part / variant / direction / frame 을 추론한다.
2. **Normalize** — 규격 검사만 하고 원본은 건드리지 않는다.
   PPU, pivot, 캔버스 크기, 프레임 수 불일치를 리포트로 남긴다.
3. **Rule** — `04_RULES/` 에 조합 규칙을 JSON으로 정의한다 (제약 · 확률 · 금지 조합).
4. **Generate** — 규칙 + 팔레트 + seed → `05_GENERATED/` 에 variant 정의(JSON) 및 합성 PNG.
5. **Validate** — 중복 조합, 규격 이탈, 누락 파츠 검사.
6. **Export** — `06_UNITY_EXPORT/` 로 manifest · 파츠 시트 · 런타임 C# 을 묶는다.
   **`.meta` 는 만들지 않는다.** GUID 는 소비자 Unity 프로젝트의 것이고, Factory 가
   생성하거나 덮어쓰면 그 프로젝트의 기존 참조가 전부 끊긴다
   (`00_DOCS/export-contract-v1.md` 참조). prefab · SpriteLibrary · clip · controller 는
   소비자 쪽 에디터 빌더가 만든다.

## 두 종류의 variation을 섞지 않는다

- **Deterministic** (기본, 70~90%): sprite swap, palette swap, layer 합성, flip, prop 조합.
  → 코드로 처리. 결과가 안정적이고 재생성 가능.
- **Generative** (예외): 외부 이미지 생성 모델.
  → 라이선스가 허용하는 소스 또는 직접 만든 master asset에만 적용.
  → 결과물은 `01_SOURCE/` 가 아니라 별도 계층에 둔다.

## Unity 쪽 규격 기본값

별도 지정이 없으면:

```
Pixels Per Unit   : 팩의 타일 크기와 일치 (LimeZu = 16)
Filter Mode       : Point (no filter)
Compression       : None
Pivot             : Bottom Center (캐릭터) / Center (프롭)
Sprite Mode       : Multiple (시트) / Single (개별 PNG)
Mesh Type         : Full Rect
```

캐릭터는 Unity **Sprite Library / Sprite Resolver** 구조를 우선 사용한다.
Main Sprite Library 하나 + 캐릭터 타입별 Variant Library.
애니메이션은 공유하고 sprite만 교체한다.

## 리포트 형식

스캔/검증 결과는 항상 파일로 남긴다. 터미널 출력만으로 끝내지 않는다.
리포트는 축이 둘이다 — **팩 축**(무엇을 가졌나)과 **프로파일 축**(무엇을 만들었나).

- 스캔 결과 → `02_CATALOG/<pack>.json` · `02_CATALOG/<pack>.summary.md`
- 가용 능력 한 장 → `02_CATALOG/CAPABILITIES.md` (모든 팩을 모은 것)
- 검증 리포트 → `05_GENERATED/reports/<profile>_validation.{json,md}`
- 출처 표기 → `05_GENERATED/reports/<profile>_attribution.md`
- 발주 회신 한 장 → `05_GENERATED/reports/<profile>_brief.md`
