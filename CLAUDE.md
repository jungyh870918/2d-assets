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

## 작업 순서

1. **Scan** — `01_SOURCE/<pack>/` 을 스캔해 `02_CATALOG/<pack>.json` 생성.
   파일명 패턴에서 category / part / variant / direction / frame 을 추론한다.
2. **Normalize** — 규격 검사만 하고 원본은 건드리지 않는다.
   PPU, pivot, 캔버스 크기, 프레임 수 불일치를 리포트로 남긴다.
3. **Rule** — `04_RULES/` 에 조합 규칙을 JSON으로 정의한다 (제약 · 확률 · 금지 조합).
4. **Generate** — 규칙 + 팔레트 + seed → `05_GENERATED/` 에 variant 정의(JSON) 및 합성 PNG.
5. **Validate** — 중복 조합, 규격 이탈, 누락 파츠 검사.
6. **Export** — `06_UNITY_EXPORT/` 로 prefab/spritelib/meta 포함 패키지 구성.

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
- 스캔 결과 → `02_CATALOG/<pack>.json`
- 검증 리포트 → `02_CATALOG/<pack>.report.md`
