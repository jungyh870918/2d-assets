# 2D ART FACTORY

구매한 modular 2D 에셋을 **원본 그대로 두고**, 조합/색상/레이어 규칙만으로
게임별 아트를 대량 생성하기 위한 저장소.

핵심 원칙: **Claude는 그림을 그리지 않는다. Claude는 아트 디렉터 + 에셋 엔지니어다.**

## 폴더 구조

```
00_DOCS/          구매 목록, 라이선스 기록, 네이밍 규칙
01_SOURCE/        구매/다운로드 원본. 절대 수정 금지 (read-only)
  _INBOX/         다운로드한 zip 임시 보관 (풀고 나면 비움)
02_CATALOG/       Claude가 01_SOURCE를 스캔해 만든 asset catalog (JSON)
03_PALETTES/      팔레트 정의 (Korean90s, Horror, Military ...)
04_RULES/         variation 생성 규칙 (조합 제약, 확률, 금지 조합)
05_GENERATED/     규칙으로 생성된 결과물 (언제든 재생성 가능 = 버려도 됨)
06_UNITY_EXPORT/  Unity 프로젝트로 넘길 최종 패키지
tools/            스캐너 / 생성기 / 검증 스크립트
```

## 데이터 흐름

```
01_SOURCE  ──(scan)──>  02_CATALOG
                            │
        03_PALETTES + 04_RULES
                            │
                         (generate)
                            ↓
                       05_GENERATED
                            │
                         (validate)
                            ↓
                      06_UNITY_EXPORT  ──>  게임 프로젝트
```

## 규칙

1. `01_SOURCE`는 **읽기 전용**. 어떤 스크립트도 여기에 쓰지 않는다.
2. `05_GENERATED`는 **언제든 삭제하고 재생성 가능**해야 한다. 손으로 고치지 않는다.
3. 모든 생성은 **seed 기반 결정적(deterministic)** 이어야 한다. 같은 seed = 같은 결과.
4. 새 에셋을 넣을 때마다 `00_DOCS/licenses/` 에 라이선스 기록을 남긴다.
5. 구매 에셋을 **생성형 AI 학습 데이터로 쓰지 않는다** (대부분 라이선스가 금지).

## 시작하기

- 구매 후보 목록: [00_DOCS/asset-shortlist.md](00_DOCS/asset-shortlist.md)
- 네이밍 규칙: [00_DOCS/naming-convention.md](00_DOCS/naming-convention.md)
- Claude 작업 지침: [CLAUDE.md](CLAUDE.md)
