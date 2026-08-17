# 네이밍 규칙

원본(`01_SOURCE`)의 파일명은 **바꾸지 않는다.** 아래 규칙은 `05_GENERATED` 이후에만 적용.

## 원본 팩 폴더

```
01_SOURCE/<domain>/<vendor>_<packname>_<version>/
```

예:
```
01_SOURCE/characters/rgsdev_free-cc0-modular-vector-characters_v1/
01_SOURCE/environments/limezu_modern-interiors-free_v2.2/
01_SOURCE/characters/smallscaleint_cc2d-modern_2.0/
```

팩 폴더 이름이 `00_DOCS/licenses/<pack>.md` 의 파일명이자 카탈로그 이름
(`02_CATALOG/<pack>.json`)이 된다. 이 셋은 항상 같은 문자열이다.

각 팩 폴더 루트에 `SOURCE.md` 를 둔다 (출처 URL / 구매일 / 버전 / 라이선스 요약).

## 생성물

**canonical identity 는 `<profile>/<seed>/` 다.**

```
05_GENERATED/characters/<profile>/<seed>/
    character.json       조합 정의 (seed, archetype, 파츠, 팔레트)
    generation.json      생성 메타데이터 (규칙/카탈로그/팔레트 hash, 라이선스)
    sources.json         사용한 01_SOURCE 파일 목록
    preview.png          미리보기 1장
    sheet_<anim>.png     애니메이션 시트
```

예:
```
05_GENERATED/characters/cc0_test_population/1013/
```

### 왜 seed 인가

- seed 는 **결정적 identity** 다. 같은 규칙 + 같은 카탈로그 + 같은 seed = 같은 캐릭터.
  폴더 이름만 보고 재생성할 수 있어야 하므로 identity 는 seed 여야 한다.
- `archetype` 은 규칙을 고치면 바뀔 수 있고, `index` 는 생성 순서에 의존한다.
  둘 다 재생성 가능성을 보장하지 못하므로 폴더 이름에 쓰지 않는다.
- `archetype` 은 `character.json` 의 metadata 로 남는다 (`"archetype": "raider"`).

### 시스템 identity 와 display name 을 분리한다

| 용도 | 값 | 어디에 |
|---|---|---|
| 시스템 identity | `<profile>/<seed>` | 폴더 이름, Unity manifest 의 `directory` |
| 사람이 보는 이름 | `<archetype> #<seed>` 등 | contact sheet 라벨, 에디터 표시용 |

display name 은 표시할 때 조합해서 만든다. 폴더 이름으로 굳히지 않는다.
따라서 **rename migration 은 필요 없다** — 이름을 바꾸고 싶으면 표시 규칙만 바꾼다.

## 식별자

- `profile` : 아트 프로파일. `cc0_test_population`, `modern_korean_school`, `modern_zombie`
- `seed` : 정수. 규칙 파일의 `archetypes[].seeds` 가 배정한다. 팩/규칙 안에서 유일해야 한다.
- `archetype` : `student`, `police`, `gangster`, `civilian`, `zombie`, `raider` — metadata 전용

## 팔레트

```
03_PALETTES/<name>.json
```
`name`은 소문자 + 언더스코어. 예: `korean_90s`, `horror_night`, `military_od`
