"""06_UNITY_EXPORT/characters/ 로 내보내기.

이 단계에서 게임 시스템을 만들지 않는다. Unity 가 읽기 쉬운 형태로 옮기기만 한다.

manifest 는 character.json 을 그대로 복사한 게 아니라 **Unity 모양으로 편 것**이다.
Unity 의 JsonUtility 는 dictionary 를 역직렬화하지 못하므로 parts / palette 를
배열로 편다. 정본은 그대로 character.json 이다.
"""

import json
import os
import shutil

from . import TOOL_VERSION, licensing, order, paths

SCHEMA = "ap2d.unity_manifest/1"

# 모드별 Unity 소비 경로. **정보만 보존한다** — 이번 단계에서 구현하지 않는다.
UNITY_CONSUMPTION = {
    "modular_composition": {
        "sprites": "baked_sheets",
        "slicing": "cell_grid_from_manifest",
        "animation": "frames_from_sheet",
        "part_swapping": "offline_only",
        "notes": "캐릭터마다 시트를 구워 내보낸다. 런타임 파츠 교체는 불가능하고, "
                 "그게 필요해지면 Sprite Library/Resolver 단계로 간다.",
    },
    "composed_sheet": {
        "sprites": "source_sheets",
        "slicing": "requires_grid_metadata",
        "animation": "animator_with_direction",
        "part_swapping": "impossible",
        "notes": "완성 캐릭터 시트라 파츠 교체가 원천적으로 불가능하다. "
                 "Sprite Library 가 아니라 Animator + 시트 슬라이싱 경로다. "
                 "격자 크기를 팩이 선언하지 않으면 slicing 전에 metadata 가 필요하다.",
    },
    "unknown": {
        "sprites": "unknown",
        "slicing": "unknown",
        "animation": "unknown",
        "part_swapping": "unknown",
        "notes": "캐릭터 생성 대상이 아니다.",
    },
}

# CLAUDE.md 의 Unity 기본값. 규칙 파일의 "unity" 블록으로 덮어쓸 수 있다.
DEFAULT_IMPORT_SETTINGS = {
    "pixels_per_unit": 100,
    "filter_mode": "Point",
    "compression": "None",
    "mesh_type": "FullRect",
    "pivot": "BottomCenter",
    "max_texture_size": 2048,
    "generate_mip_maps": False,
    "frame_rate": 12,
}


def _flatten_parts(definition):
    ramps = definition.get("palette", {}).get("slots", {})
    out = []
    for slot in definition["layer_order"]:
        part_name = definition["parts"].get(slot)
        if not part_name:
            continue
        out.append({"slot": slot, "part": part_name, "ramp": ramps.get(slot, "")})
    return out


def _flatten_palette(definition):
    pal = definition.get("palette", {})
    return {
        "name": pal.get("palette", ""),
        "source": pal.get("source", ""),
        "tint_index": pal.get("tint_index", 0),
        "groups": [{"group": g, "ramp": r}
                   for g, r in sorted(pal.get("groups", {}).items())],
    }


