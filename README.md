# 2D ART FACTORY

구매·CC0 modular 2D 에셋을 **원본 그대로 두고**, 조합/색상/레이어 규칙만으로
게임별 아트를 대량 생성하는 저장소.

핵심 원칙: **여기서 그림을 그리지 않는다. 조합하고, 검증하고, 엔진에 배선한다.**

## 폴더 구조

```
00_DOCS/          라이선스 기록 · 계약 문서 · 결정 기록
01_SOURCE/        구매/다운로드 원본. 절대 수정 금지 (read-only)
  _INBOX/         다운로드한 zip 임시 보관 (풀고 나면 비움)
02_CATALOG/       스캔 결과 (JSON) · 사람이 읽는 요약 · CAPABILITIES.md
03_PALETTES/      팔레트 정의 (램프 구조)
04_RULES/         생성 규칙 (조합 제약 · 확률 · 금지 조합 · order 블록)
05_GENERATED/     정의 · PNG · 검증 리포트 · 발주 회신 (언제든 재생성 = 버려도 됨)
06_UNITY_EXPORT/  Unity 로 넘길 패키지 (baked / runtime 두 갈래)
tools/            스캐너 · 생성기 · 검증 · 익스포터
  ap2d/           파이프라인 라이브러리
  unity/          소비자 프로젝트로 복사되는 C#
```

## 데이터 흐름

```
01_SOURCE  ──(scan)──>  02_CATALOG  ──>  CAPABILITIES.md   "무엇을 시킬 수 있나"
                            │
        03_PALETTES + 04_RULES
                            │
                        (generate)          seed 결정적
                            ↓
                       05_GENERATED  ──>  <profile>_brief.md   "무엇을 했나"
                            │
                        (validate)
                            ↓
                      06_UNITY_EXPORT
                            │
                    (export_consumer_package)
                            ↓
                    별도 Unity 게임 프로젝트
```

게임 쪽 경계는 [game-sandbox](https://github.com/jungyh870918/game-sandbox) 에서 실측한다 —
Factory 저장소가 없어도 열리고 도는 별도 프로젝트다.

## 규칙

1. `01_SOURCE` 는 **읽기 전용**. 어떤 스크립트도 여기에 쓰지 않는다.
2. `05_GENERATED` 는 **언제든 삭제하고 재생성 가능**해야 한다. 손으로 고치지 않는다.
3. 모든 생성은 **seed 기반 결정적**이어야 한다. 같은 seed = 같은 결과.
4. 새 에셋마다 `00_DOCS/licenses/` 에 라이선스 기록을 남긴다. 없으면 생성기가 거부한다.
5. 구매 에셋을 **생성형 AI 입력/학습에 쓰지 않는다** (대부분 라이선스가 금지).
6. 구현이 바뀌어 문서의 사실 설명이 달라지면 **같은 변경 안에서 함께 고친다.**

## 빠르게

```bash
python3 tools/capability_sheet.py                     # 지금 무엇이 가능한가
python3 tools/run_pipeline.py 04_RULES/<이름>.json     # 스캔→생성→검증→export→회신
python3 tools/tests/test_pipeline.py                  # 자동 테스트
python3 tools/source_fingerprint.py                   # 소스가 변조됐는지
```

명령 전체와 모듈 구조는 [tools/README.md](tools/README.md).

## 판정하지 않는 것

검증은 **사실만 본다** — 치수 · 알파 · 중복 · 소스 불변 · 재현성 · 라이선스.
「관측된 분포」도 후보 중 몇 개가 실제로 나왔는지를 셀 뿐이고, 임계값도 등급도 없다.
무엇이 더 좋은지는 사람이 정한다. 그래서 이 저장소에는 `picks/` · `approved/` 가 없다.

## 문서

| 문서 | 무엇 |
|---|---|
| [CLAUDE.md](CLAUDE.md) | 작업 지침 · 절대 규칙 |
| [00_DOCS/DIRECTOR_CONTEXT.md](00_DOCS/DIRECTOR_CONTEXT.md) | 누가 결정하는가 · 고정된 경계 · 발주 입출력 |
| [00_DOCS/export-contract-v1.md](00_DOCS/export-contract-v1.md) | Factory ↔ 소비자 소유권 경계, GUID 안정성 |
| [00_DOCS/game-art-profile.md](00_DOCS/game-art-profile.md) | 게임이 허용하는 것 · population 결정 경계 |
| [00_DOCS/unity-sprite-runtime.md](00_DOCS/unity-sprite-runtime.md) | Sprite Library / Resolver 런타임 |
| [00_DOCS/naming-convention.md](00_DOCS/naming-convention.md) | 팩·파일 네이밍 |
| [00_DOCS/licenses/](00_DOCS/licenses/) | 팩별 라이선스 기록 (생성 게이트의 입력) |
| [02_CATALOG/CAPABILITIES.md](02_CATALOG/CAPABILITIES.md) | 자동 생성 — 지금 무엇을 시킬 수 있는가 |
