# 구매 후보 shortlist

기준: **modular / layered / 파츠 분리 / 팔레트 교체 / 소스파일 포함**.
완성 PNG만 주는 팩은 자동화 증폭이 안 되므로 우선순위를 낮춘다.

가격·세일은 2026-08 검색 시점 기준이며 변동된다. 구매 전 페이지에서 재확인할 것.

---

## Tier 0 — 먼저 무료로 검증

| 에셋 | 링크 | 가격 | 왜 |
|---|---|---|---|
| Free CC0 Modular Animated Vector Characters 2D (RGS_Dev) | https://rgsdev.itch.io/free-cc0-modular-animated-vector-characters-2d | 무료 / CC0 | 파츠 분리 + 흰색 기반 recolor 구조. 파이프라인 전체를 0원으로 검증 가능 |

**첫 실험**: 이걸 Unity에 넣고 `CharacterDefinition` ScriptableObject + seed 기반
`RandomizeCharacter()` + JSON 저장을 만들어본다. 여기서 되면 나머지도 된다.

---

## Tier 1 — 현대물 코어 (이 3개면 대부분의 현대 배경 게임이 커버됨)

| 에셋 | 링크 | 가격 | 비고 |
|---|---|---|---|
| Character Creator 2D – Modern (SmallScaleInt) | https://smallscaleint.itch.io/character-creator-2d-modern | 유료 (세일 잦음) | 파츠 조합 + 파츠별 tint + 8방향 애니메이션 + 스프라이트시트 export. Unity 패키지 + 독립실행 버전. 무료 샘플 캐릭터 2종 포함 |
| Modern Interiors – RPG Tileset [16x16] (LimeZu) | https://limezu.itch.io/moderninteriors | 유료 | 가구/소품이 **개별 PNG로도 분리 제공** → 카탈로그 자동화에 결정적 |
| Modern Exteriors – RPG Tileset [16x16] (LimeZu) | https://limezu.itch.io/modernexteriors | 유료 (~$2.50 세일가 확인됨) | 거리/건물/차량/도시 소품. Interiors와 스타일 호환 |

LimeZu 계열은 하나의 "그래픽 언어"로 계속 확장 가능:
https://limezu.itch.io/ (Modern Office, Modern Farm, Serene Village 등)

---

## Tier 2 — 확장

| 에셋 | 링크 | 가격 | 비고 |
|---|---|---|---|
| Character Creator 2D – Fantasy (SmallScaleInt) | https://smallscaleint.itch.io/character-creator-2d-fantasy | $19.99~ | Modern과 같은 철학. 판타지 라인 분리용 |
| Memao Sprite Sheet Creator (Sleeping Robot Games) | https://sleeping-robot-games.itch.io/sprite-sheet-creator | ~$12.99 | 16x32 픽셀 캐릭터, 4방향. **자체 커스텀 파츠 추가 가능** = 내 아트를 규격에 얹을 수 있음 |
| 2D Monster Pack : Basic Bundle (+PSB) (SP1) | https://assetstore.unity.com/packages/2d/characters/2d-monster-pack-basic-bundle-psb-328637 | Asset Store | PSB 소스 포함 → Unity PSD Importer로 레이어 단위 활용 |

---

## 확인 필요 (링크 미확정)

아래는 이름만 거론된 것으로, 정확한 상품 페이지를 아직 확정하지 못했다. 직접 검색해서 확인할 것.

- Ultimate Modular Character Creator → https://itch.io/search?q=modular+character+creator
- Fantasy Workshop: Modular Sprite Builder → https://assetstore.unity.com/?q=modular%20sprite%20builder

---

## 카테고리 탐색용 링크

- itch.io 캐릭터 커스터마이즈 에셋: https://itch.io/game-assets/tag-2d/tag-character-customization
- itch.io 캐릭터 생성 툴: https://itch.io/tools/tag-character-customization
- Unity Asset Store 2D 캐릭터: https://assetstore.unity.com/2d/characters

---

## 구매 시 체크리스트

**최우선**
- [ ] 파츠가 개별 파일로 분리되어 있는가 (거대 시트 1장이 아닌가)
- [ ] PSD / PSB / 레이어 소스가 포함되는가
- [ ] 팔레트 교체 또는 tint를 전제로 만들어졌는가
- [ ] 애니메이션 프레임 규격이 팩 전체에서 일관적인가
- [ ] 같은 제작자의 호환 확장팩이 계속 나오는가

**피할 것**
- [ ] 완성 PNG만 제공 / 레이어 없음 / flattened
- [ ] 캐릭터별로 프레임 수와 캔버스 크기가 제각각

**구매 직후 할 일**
1. zip을 `01_SOURCE/_INBOX/` 에 두고 압축 해제
2. `01_SOURCE/<domain>/<vendor>_<pack>_<version>/` 로 이동
3. 그 폴더에 `SOURCE.md` 작성 (출처 URL / 구매일 / 버전)
4. `00_DOCS/licenses/<vendor>_<pack>.md` 작성
5. Claude에게 카탈로그 스캔 지시
