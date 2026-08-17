"""ap2d — 2D Art Factory 파이프라인.

scan -> catalog -> generate -> validate -> unity export.

규약은 CLAUDE.md / README.md 를 따른다:
  - 01_SOURCE 는 읽기 전용. 이 패키지의 어떤 코드도 그 아래에 쓰지 않는다.
  - 모든 생성은 seed 기반 결정적. random() / 현재 시각을 쓰지 않는다.
"""

TOOL_VERSION = "0.1.0"
