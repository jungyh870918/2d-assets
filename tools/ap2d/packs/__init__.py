"""팩별 지식을 격리하는 adapter 레지스트리.

generic scanner 가 경로/파일명 추론으로 읽어낼 수 없지만, 팩 자체가 권위 있는
metadata 를 제공하는 경우에만 adapter 를 쓴다. adapter 는 **표준 카탈로그 스키마**를
직접 만들어 돌려주고, 그 뒤 단계(rule / compose / generate / validate / export)는
전부 generic 이다.

규칙:
  - pack-specific 지식은 이 패키지 안에만 둔다.
    generic code 에 `if "lpc" in pack_name` 같은 분기를 뿌리지 않는다.
  - adapter 는 카탈로그 스키마를 지킨다. 새 스키마를 만들지 않는다.
  - plugin framework 를 만들지 않는다. dict 하나로 충분하다.
"""

from . import lpc

ADAPTERS = {
    "lpc": lpc,
}


def get(name):
    if name not in ADAPTERS:
        raise KeyError("알 수 없는 pack adapter: %r (있는 것: %s)"
                       % (name, ", ".join(sorted(ADAPTERS))))
    return ADAPTERS[name]


def names():
    return sorted(ADAPTERS)