def export(rule, characters, out_root=None, import_settings=None,
           license_summary=None, capabilities=None, attribution_ref=None):
    """characters: [(dir, definition)] — generate 결과 폴더에서 읽은 것.

    manifest 는 `generation_mode` 를 싣는다. Unity 쪽 소비 경로가 모드마다 다르기
    때문이다 — modular_composition 은 구운 시트를, composed_sheet 는 원본 시트를
    Animator 로 쓴다. 지금은 정보만 보존하고 Sprite Library 는 만들지 않는다.
    """
    if license_summary is None:
        license_summary = licensing.summarize(licensing.load(rule["pack"]))
    capabilities = capabilities or {}
    out_root = out_root or os.path.join(paths.UNITY_EXPORT, "characters",
                                        rule["profile"])
    settings = dict(DEFAULT_IMPORT_SETTINGS)
    settings.update(rule.get("unity", {}))
    if import_settings:
        settings.update(import_settings)

    if os.path.isdir(out_root):
        shutil.rmtree(paths.assert_writable(out_root))
    paths.ensure_dir(out_root)

    manifest_characters = []
    copied = 0
    for cdir, definition in characters:
        seed = str(definition["seed"])
        dest = paths.ensure_dir(os.path.join(out_root, seed))

        shutil.copy2(os.path.join(cdir, "character.json"),
                     os.path.join(dest, "character.json"))
        copied += 1

        outputs = definition.get("outputs", {})
        entry = {
            "seed": definition["seed"],
            "archetype": definition.get("archetype", ""),
            "directory": seed,
            "definition": "%s/character.json" % seed,
            "parts": _flatten_parts(definition),
            "palette": _flatten_palette(definition),
            "animations": definition.get("animations", []),
            "sheets": [],
        }

        preview = outputs.get("preview")
        if preview:
            shutil.copy2(os.path.join(cdir, preview["file"]),
                         os.path.join(dest, preview["file"]))
            copied += 1
            entry["preview"] = {
                "file": "%s/%s" % (seed, preview["file"]),
                "sprite_mode": "Single",
                "size": preview["size"],
            }

        for key, info in sorted((outputs.get("sheets") or {}).items()):
            shutil.copy2(os.path.join(cdir, info["file"]),
                         os.path.join(dest, info["file"]))
            copied += 1
            sheet = {
                # 키가 "anim:direction" 일 수 있으므로 애니메이션 이름을 그대로 쓰지 않는다.
                "animation": info.get("animation", key),
                "file": "%s/%s" % (seed, info["file"]),
                "sprite_mode": "Multiple",
                "frame_count": info["frame_count"],
                "cell_width": info["cell_size"][0],
                "cell_height": info["cell_size"][1],
                "size": info["size"],
                "frame_rate": settings["frame_rate"],
            }
            if info.get("direction"):
                sheet["direction"] = info["direction"]
            entry["sheets"].append(sheet)
        manifest_characters.append(entry)

    manifest = {
        "schema": SCHEMA,
        "tool_version": TOOL_VERSION,
        "profile": rule["profile"],
        "pack": rule["pack"],
        "rule": rule["_path"],
        # 이 산출물이 자체 기술 검증인지 발주 대응인지. 파일만 봐서는 성격을 알 수 없어서
        # 라벨 하나를 싣는다. **막는 값이 아니다** — 생성도 export 도 그대로 자유롭다.
        "order": order.order_block(rule),
        "character_count": len(manifest_characters),
        # Unity 소비 경로가 갈리는 축. 아직 Sprite Library 는 만들지 않고 정보만 남긴다.
        "generation_mode": capabilities.get("generation_mode", "unknown"),
        "origin_policy": capabilities.get("origin_policy", "unknown"),
        # 논리 셀 크기. 시트 셀 기반 팩에서만 값이 있다.
        "logical_cell": capabilities.get("cell"),
        "direction_axis": capabilities.get("direction_axis",
                                           {"present": "unknown"}),
        # 파일 단위 attribution 은 리포트가 정본이다. manifest 에는 요약과 참조만 둔다.
        "attribution": attribution_ref or {"attribution_required": False},
        "unity_consumption": UNITY_CONSUMPTION.get(
            capabilities.get("generation_mode"), UNITY_CONSUMPTION["unknown"]),
        # Unity 쪽에서도 제한을 잃지 않게 manifest 상단에 싣는다.
        "license": license_summary,
        "commercial_release_eligible":
            license_summary["commercial_release_eligible"],
        "import_settings": settings,
        "characters": manifest_characters,
    }
    manifest_path = os.path.join(out_root, "manifest.json")
    with open(paths.assert_writable(manifest_path), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    _write_readme(out_root, manifest)
    return manifest_path, copied, manifest


def _write_readme(out_root, manifest):
    s = manifest["import_settings"]
    lic = manifest["license"]
    banner = []
    if not lic["commercial_release_eligible"]:
        banner = [
            "> ⛔ **%s**" % licensing.NONCOMMERCIAL_BANNER,
            ">",
            "> 소스 팩 `%s` 의 라이선스는 `commercial_use: %s` 다 (`%s`)."
            % (manifest["pack"], lic["commercial_use"], lic["license"]),
            "> 이 폴더의 결과물을 상업 프로젝트에 넣지 마라.",
            "",
        ]
    text = "\n".join([
        "# %s — Unity export" % manifest["profile"],
        "",
    ] + banner + [
        "`tools/export_unity.py` 가 만든 폴더다. 손으로 고치지 않는다 —",
        "05_GENERATED 를 다시 만들고 export 를 다시 돌리면 통째로 덮어쓴다.",
        "",
        "- commercial_release_eligible: **%s**"
        % str(lic["commercial_release_eligible"]).lower(),
        "- 캐릭터 %d개, 팩 `%s`" % (manifest["character_count"], manifest["pack"]),
        "- 규칙: `%s`" % manifest["rule"],
        "",
        "## 쓰는 법",
        "",
        "1. 이 폴더를 Unity 프로젝트의 `Assets/` 아래로 복사한다.",
        "2. `tools/unity/GeneratedCharacter.cs` 를 `Assets/Scripts/` 에,",
        "   `tools/unity/GeneratedCharacterImporter.cs` 를 `Assets/Editor/` 에 넣는다.",
        "3. 메뉴 **2D Art Factory > Import Generated Characters** 를 실행하고",
        "   이 폴더의 `manifest.json` 을 고른다.",
        "",
        "importer 가 하는 일은 세 가지뿐이다: manifest 읽기 / 텍스처 임포트 설정 적용",
        "(시트는 cell 크기로 슬라이스) / 캐릭터당 `GeneratedCharacter` 에셋 생성 + 스프라이트 연결.",
        "Animator, Addressables, prefab factory 는 만들지 않는다.",
        "",
        "## 임포트 설정",
        "",
        "| 항목 | 값 |",
        "|---|---|",
        "| Pixels Per Unit | %s |" % s["pixels_per_unit"],
        "| Filter Mode | %s |" % s["filter_mode"],
        "| Compression | %s |" % s["compression"],
        "| Mesh Type | %s |" % s["mesh_type"],
        "| Pivot | %s |" % s["pivot"],
        "| Sprite Mode | preview = Single / sheet = Multiple |",
        "| Frame Rate | %s |" % s["frame_rate"],
        "",
    ])
    with open(paths.assert_writable(os.path.join(out_root, "README.md")),
              "w", encoding="utf-8") as fh:
        fh.write(text)
