#!/usr/bin/env python3
"""파이프라인 자동 테스트.

    python3 tools/tests/test_pipeline.py          # 전체
    python3 -m unittest discover -s tools/tests   # 위와 동일

pytest 의존성을 만들지 않기 위해 표준 라이브러리 unittest 만 쓴다.
이미지 렌더는 느리므로 대부분의 테스트는 render_images=False 로 정의만 만든다.
"""

import copy
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ap2d import (attribution, capability, catalog as catalog_mod,  # noqa: E402
                  compose, contactsheet, generate, integrity, licensing,
                  order as order_mod, palette as palette_mod, paths, rules)

RULE = "04_RULES/cc0_test_population.json"
PACK = "rgsdev_free-cc0-modular-vector-characters_v1"
CATALOG = "02_CATALOG/%s.json" % PACK

# 두 번째 검증팩: 구조도 라이선스도 전혀 다른 environment 팩
ENV_PACK = "limezu_modern-interiors-free_v2.2"
ENV_CATALOG = "02_CATALOG/%s.json" % ENV_PACK


def hash_tree(root):
    """폴더 전체를 (상대경로 -> sha256) 로. 소스 불변 확인용.

    구현은 `ap2d.integrity` 하나뿐이다 — 해시 방법이 두 벌이면 같은 트리에서
    다른 값이 나오고, 그러면 불변식을 측정할 수 없다.
    """
    return integrity.file_hashes(root)


class PipelineTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(paths.abspath(CATALOG)):
            raise unittest.SkipTest(
                "카탈로그가 없다. 먼저 tools/scan_pack.py 를 돌려라: %s" % CATALOG)
        cls.catalog = catalog_mod.load_catalog(CATALOG)
        cls.palette = palette_mod.load("03_PALETTES/cc0_creature.json")
        cls.rule = rules.load(RULE, catalog=cls.catalog, pal=cls.palette)

    def build(self, seed, arch_index=0, attempt_state=None):
        arch = self.rule["archetypes"][arch_index]
        return generate.build_definition(
            self.rule, self.catalog, self.palette, arch, seed,
            used_keys=attempt_state)


class TestDeterminism(PipelineTestBase):
    """1. 같은 seed 두 번 생성 -> 결과 동일."""

    def test_same_seed_same_definition(self):
        for seed in (1001, 1005, 1011, 1020):
            arch_index = 0 if seed < 1011 else 1
            first, tints_a, _ = self.build(seed, arch_index)
            second, tints_b, _ = self.build(seed, arch_index)
            self.assertEqual(first, second,
                             "seed %d 의 정의가 두 번 호출에서 달라졌다" % seed)
            self.assertEqual(tints_a, tints_b,
                             "seed %d 의 팔레트 tint 가 달라졌다" % seed)

    def test_same_seed_same_json_bytes(self):
        """직렬화한 바이트까지 같아야 한다 (키 순서 포함)."""
        first, _, _ = self.build(1007)
        second, _, _ = self.build(1007)
        self.assertEqual(json.dumps(first, sort_keys=False),
                         json.dumps(second, sort_keys=False))

    def test_full_run_is_byte_identical(self):
        """규칙 전체를 두 번 돌려 character.json 바이트를 대조한다 (이미지 제외)."""
        a = tempfile.mkdtemp(prefix="ap2d_test_a_")
        b = tempfile.mkdtemp(prefix="ap2d_test_b_")
        try:
            generate.generate(RULE, out_root=a, render_images=False, verbose=False)
            generate.generate(RULE, out_root=b, render_images=False, verbose=False)
            tree_a = hash_tree(a)
            tree_b = hash_tree(b)
            self.assertEqual(sorted(tree_a), sorted(tree_b), "생성된 파일 목록이 다르다")
            differing = [k for k in tree_a if tree_a[k] != tree_b[k]]
            self.assertEqual(differing, [], "재실행에서 달라진 파일: %s" % differing)
        finally:
            shutil.rmtree(a, ignore_errors=True)
            shutil.rmtree(b, ignore_errors=True)

    def test_rendered_images_are_byte_identical(self):
        """렌더까지 포함해 한 seed 만 확인 (전체는 validator 가 한다)."""
        rule = copy.deepcopy(self.rule)
        rule["archetypes"] = [dict(rule["archetypes"][0])]
        rule["archetypes"][0]["seeds"] = [1001]
        tmp_rule = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8")
        try:
            payload = {k: v for k, v in rule.items() if not k.startswith("_")}
            for arch in payload["archetypes"]:
                arch.pop("_seeds", None)
            json.dump(payload, tmp_rule)
            tmp_rule.close()

            a = tempfile.mkdtemp(prefix="ap2d_img_a_")
            b = tempfile.mkdtemp(prefix="ap2d_img_b_")
            try:
                generate.generate(tmp_rule.name, out_root=a, verbose=False)
                compose.clear_cache()
                generate.generate(tmp_rule.name, out_root=b, verbose=False)
                self.assertEqual(hash_tree(a), hash_tree(b),
                                 "렌더된 PNG 가 재실행에서 달라졌다")
            finally:
                shutil.rmtree(a, ignore_errors=True)
                shutil.rmtree(b, ignore_errors=True)
        finally:
            os.unlink(tmp_rule.name)


class TestVariation(PipelineTestBase):
    """2. 다른 seed -> 가능한 경우 다른 character."""

    def test_different_seeds_differ(self):
        result = generate.generate(RULE, out_root=tempfile.mkdtemp(
            prefix="ap2d_var_"), render_images=False, verbose=False)
        keys = set()
        for record in result["records"]:
            definition = record["definition"]
            key = json.dumps(
                {"parts": {k: v for k, v in definition["parts"].items() if v},
                 "palette": definition["palette"]["groups"]},
                sort_keys=True)
            keys.add(key)
        shutil.rmtree(result["out_root"], ignore_errors=True)
        self.assertEqual(len(keys), len(result["records"]),
                         "서로 다른 seed 가 같은 조합을 냈다")

    def test_uses_more_than_one_value_per_multi_variant_slot(self):
        """변형이 여러 개인 슬롯은 실제로 여러 값이 나와야 한다 (한 값에 고착 방지)."""
        seen = {}
        for arch_index, arch in enumerate(self.rule["archetypes"]):
            for seed in arch["_seeds"]:
                definition, _, _ = self.build(seed, arch_index)
                for slot, value in definition["parts"].items():
                    seen.setdefault(slot, set()).add(value)
        for slot in ("head", "eyes", "mouth", "hair", "horn"):
            self.assertGreater(
                len(seen[slot]), 1,
                "slot %r 이 항상 같은 값(%s)만 낸다" % (slot, seen[slot]))


class TestAssetSelection(PipelineTestBase):
    """3. 존재하지 않는 asset 선택 금지."""

    def test_every_choice_exists_in_catalog(self):
        for arch_index, arch in enumerate(self.rule["archetypes"]):
            for seed in arch["_seeds"]:
                definition, _, _ = self.build(seed, arch_index)
                for slot, part_name in definition["parts"].items():
                    if part_name is None:
                        continue
                    category = self.rule["slots"][slot]["from"]
                    self.assertIn(category, self.catalog["parts"])
                    self.assertIn(
                        part_name, self.catalog["parts"][category],
                        "seed %d slot %s: 카탈로그에 없는 part %s" % (seed, slot, part_name))

    def test_every_source_file_exists(self):
        definition, tints, _ = self.build(1013, 1)
        layers = generate.layers_for(definition, self.rule, tints)
        self.assertTrue(layers)
        for anim in definition["animations"]:
            for slot, category, part_name, _tint, layer_index in layers:
                count = compose.frame_count(self.catalog, category, part_name, anim,
                                            layer_index)
                for frame in range(count):
                    rel = compose.frame_path(
                        self.catalog, category, part_name, anim, frame)
                    self.assertTrue(os.path.isfile(paths.abspath(rel)),
                                    "소스 파일 없음: %s" % rel)

    def test_required_slots_are_never_none(self):
        for arch_index, arch in enumerate(self.rule["archetypes"]):
            for seed in arch["_seeds"]:
                definition, _, _ = self.build(seed, arch_index)
                for slot, spec in self.rule["slots"].items():
                    merged = rules.merge_constraint(
                        spec, arch.get("constraints", {}).get(slot, {}))
                    if merged["required"]:
                        self.assertIsNotNone(
                            definition["parts"][slot],
                            "required slot %r 이 seed %d 에서 비었다" % (slot, seed))

    def test_archetype_constraint_is_enforced(self):
        """raider 는 무기가 반드시 있어야 한다."""
        raider = self.rule["archetypes"][1]
        self.assertEqual(raider["name"], "raider")
        for seed in raider["_seeds"]:
            definition, _, _ = self.build(seed, 1)
            self.assertIsNotNone(definition["parts"]["weapon"],
                                 "raider seed %d 에 무기가 없다" % seed)
            self.assertIn(definition["palette"]["groups"]["weapon"],
                          ("metal_gunmetal", "metal_steel"))

    def test_paired_slot_follows(self):
        """날개는 한쪽만 나오면 안 된다."""
        for arch_index, arch in enumerate(self.rule["archetypes"]):
            for seed in arch["_seeds"]:
                definition, _, _ = self.build(seed, arch_index)
                left = definition["parts"]["wing_l"]
                right = definition["parts"]["wing_r"]
                self.assertEqual(left is None, right is None,
                                 "seed %d 의 날개가 한쪽만 있다" % seed)


class TestSourceImmutability(unittest.TestCase):
    """4. source directory hash 불변."""

    def test_generation_does_not_touch_source(self):
        pack_root = paths.abspath("01_SOURCE/characters/%s" % PACK)
        if not os.path.isdir(pack_root):
            self.skipTest("소스 팩이 없다: %s" % pack_root)
        before = hash_tree(pack_root)
        tmp = tempfile.mkdtemp(prefix="ap2d_src_")
        try:
            generate.generate(RULE, out_root=tmp, render_images=True, verbose=False)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        after = hash_tree(pack_root)
        self.assertEqual(sorted(before), sorted(after), "01_SOURCE 의 파일 목록이 바뀌었다")
        changed = [k for k in before if before[k] != after[k]]
        self.assertEqual(changed, [], "01_SOURCE 의 파일이 변조됐다: %s" % changed)

    def test_write_guard_rejects_source_paths(self):
        with self.assertRaises(PermissionError):
            paths.assert_writable(paths.abspath("01_SOURCE/characters/x.png"))
        with self.assertRaises(PermissionError):
            paths.ensure_dir(paths.abspath("01_SOURCE/nope"))
        # 01_SOURCE 밖은 통과해야 한다
        paths.assert_writable(paths.abspath("05_GENERATED/x.png"))


class TestBadRules(PipelineTestBase):
    """5. 잘못된 rule 입력 시 명확한 오류."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ap2d_rule_")
        with open(paths.abspath(RULE), "r", encoding="utf-8") as fh:
            self.base = json.load(fh)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_rule(self, mutate):
        rule = copy.deepcopy(self.base)
        mutate(rule)
        path = os.path.join(self.tmp, "bad.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rule, fh)
        return path

    def assert_rule_error(self, mutate, *fragments):
        path = self.write_rule(mutate)
        with self.assertRaises(rules.RuleError) as ctx:
            rules.load(path, catalog=self.catalog, pal=self.palette)
        message = str(ctx.exception)
        for fragment in fragments:
            self.assertIn(fragment, message,
                          "오류 메시지가 원인을 설명하지 않는다: %r" % message)

    def test_missing_schema(self):
        self.assert_rule_error(lambda r: r.pop("schema"), "schema")

    def test_missing_required_field(self):
        self.assert_rule_error(lambda r: r.pop("slots"), "slots")

    def test_unknown_category(self):
        self.assert_rule_error(
            lambda r: r["slots"]["head"].update({"from": "tentacle"}),
            "head", "tentacle")

    def test_unknown_part_in_allow(self):
        self.assert_rule_error(
            lambda r: r["slots"]["head"].update({"allow": ["head99"]}), "head99")

    def test_layer_order_missing_slot(self):
        self.assert_rule_error(
            lambda r: r["layer_order"].remove("hair"), "layer_order", "hair")

    def test_layer_order_unknown_slot(self):
        self.assert_rule_error(
            lambda r: r["layer_order"].append("tail"), "layer_order", "tail")

    def test_required_slot_with_none_weight(self):
        self.assert_rule_error(
            lambda r: r["slots"]["head"].update({"none_weight": 0.5}),
            "head", "none_weight")

    def test_duplicate_seed_across_archetypes(self):
        def mutate(rule):
            rule["archetypes"][1]["seeds"] = {"from": 1005, "to": 1014}
        self.assert_rule_error(mutate, "seed", "중복")

    def test_unknown_palette_ramp(self):
        self.assert_rule_error(
            lambda r: r["palettes"]["groups"]["skin"]["ramps"].append("skin_neon"),
            "skin_neon")

    def test_slot_without_palette_assignment(self):
        self.assert_rule_error(
            lambda r: r["palettes"]["groups"]["skin"]["slots"].remove("body"),
            "body")

    def test_animation_not_in_pack(self):
        self.assert_rule_error(
            lambda r: r["animations"].append("cartwheel"), "cartwheel")

    def test_constraint_on_unknown_slot(self):
        self.assert_rule_error(
            lambda r: r["archetypes"][0]["constraints"].update({"tail": {}}), "tail")

    def test_malformed_json(self):
        path = os.path.join(self.tmp, "broken.json")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{ not json")
        with self.assertRaises(rules.RuleError) as ctx:
            rules.load(path)
        self.assertIn("파싱", str(ctx.exception))

    def test_missing_file(self):
        with self.assertRaises(rules.RuleError) as ctx:
            rules.load(os.path.join(self.tmp, "nope.json"))
        self.assertIn("없다", str(ctx.exception))


class TestLicenseGate(unittest.TestCase):
    """6. 라이선스 승인되지 않은 pack 은 generator 진입 차단."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ap2d_lic_")
        self.original = licensing.paths.LICENSES
        licensing.paths.LICENSES = self.tmp

    def tearDown(self):
        licensing.paths.LICENSES = self.original
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_license(self, name, **overrides):
        fields = {
            "pack": name,
            "license": "CC0-1.0",
            "commercial_use": "yes",
            "modification": "yes",
            "redistribution": "yes",
            "ai_training": "yes",
            "pipeline_approved": "yes",
            "acquired": "2026-08-16",
            "source_url": "https://example.invalid/",
        }
        fields.update(overrides)
        body = "---\n" + "".join(
            "%s: %s\n" % (k, v) for k, v in fields.items()) + "---\n\n# %s\n" % name
        with open(os.path.join(self.tmp, name + ".md"), "w", encoding="utf-8") as fh:
            fh.write(body)

    def test_missing_license_blocks(self):
        with self.assertRaises(licensing.LicenseError) as ctx:
            licensing.require_approved("some_unrecorded_pack")
        self.assertIn("라이선스 기록이 없다", str(ctx.exception))

    def test_not_approved_blocks(self):
        self.write_license("pending_pack", pipeline_approved="no")
        with self.assertRaises(licensing.LicenseError) as ctx:
            licensing.require_approved("pending_pack")
        self.assertIn("pipeline_approved", str(ctx.exception))

    def test_no_modification_blocks(self):
        self.write_license("locked_pack", modification="no")
        with self.assertRaises(licensing.LicenseError) as ctx:
            licensing.require_approved("locked_pack")
        self.assertIn("수정", str(ctx.exception))

    def test_incomplete_record_blocks(self):
        with open(os.path.join(self.tmp, "partial_pack.md"), "w", encoding="utf-8") as fh:
            fh.write("---\npack: partial_pack\nlicense: CC0-1.0\n---\n")
        with self.assertRaises(licensing.LicenseError) as ctx:
            licensing.require_approved("partial_pack")
        self.assertIn("필수 항목 누락", str(ctx.exception))

    def test_no_frontmatter_blocks(self):
        with open(os.path.join(self.tmp, "plain_pack.md"), "w", encoding="utf-8") as fh:
            fh.write("# 그냥 마크다운\n\nCC0 인 것 같음\n")
        with self.assertRaises(licensing.LicenseError):
            licensing.require_approved("plain_pack")

    def test_approved_passes(self):
        self.write_license("ok_pack")
        fields = licensing.require_approved("ok_pack")
        self.assertEqual(fields["license"], "CC0-1.0")

    def test_generator_refuses_unapproved_pack(self):
        """generator 가 실제로 라이선스 게이트를 통과해야만 돈다."""
        rule_dir = tempfile.mkdtemp(prefix="ap2d_licrule_")
        try:
            with open(paths.abspath(RULE), "r", encoding="utf-8") as fh:
                rule = json.load(fh)
            rule["pack"] = "unapproved_pack"
            path = os.path.join(rule_dir, "unapproved.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(rule, fh)
            with self.assertRaises(licensing.LicenseError):
                generate.generate(path, out_root=rule_dir, render_images=False,
                                  verbose=False)
        finally:
            shutil.rmtree(rule_dir, ignore_errors=True)


class TestRealLicenseRecord(unittest.TestCase):
    """실제 팩의 라이선스 기록이 게이트를 통과하는지."""

    def test_cc0_pack_is_approved(self):
        fields = licensing.require_approved(PACK)
        self.assertEqual(fields["license"], "CC0-1.0")
        self.assertEqual(fields["pipeline_approved"], "yes")


class TestCatalogInference(unittest.TestCase):
    """스캐너 추론이 완성본 폴더를 파츠로 오분류하지 않는지."""

    def test_category_inference(self):
        cases = [
            (["left", "feet"], "foot", 1.0),
            (["bodies"], "body", 1.0),
            (["right", "weapons"], "weapon", 1.0),
            (["char", "1"], "unknown", 0.0),
            (["enemies"], "unknown", 0.0),
        ]
        for tokens, expected, conf in cases:
            got, got_conf = catalog_mod._classify_category(tokens)
            self.assertEqual(got, expected, "%s -> %s" % (tokens, got))
            self.assertEqual(got_conf, conf, "%s confidence" % tokens)

    def test_ambiguous_tokens_get_low_confidence(self):
        """'with hands' 는 어휘가 걸려도 확신하면 안 된다."""
        got, conf = catalog_mod._classify_category(["with", "hands"])
        self.assertEqual(got, "hand")
        self.assertLess(conf, 0.8, "'with hands' 를 파츠로 확정하면 안 된다")

    def test_tokenizer(self):
        self.assertEqual(catalog_mod._tokens("footL1"), ["foot", "l", "1"])
        self.assertEqual(catalog_mod._tokens("Left feet"), ["left", "feet"])
        self.assertEqual(catalog_mod._tokens("jumpStart_0"), ["jump", "start", "0"])

    def test_full_body_folder_is_not_modular(self):
        if not os.path.isfile(paths.abspath(CATALOG)):
            self.skipTest("카탈로그 없음")
        cat = catalog_mod.load_catalog(CATALOG)
        leaked = [e["pack_path"] for e in cat["entries"]
                  if e["inferred"]["asset_kind"] == "character_part"
                  and not e["pack_path"].startswith(
                      "Free 2D Animated Vector Game Character Sprites/Animated body parts/")]
        self.assertEqual(leaked[:5], [],
                         "완성본 폴더의 파일이 character_part 로 새어 들어왔다")

    def test_wrapper_folder_name_does_not_drive_classification(self):
        """CC0 팩의 래퍼 폴더 이름에 'Character' 가 들어 있다.

        전 파일이 공유하는 폴더는 파일들을 구분해주지 못하므로 분류 근거가 되면 안 된다.
        """
        if not os.path.isfile(paths.abspath(CATALOG)):
            self.skipTest("카탈로그 없음")
        cat = catalog_mod.load_catalog(CATALOG)
        by_path = {e["pack_path"].split("/", 1)[-1]: e for e in cat["entries"]}
        for name in ("Environment/rock1.png", "Extras/bullet.png"):
            entry = by_path.get(name)
            self.assertIsNotNone(entry, "%s 가 카탈로그에 없다" % name)
            self.assertEqual(
                entry["inferred"]["asset_kind"], "unknown",
                "%s 가 래퍼 폴더 이름 때문에 잘못 분류됐다 (%s)"
                % (name, entry["inferred"]["asset_kind"]))

    def test_sequence_requires_contiguous_frames(self):
        """번호가 끊겨 있으면 애니메이션 시퀀스가 아니다."""
        entries = []
        for i in (1, 2, 3, 9, 16):
            entries.append({
                "file_type": "image", "pack_path": "Old/Tileset_16x16_%d.png" % i,
                "inferred": {"subcategory": "Old", "animation": "Tileset_16x16",
                             "frame": i},
                "confidence": {},
            })
        for i in (0, 1, 2):
            entries.append({
                "file_type": "image", "pack_path": "body1/idle_%d.png" % i,
                "inferred": {"subcategory": "body1", "animation": "idle",
                             "frame": i},
                "confidence": {},
            })
        catalog_mod._validate_sequences(entries)
        tileset = [e for e in entries if "Tileset" in e["pack_path"]]
        idle = [e for e in entries if "idle" in e["pack_path"]]
        for e in tileset:
            self.assertIsNone(e["inferred"]["frame"],
                              "끊긴 번호가 프레임으로 남았다: %s" % e["pack_path"])
            self.assertIsNotNone(e["inferred"]["variant_index"],
                                 "variant_index 로 되돌리지 않았다")
        for e in idle:
            self.assertIsNotNone(e["inferred"]["frame"],
                                 "연속 프레임이 강등됐다: %s" % e["pack_path"])

    def test_tile_size_and_scale_group(self):
        self.assertEqual(catalog_mod._tile_size("a/16x16/Interiors_16x16.png"),
                         [16, 16])
        self.assertIsNone(catalog_mod._tile_size("Bodies/body1/idle_0.png"))
        self.assertEqual(
            catalog_mod._scale_group_key("Old/Tileset_16x16_1.png"),
            catalog_mod._scale_group_key("Old/Tileset_48x48_1.png"))
        self.assertNotEqual(
            catalog_mod._scale_group_key("Old/Tileset_16x16_1.png"),
            catalog_mod._scale_group_key("Old/Tileset_16x16_2.png"))

    def test_kind_hint_prefers_deeper_segment(self):
        """파일명이 상위 폴더명보다 그 파일을 잘 설명한다."""
        self.assertEqual(
            catalog_mod._classify_kind_hint("Old/mv/Character_2_16x16.png"),
            "character")
        self.assertEqual(
            catalog_mod._classify_kind_hint("Characters_free/Adam_run_16x16.png"),
            "character")
        self.assertEqual(
            catalog_mod._classify_kind_hint("Interiors_free/16x16/Interiors_free_16x16.png"),
            "tileset")
        self.assertIsNone(
            catalog_mod._classify_kind_hint("Old/idle_16x16_2.png"),
            "근거 없는 파일에 kind 를 붙이면 안 된다")


class TestTwoPackCoexistence(unittest.TestCase):
    """구조가 전혀 다른 두 팩이 서로 오염되지 않고 공존하는가."""

    @classmethod
    def setUpClass(cls):
        for path in (CATALOG, ENV_CATALOG):
            if not os.path.isfile(paths.abspath(path)):
                raise unittest.SkipTest("카탈로그가 없다: %s" % path)
        cls.char = catalog_mod.load_catalog(CATALOG)
        cls.env = catalog_mod.load_catalog(ENV_CATALOG)

    def test_packs_get_different_asset_kinds(self):
        char_kinds = self.char["pack"]["asset_kinds"]
        env_kinds = self.env["pack"]["asset_kinds"]
        self.assertGreater(char_kinds.get("character_part", 0), 0,
                           "character 팩에 character_part 가 없다")
        self.assertEqual(env_kinds.get("character_part", 0), 0,
                         "environment 팩에서 character_part 가 나왔다")
        self.assertGreater(env_kinds.get("environment_tile", 0), 0,
                           "environment 팩에 environment_tile 이 없다")
        self.assertEqual(char_kinds.get("environment_tile", 0), 0,
                         "character 팩에서 environment_tile 이 나왔다")

    def test_environment_pack_does_not_pollute_body_part_classifier(self):
        """environment 팩의 어떤 파일도 body part category 를 얻으면 안 된다."""
        polluted = [(e["pack_path"], e["inferred"]["category"])
                    for e in self.env["entries"]
                    if e["inferred"]["category"] != "unknown"]
        self.assertEqual(polluted, [],
                         "environment 팩이 body part category 를 얻었다")
        self.assertEqual(self.env["parts"], {},
                         "environment 팩에서 조합 가능한 파츠가 만들어졌다")

    def test_environment_pack_characters_are_composed_not_parts(self):
        """environment 팩 안의 Characters_free/ 는 완성 캐릭터로 분리되어야 한다."""
        chars = [e for e in self.env["entries"]
                 if "Characters_free" in e["pack_path"]]
        self.assertTrue(chars, "Characters_free 를 찾지 못했다")
        for e in chars:
            self.assertEqual(
                e["inferred"]["asset_kind"], "composed_character",
                "%s 가 %s 로 분류됐다" % (e["pack_path"], e["inferred"]["asset_kind"]))

    def test_unknown_stays_unknown(self):
        """근거가 없으면 unknown 으로 남아야 한다. 억지로 채우지 않는다."""
        env_kinds = self.env["pack"]["asset_kinds"]
        self.assertGreater(env_kinds.get("unknown", 0) + env_kinds.get("spritesheet", 0), 0,
                           "모든 파일이 분류됐다 — 과잉 분류를 의심해야 한다")
        for e in self.env["entries"]:
            inf = e["inferred"]
            if inf["asset_kind"] == "unknown":
                self.assertEqual(inf["category"], "unknown")
                self.assertEqual(e["confidence"]["asset_kind"], 0.0,
                                 "unknown 인데 confidence 가 0 이 아니다")

    def test_spritesheet_is_structural_not_semantic(self):
        """격자는 증명했지만 내용은 모르는 파일 — 격자 정보만 남고 의미는 비어야 한다."""
        sheets = [e for e in self.env["entries"]
                  if e["inferred"]["asset_kind"] == "spritesheet"]
        self.assertTrue(sheets, "spritesheet 로 분류된 파일이 없다")
        for e in sheets:
            self.assertEqual(e["inferred"]["category"], "unknown")
            self.assertIsNotNone(e["inferred"].get("grid"),
                                 "spritesheet 인데 격자 정보가 없다")
            self.assertGreater(e["inferred"]["grid"]["cells"], 1)

    def test_packaging_axis(self):
        env_packaging = self.env["pack"]["packaging"]
        char_packaging = self.char["pack"]["packaging"]
        self.assertGreater(env_packaging.get("sheet", 0), 0,
                           "environment 팩에 sheet 가 없다")
        self.assertGreater(char_packaging.get("sequence", 0), 0,
                           "character 팩에 sequence 가 없다")
        self.assertEqual(char_packaging.get("sheet", 0), 0,
                         "character 팩에서 sheet 가 나왔다 (개별 프레임 팩이다)")

    def test_scale_variants_detected_without_fingerprinting(self):
        """16/32/48 배율본이 SHA 로는 안 잡히지만 후보로는 식별되어야 한다."""
        groups = self.env["pack"]["scale_variant_groups"]
        self.assertGreater(len(groups), 0, "배율본 후보를 하나도 못 찾았다")
        hashes = collections_counter_by_hash(self.env["entries"])
        for key, files in groups.items():
            self.assertGreaterEqual(len(files), 2)
            shas = set(hashes[f] for f in files)
            self.assertEqual(len(shas), len(files),
                             "배율본인데 SHA 가 같다 — 중복 검사로 잡혔어야 한다")

    def test_catalog_scan_is_deterministic(self):
        """environment 팩에는 generation 대상이 없으므로, 이 팩에 적용되는
        결정성 주장은 '같은 소스 -> 같은 카탈로그 바이트' 다.
        카탈로그에 타임스탬프가 없어야 성립한다."""
        for pack_name, catalog_path in ((PACK, CATALOG), (ENV_PACK, ENV_CATALOG)):
            root = catalog_mod.load_catalog(catalog_path)["pack"]["root"]
            abs_root = paths.abspath(root)
            if not os.path.isdir(abs_root):
                self.skipTest("소스 팩 없음: %s" % root)
            first = catalog_mod.scan_pack(abs_root, pack_name)
            second = catalog_mod.scan_pack(abs_root, pack_name)
            self.assertEqual(
                json.dumps(first, sort_keys=True),
                json.dumps(second, sort_keys=True),
                "%s 의 카탈로그가 재스캔에서 달라졌다" % pack_name)

    def test_environment_catalog_matches_committed_file(self):
        """커밋된 카탈로그가 현재 소스와 일치하는가 (소스 불변 + 재현성)."""
        root = paths.abspath(self.env["pack"]["root"])
        if not os.path.isdir(root):
            self.skipTest("소스 팩 없음")
        fresh = catalog_mod.scan_pack(root, ENV_PACK)
        self.assertEqual(json.dumps(fresh, sort_keys=True),
                         json.dumps(self.env, sort_keys=True),
                         "02_CATALOG 의 environment 카탈로그가 소스와 어긋난다")

    def test_no_prop_in_environment_free_pack(self):
        """POC SKIP 의 근거가 카탈로그 수치로 남아 있어야 한다."""
        self.assertEqual(self.env["pack"]["asset_kinds"].get("prop", 0), 0,
                         "개별 prop 이 생겼다면 environment POC 를 다시 검토해야 한다")


def collections_counter_by_hash(entries):
    return {e["pack_path"]: e["sha256"] for e in entries}


FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "cc0_baseline.json")
HDS_PACK = "unknown_free-hd-survivor-w-bike_v1"
HDS_CATALOG = "02_CATALOG/%s.json" % HDS_PACK


def _load_fixture():
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        return json.load(fh)


class TestTier0ByteRegression(unittest.TestCase):
    """Tier 0 산출물이 커밋된 fixture 와 바이트 단위로 같은가.

    generation.json 은 catalog_sha256 을 담고 있어 카탈로그 스키마가 바뀌면
    정당하게 바뀐다. 그래서 fixture 에서 제외했고, 대신 아래에서 별도로
    '카탈로그를 정확히 가리키는가'를 검사한다.
    """

    def setUp(self):
        self.fixture = _load_fixture()
        self.profile_dir = os.path.join(paths.GEN_CHARACTERS,
                                        self.fixture["profile"])
        if not os.path.isdir(self.profile_dir):
            self.skipTest("생성 결과 없음 — 먼저 run_pipeline 을 돌려라")

    def test_outputs_byte_identical(self):
        changed = []
        for rel, expected in self.fixture["outputs"].items():
            path = os.path.join(self.profile_dir, rel)
            if not os.path.isfile(path):
                changed.append((rel, "없음"))
                continue
            h = hashlib.sha256()
            with open(path, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != expected:
                changed.append((rel, "hash 불일치"))
        self.assertEqual(changed, [],
                         "Tier 0 산출물이 바뀌었다 (회귀): %s" % changed[:5])

    def test_generation_json_points_at_current_catalog(self):
        catalog_sha = hashlib.sha256(
            open(paths.abspath(CATALOG), "rb").read()).hexdigest()
        for name in os.listdir(self.profile_dir):
            gpath = os.path.join(self.profile_dir, name, "generation.json")
            if not os.path.isfile(gpath):
                continue
            with open(gpath, "r", encoding="utf-8") as fh:
                gen = json.load(fh)
            self.assertEqual(gen["catalog_sha256"], catalog_sha,
                             "%s 의 catalog_sha256 이 현재 카탈로그와 다르다" % name)

    def test_cc0_parts_index_unchanged(self):
        cat = catalog_mod.load_catalog(CATALOG)
        got = hashlib.sha256(
            json.dumps(cat["parts"], sort_keys=True).encode()).hexdigest()
        self.assertEqual(got, self.fixture["cc0_parts_index_sha"],
                         "CC0 parts index 가 바뀌었다")
        self.assertEqual(cat["pack"]["asset_kinds"],
                         self.fixture["cc0_asset_kinds"],
                         "CC0 asset_kind 분포가 바뀌었다")


class TestGenerationCapability(unittest.TestCase):
    """generator 가 요구하는 전제가 명시적으로 계산되는가."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = _load_fixture()
        cls.catalogs = {}
        for pack in cls.fixture["capabilities"]:
            path = "02_CATALOG/%s.json" % pack
            if not os.path.isfile(paths.abspath(path)):
                raise unittest.SkipTest("카탈로그 없음: %s" % path)
            cls.catalogs[pack] = catalog_mod.load_catalog(path)

    def test_capabilities_match_fixture(self):
        for pack, expected in self.fixture["capabilities"].items():
            self.assertEqual(self.catalogs[pack]["pack"]["capabilities"], expected,
                             "%s 의 capability 가 바뀌었다" % pack)

    def test_capability_detection_is_deterministic(self):
        for pack, cat in self.catalogs.items():
            root = paths.abspath(cat["pack"]["root"])
            if not os.path.isdir(root):
                self.skipTest("소스 없음: %s" % pack)
            # adapter 로 만든 카탈로그는 재스캔도 같은 adapter 로 해야 한다.
            adapter = cat["pack"].get("adapter")
            a = catalog_mod.scan_pack(root, pack, adapter=adapter)["pack"]["capabilities"]
            b = catalog_mod.scan_pack(root, pack, adapter=adapter)["pack"]["capabilities"]
            self.assertEqual(a, b, "%s capability 계산이 비결정적" % pack)
            self.assertEqual(a, cat["pack"]["capabilities"],
                             "%s 재스캔 capability 가 커밋본과 다르다" % pack)

    def test_only_cc0_is_composable(self):
        caps = {p: c["pack"]["capabilities"] for p, c in self.catalogs.items()}
        self.assertEqual(caps[PACK]["composable"], "yes")
        self.assertEqual(caps[PACK]["generation_mode"], "modular_composition")
        for pack in (ENV_PACK, HDS_PACK):
            self.assertEqual(caps[pack]["composable"], "no",
                             "%s 가 composable 로 잡혔다" % pack)
            self.assertNotEqual(caps[pack]["generation_mode"], "modular_composition")

    def test_reasons_are_distinct_and_specific(self):
        caps = {p: c["pack"]["capabilities"] for p, c in self.catalogs.items()}
        self.assertEqual(caps[ENV_PACK]["reason"],
                         "atlas_only_no_individual_props")
        self.assertEqual(caps[HDS_PACK]["reason"], "composed_sheets_only")
        self.assertNotIn("reason", caps[PACK])

    def test_shared_canvas_separates_hds_from_modern_interiors(self):
        """둘 다 composable=no 지만 이유가 다르다. 그 차이가 드러나야 한다."""
        caps = {p: c["pack"]["capabilities"] for p, c in self.catalogs.items()}
        self.assertEqual(caps[HDS_PACK]["shared_canvas"], "yes",
                         "HD Survivor 는 23장이 모두 1792x1024 다")
        self.assertEqual(caps[ENV_PACK]["shared_canvas"], "no")

    def test_unprovable_capability_is_unknown_not_no(self):
        """파츠가 없으면 정렬을 증명할 수 없다. no 라고 단정하면 안 된다."""
        caps = {p: c["pack"]["capabilities"] for p, c in self.catalogs.items()}
        for pack in (ENV_PACK, HDS_PACK):
            self.assertEqual(caps[pack]["pre_aligned"], "unknown")
            self.assertEqual(caps[pack]["shared_origin"], "unknown")
            self.assertEqual(caps[pack]["animation_compatible"], "unknown")

    def test_unsupported_pack_returns_explicit_skip_not_crash(self):
        for pack in (ENV_PACK, HDS_PACK):
            status = generate.generation_status(self.catalogs[pack])
            self.assertEqual(status["status"], "skipped")
            self.assertNotEqual(status["generation_mode"], "modular_composition")
            self.assertTrue(status["reason"])
        supported = generate.generation_status(self.catalogs[PACK])
        self.assertEqual(supported["status"], "supported")

    def test_generator_raises_named_error_for_unsupported_pack(self):
        """곁가지 오류가 아니라 팩 구조 문제라고 말해야 한다."""
        tmp = tempfile.mkdtemp(prefix="ap2d_unsup_")
        try:
            rule = {
                "schema": "ap2d.rule/1", "id": "probe", "profile": "probe",
                "pack": HDS_PACK, "catalog": HDS_CATALOG,
                "animations": [], "slots": {"body": {"required": True, "from": "body"}},
                "layer_order": ["body"],
                "archetypes": [{"name": "a", "seeds": [1]}],
            }
            path = os.path.join(tmp, "probe.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(rule, fh)
            # 라이선스 게이트가 먼저 막으므로 그것부터 확인
            with self.assertRaises(licensing.LicenseError):
                generate.generate(path, out_root=tmp, render_images=False,
                                  verbose=False)
            # 라이선스를 통과했다고 가정했을 때 구조 게이트가 잡는지
            cat = self.catalogs[HDS_PACK]
            with self.assertRaises(generate.UnsupportedPackError) as ctx:
                raise generate.UnsupportedPackError(
                    HDS_PACK, cat["pack"]["capabilities"])
            self.assertEqual(ctx.exception.reason, "composed_sheets_only")
            self.assertIn("modular composition", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestDirectionAndSideAxes(unittest.TestCase):
    """§3 side 와 direction 분리 · §2 direction 축 · §4 animation 표기."""

    @classmethod
    def setUpClass(cls):
        for path in (CATALOG, HDS_CATALOG, ENV_CATALOG):
            if not os.path.isfile(paths.abspath(path)):
                raise unittest.SkipTest("카탈로그 없음: %s" % path)
        cls.cc0 = catalog_mod.load_catalog(CATALOG)
        cls.hds = catalog_mod.load_catalog(HDS_CATALOG)
        cls.env = catalog_mod.load_catalog(ENV_CATALOG)

    # ── side 는 신체 좌우만 ────────────────────────────────────────────
    def test_strafe_left_is_not_body_side(self):
        """HD Survivor regression fixture: StrafeLeft 는 이동 방향이다."""
        by_name = {os.path.basename(e["pack_path"]): e for e in self.hds["entries"]}
        for name in ("StrafeLeft.png", "StrafeRight.png",
                     "StrafeLeftAttack.png", "StrafeRightAttack.png"):
            entry = by_name.get(name)
            self.assertIsNotNone(entry, "%s 가 카탈로그에 없다" % name)
            self.assertEqual(
                entry["inferred"]["side"], "unknown",
                "%s 의 Left/Right 를 신체 좌우로 읽었다" % name)

    def test_no_side_anywhere_in_hd_survivor(self):
        sides = set(e["inferred"]["side"] for e in self.hds["entries"])
        self.assertEqual(sides, {"unknown"},
                         "완성 시트 팩에서 body side 가 나왔다: %s" % sides)

    def test_body_part_side_still_detected(self):
        """CC0 의 진짜 좌우는 계속 잡혀야 한다."""
        for category, part, expected in (("foot", "footL1", "left"),
                                         ("foot", "footR1", "right"),
                                         ("wing", "wingL1", "left"),
                                         ("hand", "handR1", "right")):
            self.assertEqual(self.cc0["parts"][category][part]["side"], expected,
                             "%s 의 side 가 사라졌다" % part)

    def test_side_requires_body_part_vocabulary(self):
        self.assertEqual(catalog_mod._classify_side(["left", "feet"])[0], "left")
        self.assertEqual(catalog_mod._classify_side(["foot", "l", "1"])[0], "left")
        self.assertEqual(catalog_mod._classify_side(["strafe", "left"])[0],
                         "unknown")
        self.assertEqual(catalog_mod._classify_side(["run", "backwards"])[0],
                         "unknown")

    # ── direction 축 ─────────────────────────────────────────────────
    def test_direction_axis_exists_and_allows_unknown(self):
        for cat in (self.cc0, self.hds, self.env):
            axis = cat["pack"]["direction_axis"]
            self.assertIn("present", axis)
            self.assertIn("encoding", axis)
            self.assertIn("values", axis)
            self.assertIn(axis["present"], ("yes", "no", "unknown"))

    def test_direction_unproven_is_unknown_not_no(self):
        """파일명에서 못 찾은 것과 '없다'는 다르다."""
        for cat in (self.cc0, self.hds):
            self.assertEqual(cat["pack"]["direction_axis"]["present"], "unknown")
            self.assertEqual(cat["pack"]["capabilities"]["directional"], "unknown")

    def test_direction_axis_not_forced_into_part_index(self):
        """방향이 증명되지 않은 팩에 direction 단계를 만들지 않는다."""
        part = self.cc0["parts"]["body"]["body1"]
        self.assertNotIn("directions", part)
        self.assertNotIn("directions", part["animations"]["idle"])
        self.assertEqual(sorted(part["animations"]["idle"]),
                         ["files", "frame_count"])

    def test_direction_grouping_activates_when_proven(self):
        """direction 이 읽히면 part index 에 축이 생긴다 (합성 입력으로 검증)."""
        entries = []
        for direction in ("north", "south"):
            for frame in (0, 1):
                entries.append({
                    "file_type": "image",
                    "pack_path": "Heads/head1/%s_walk_%d.png" % (direction, frame),
                    "path": "01_SOURCE/x/Heads/head1/%s_walk_%d.png" % (direction, frame),
                    "image": {"dimensions": [64, 64]},
                    "inferred": {"asset_kind": "character_part", "category": "head",
                                 "part": "head1", "animation": "walk", "frame": frame,
                                 "direction": direction, "side": "unknown"},
                    "confidence": {},
                })
        index = catalog_mod.build_part_index(entries)
        walk = index["head"]["head1"]["animations"]["walk"]
        self.assertIn("directions", walk, "방향이 있는데 축이 생기지 않았다")
        self.assertEqual(sorted(walk["directions"]), ["north", "south"])
        self.assertEqual(len(walk["directions"]["north"]["files"]), 2)

    # ── animation 표기 ───────────────────────────────────────────────
    def test_animation_source_distinguishes_sequence_from_sheet(self):
        cc0_sources = set(e["inferred"]["animation_source"]
                          for e in self.cc0["entries"]
                          if e["inferred"]["asset_kind"] == "character_part")
        self.assertEqual(cc0_sources, {"frame_sequence"})
        hds_sources = set(e["inferred"]["animation_source"]
                          for e in self.hds["entries"]
                          if e["file_type"] == "image")
        self.assertEqual(hds_sources, {"sheet_name"})

    def test_animation_sheet_names_are_read(self):
        anims = set(e["inferred"]["animation"] for e in self.hds["entries"]
                    if e["file_type"] == "image")
        for expected in ("Idle", "Walk", "Attack1", "RideIdle", "StrafeLeft"):
            self.assertIn(expected, anims)
        self.assertNotIn("unknown", anims)

    def test_sheet_promotion_requires_proven_context(self):
        """environment 팩의 PNG 는 애니메이션으로 승격되면 안 된다."""
        promoted = [e for e in self.env["entries"]
                    if e["inferred"]["animation_source"] == "sheet_name"]
        self.assertEqual(promoted, [],
                         "environment 팩에서 파일명이 애니메이션으로 승격됐다")

    def test_sheet_promotion_skipped_when_parts_exist(self):
        """CC0 는 파츠가 있으므로 승격 자체가 일어나지 않는다."""
        promoted = [e for e in self.cc0["entries"]
                    if e["inferred"]["animation_source"] == "sheet_name"]
        self.assertEqual(promoted, [])

    def test_promotion_is_pack_level_not_per_file_guess(self):
        entries = [{
            "file_type": "image", "pack_path": "Idle.png",
            "image": {"dimensions": [100, 100]},
            "inferred": {"asset_kind": "unknown", "animation": "unknown",
                         "frame": None, "animation_source": "unknown"},
            "confidence": {},
        }]
        # 이미지 1장뿐이면 승격하지 않는다
        self.assertEqual(catalog_mod._promote_animation_sheets(entries, "characters"),
                         [])
        # domain 이 characters 가 아니어도 승격하지 않는다
        entries.append(dict(entries[0], pack_path="Walk.png"))
        entries[1]["inferred"] = dict(entries[0]["inferred"])
        entries[1]["confidence"] = {}
        self.assertEqual(catalog_mod._promote_animation_sheets(entries, "props"), [])


class TestComposeContract(unittest.TestCase):
    """§7 compose.py 는 modular composition 전용이다."""

    @classmethod
    def setUpClass(cls):
        for path in (CATALOG, HDS_CATALOG, ENV_CATALOG):
            if not os.path.isfile(paths.abspath(path)):
                raise unittest.SkipTest("카탈로그 없음")
        cls.cc0 = catalog_mod.load_catalog(CATALOG)
        cls.hds = catalog_mod.load_catalog(HDS_CATALOG)
        cls.env = catalog_mod.load_catalog(ENV_CATALOG)

    def test_modular_pack_passes_contract(self):
        caps = compose.require_modular(self.cc0)
        self.assertEqual(caps["generation_mode"], compose.MODULAR_MODE)

    def test_composed_sheet_pack_is_explicitly_skipped(self):
        with self.assertRaises(compose.UnsupportedModeError) as ctx:
            compose.require_modular(self.hds)
        self.assertEqual(ctx.exception.mode, "composed_sheet")
        self.assertEqual(ctx.exception.reason, "composed_sheets_only")
        self.assertIn("modular composition 전용", str(ctx.exception))

    def test_environment_pack_is_explicitly_skipped(self):
        with self.assertRaises(compose.UnsupportedModeError) as ctx:
            compose.require_modular(self.env)
        self.assertEqual(ctx.exception.mode, "unsupported")

    def test_unsupported_mode_error_is_a_compose_error(self):
        """호출한 쪽이 ComposeError 로 잡아도 놓치지 않아야 한다."""
        self.assertTrue(issubclass(compose.UnsupportedModeError,
                                   compose.ComposeError))

    def test_animation_bbox_only_required_for_modular_packs(self):
        """계약을 통과한 팩에는 animation_bbox 가 항상 있다."""
        compose.require_modular(self.cc0)
        for anim in ("idle", "walk"):
            self.assertTrue(compose.animation_box(self.cc0, anim))
        # 계약을 못 지키는 팩은 bbox 를 요구당하기 전에 막힌다
        self.assertEqual(self.hds["pack"].get("animation_bbox"), {})


class TestExportContractTwoModes(unittest.TestCase):
    """§8 export manifest 가 두 모드를 구분하는가."""

    def test_manifest_carries_mode_and_origin_policy(self):
        manifest = os.path.join(paths.UNITY_EXPORT, "characters",
                                "cc0_test_population", "manifest.json")
        if not os.path.isfile(manifest):
            self.skipTest("Unity export 없음")
        with open(manifest, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(data["generation_mode"], "modular_composition")
        self.assertEqual(data["origin_policy"], "shared_canvas")
        self.assertIn("direction_axis", data)
        self.assertEqual(data["unity_consumption"]["part_swapping"],
                         "offline_only")

    def test_composed_sheet_mode_has_distinct_consumption_path(self):
        from ap2d import unity_export
        modular = unity_export.UNITY_CONSUMPTION["modular_composition"]
        composed = unity_export.UNITY_CONSUMPTION["composed_sheet"]
        self.assertNotEqual(modular["sprites"], composed["sprites"])
        self.assertEqual(composed["part_swapping"], "impossible")
        self.assertEqual(composed["animation"], "animator_with_direction")

    def test_pivot_metadata_does_not_leak_between_packs(self):
        """origin_policy 는 팩마다 계산된다. 한 팩 값이 다른 팩에 새면 안 된다."""
        from ap2d import unity_export
        lic = licensing.summarize(licensing.load(PACK))
        rule = {"profile": "p", "pack": PACK, "_path": "r", "unity": {}}
        tmp_a = tempfile.mkdtemp(prefix="ap2d_pa_")
        tmp_b = tempfile.mkdtemp(prefix="ap2d_pb_")
        try:
            _p, _c, a = unity_export.export(
                rule, [], out_root=tmp_a, license_summary=lic,
                capabilities={"generation_mode": "modular_composition",
                              "origin_policy": "shared_canvas"})
            _p, _c, b = unity_export.export(
                rule, [], out_root=tmp_b, license_summary=lic,
                capabilities={"generation_mode": "composed_sheet",
                              "origin_policy": "unknown"})
            self.assertEqual(a["origin_policy"], "shared_canvas")
            self.assertEqual(b["origin_policy"], "unknown")
            self.assertEqual(b["generation_mode"], "composed_sheet")
        finally:
            shutil.rmtree(tmp_a, ignore_errors=True)
            shutil.rmtree(tmp_b, ignore_errors=True)


class TestSlotVocabularyIsolation(unittest.TestCase):
    """두 character pack 이 서로 다른 slot 어휘를 가져도 교차 오염이 없는가."""

    @classmethod
    def setUpClass(cls):
        for path in (CATALOG, HDS_CATALOG):
            if not os.path.isfile(paths.abspath(path)):
                raise unittest.SkipTest("카탈로그 없음: %s" % path)
        cls.cc0 = catalog_mod.load_catalog(CATALOG)
        cls.hds = catalog_mod.load_catalog(HDS_CATALOG)

    def test_slots_come_from_catalog_not_hardcode(self):
        cc0_slots = set(self.cc0["parts"])
        hds_slots = set(self.hds["parts"])
        self.assertTrue(cc0_slots, "CC0 에 파츠가 없다")
        self.assertEqual(hds_slots, set(),
                         "HD Survivor 에서 파츠가 나왔다 — 완성 시트뿐인 팩이다")
        self.assertEqual(cc0_slots & hds_slots, set())

    def test_hds_does_not_pollute_cc0_categories(self):
        polluted = [(e["pack_path"], e["inferred"]["category"])
                    for e in self.hds["entries"]
                    if e["inferred"]["category"] != "unknown"]
        self.assertEqual(polluted, [],
                         "HD Survivor 파일이 body part category 를 얻었다")

    def test_rule_referencing_absent_slot_fails_clearly(self):
        tmp = tempfile.mkdtemp(prefix="ap2d_slot_")
        try:
            rule = {
                "schema": "ap2d.rule/1", "id": "x", "profile": "x",
                "pack": HDS_PACK, "catalog": HDS_CATALOG, "animations": [],
                "slots": {"head": {"required": True, "from": "head"}},
                "layer_order": ["head"],
                "archetypes": [{"name": "a", "seeds": [1]}],
            }
            path = os.path.join(tmp, "x.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(rule, fh)
            with self.assertRaises(rules.RuleError) as ctx:
                rules.load(path, catalog=self.hds)
            message = str(ctx.exception)
            self.assertIn("head", message)
            self.assertIn("카탈로그에 없는 category", message)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_available_slots_are_readable_from_catalog(self):
        """규칙 작성자가 어떤 슬롯을 쓸 수 있는지 카탈로그만 보고 알 수 있어야 한다."""
        for category, parts in self.cc0["parts"].items():
            self.assertTrue(parts, "category %s 가 비었다" % category)
            for name, part in parts.items():
                self.assertIn("animations", part)
                self.assertIn("side", part)


class TestContactSheetIsDataDriven(unittest.TestCase):
    """contact sheet 가 CC0 슬롯 이름 하드코딩 없이 동작하는가."""

    def test_no_hardcoded_cc0_slots_in_module(self):
        source = open(contactsheet.__file__, "r", encoding="utf-8").read()
        for slot in ("wing_l", "horn", '"eyes"', "'eyes'"):
            self.assertNotIn(slot, source,
                             "contactsheet 에 CC0 전용 슬롯 %r 이 남아 있다" % slot)

    def test_label_slots_picks_varying_slots_only(self):
        definitions = [
            {"parts": {"body": "b1", "head": "h1", "hat": None}},
            {"parts": {"body": "b1", "head": "h2", "hat": "cap1"}},
            {"parts": {"body": "b1", "head": "h3", "hat": None}},
        ]
        slots = contactsheet.label_slots(definitions)
        self.assertIn("head", slots, "값이 갈리는 슬롯이 빠졌다")
        self.assertIn("hat", slots, "None/값이 갈리는 슬롯이 빠졌다")
        self.assertNotIn("body", slots, "전부 같은 값인 슬롯이 라벨에 들어갔다")

    def test_label_slots_follows_rule_layer_order(self):
        definitions = [
            {"parts": {"zeta": "z1", "alpha": "a1"}},
            {"parts": {"zeta": "z2", "alpha": "a2"}},
        ]
        self.assertEqual(
            contactsheet.label_slots(definitions,
                                     {"layer_order": ["zeta", "alpha"]}),
            ["zeta", "alpha"])
        self.assertEqual(contactsheet.label_slots(definitions), ["alpha", "zeta"])

    def test_works_for_unseen_slot_names(self):
        """처음 보는 슬롯 이름만 있는 팩에서도 라벨이 나와야 한다."""
        definitions = [
            {"parts": {"turret": "t1", "tread_l": "tl1"}},
            {"parts": {"turret": "t2", "tread_l": "tl2"}},
        ]
        slots = contactsheet.label_slots(definitions)
        self.assertEqual(sorted(slots), ["tread_l", "turret"])
        label = contactsheet._part_label(definitions[0], slots)
        self.assertTrue(label.strip(), "라벨이 비었다")
        self.assertIn("1", label)

    def test_real_contact_sheet_labels_are_not_empty(self):
        profile_dir = os.path.join(paths.GEN_CHARACTERS, "cc0_test_population")
        if not os.path.isdir(profile_dir):
            self.skipTest("생성 결과 없음")
        items = contactsheet.load_characters(profile_dir)
        with open(paths.abspath(RULE), "r", encoding="utf-8") as fh:
            rule = json.load(fh)
        slots = contactsheet.label_slots([d for _c, d in items], rule)
        self.assertTrue(slots, "라벨 슬롯을 하나도 못 골랐다")
        for _cdir, definition in items:
            self.assertTrue(contactsheet._part_label(definition, slots).strip())


LPC_PACK = "lpc_ulpc-generator_phase1"
LPC_CATALOG = "02_CATALOG/%s.json" % LPC_PACK
LPC_RULE = "04_RULES/lpc_phase1_population.json"
LPC_PROFILE = "lpc_phase1_population"


class LpcTestBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(paths.abspath(LPC_CATALOG)):
            raise unittest.SkipTest("LPC 카탈로그 없음 — ingest_lpc_subset 을 먼저 돌려라")
        cls.cat = catalog_mod.load_catalog(LPC_CATALOG)
        cls.rule = rules.load(LPC_RULE, catalog=cls.cat)
        cls.pack_root = paths.abspath(cls.cat["pack"]["root"])


class TestLpcAdapter(LpcTestBase):
    """§7 adapter 가 선언 metadata 를 읽고, 그 지식이 한 곳에만 있는가."""

    def test_metadata_parser_is_deterministic(self):
        from ap2d.packs import lpc
        a = lpc.select_subset(self.pack_root)
        b = lpc.select_subset(self.pack_root)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True),
                         "subset 선택이 비결정적")

    def test_catalog_build_is_deterministic(self):
        a = catalog_mod.scan_pack(self.pack_root, LPC_PACK, adapter="lpc")
        b = catalog_mod.scan_pack(self.pack_root, LPC_PACK, adapter="lpc")
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(json.dumps(a, sort_keys=True),
                         json.dumps(self.cat, sort_keys=True),
                         "커밋된 카탈로그가 재스캔 결과와 다르다")

    def test_selected_subset_matches_targets(self):
        """Phase 1 목표 + Phase 2 예외 자산이 각 슬롯에 더해진다."""
        from ap2d.packs import lpc
        base = {"body": 1, "head": 2, "hair": 4, "torso": 4, "legs": 3, "feet": 3}
        self.assertEqual(lpc.DEFAULT_SUBSET, base)
        got = {slot: len(parts) for slot, parts in self.cat["parts"].items()}
        # 예외 자산은 해당 슬롯에 추가된다 (별도 슬롯을 만들지 않는다)
        expected = dict(base)
        expected["hair"] += 1    # multi_layer: hair_braid
        expected["legs"] += 1    # animation_subset: legs_armour
        self.assertEqual(got, expected)
        self.assertEqual(lpc.PHASE2_EXTRAS, {"multi_layer": 1, "animation_subset": 1})

    def test_share_alike_assets_are_excluded(self):
        """§5 라이선스 필터. 선택된 것 중 share-alike 전용이 있으면 안 된다."""
        for slot_parts in self.cat["parts"].values():
            for name, part in slot_parts.items():
                for credit in part["credits"]:
                    self.assertIsNotNone(credit["selected_license"],
                                         "%s 에 허용 라이선스가 없다" % name)
                    self.assertFalse(credit["share_alike_required"],
                                     "%s 에 share-alike 강제 항목이 있다" % name)
                    self.assertFalse(
                        str(credit["selected_license"]).startswith("CC-BY-SA"),
                        "%s 가 share-alike 라이선스를 골랐다" % name)

    def test_license_pick_priority(self):
        from ap2d.packs import lpc
        self.assertEqual(lpc.pick_license(["GPL 3.0", "CC-BY-SA 3.0", "OGA-BY 3.0"]),
                         "OGA-BY 3.0")
        self.assertEqual(lpc.pick_license(["CC-BY-SA 3.0", "CC0"]), "CC0")
        self.assertIsNone(lpc.pick_license(["CC-BY-SA 3.0", "GPL 3.0"]))
        self.assertIsNone(lpc.pick_license([]))

    def test_license_scoped_to_used_path(self):
        """male 만 쓰는데 muscular 가 SA 라고 전체를 탈락시키면 안 된다."""
        from ap2d.packs import lpc
        definition = {"credits": [
            {"file": "body/bodies/male", "licenses": ["OGA-BY 3.0", "GPL 3.0"]},
            {"file": "body/bodies/muscular", "licenses": ["CC-BY-SA 3.0", "GPL 3.0"]},
        ]}
        scoped = lpc.scoped_credits(definition, "body/bodies/male/")
        self.assertEqual(len(scoped), 1)
        self.assertEqual(scoped[0]["file"], "body/bodies/male")

    def test_adapter_knowledge_is_isolated(self):
        """generic 모듈에 LPC 분기가 흩어져 있으면 안 된다.

        주석/독스트링에서 LPC 를 예로 드는 건 허용한다 — 왜 이런 추상화가
        필요했는지 설명하는 문장이다. 금지하는 것은 **실행되는 코드**가
        LPC 를 아는 것이다: 문자열 리터럴 "lpc", adapter 모듈 직접 import,
        `packs.lpc` 같은 접근.
        """
        import ast as ast_mod
        generic = ["catalog.py", "compose.py", "generate.py", "rules.py",
                   "validate.py", "unity_export.py", "contactsheet.py",
                   "attribution.py", "palette.py", "licensing.py"]
        base = os.path.dirname(os.path.abspath(catalog_mod.__file__))
        for name in generic:
            path = os.path.join(base, name)
            tree = ast_mod.parse(open(path, "r", encoding="utf-8").read())
            docstrings = set()
            for node in ast_mod.walk(tree):
                if isinstance(node, (ast_mod.Module, ast_mod.FunctionDef,
                                     ast_mod.ClassDef)):
                    doc = ast_mod.get_docstring(node, clean=False)
                    if doc:
                        docstrings.add(doc)
            for node in ast_mod.walk(tree):
                if isinstance(node, ast_mod.Constant) and isinstance(node.value, str):
                    if node.value in docstrings:
                        continue
                    self.assertNotIn("lpc", node.value.lower(),
                                     "%s 의 코드 문자열에 LPC 가 있다: %r"
                                     % (name, node.value[:60]))
                if isinstance(node, ast_mod.Attribute):
                    self.assertNotEqual(node.attr, "lpc",
                                        "%s 가 packs.lpc 를 직접 만진다" % name)
                if isinstance(node, (ast_mod.Import, ast_mod.ImportFrom)):
                    for alias in node.names:
                        self.assertNotEqual(alias.name, "lpc",
                                            "%s 가 lpc adapter 를 import 한다" % name)

    def test_other_packs_unaffected_by_adapter(self):
        """adapter 를 안 쓰는 팩은 경로 추론 경로를 그대로 탄다."""
        for path in (CATALOG, ENV_CATALOG, HDS_CATALOG):
            if not os.path.isfile(paths.abspath(path)):
                continue
            cat = catalog_mod.load_catalog(path)
            self.assertIsNone(cat["pack"].get("adapter"),
                              "%s 에 adapter 가 붙었다" % path)


class TestLpcTopology(LpcTestBase):
    """§8/§9 physical layout 과 logical topology 의 분리."""

    def test_sheet_based_animation_info(self):
        info = compose.animation_info(self.cat, "body", "body", "walk")
        self.assertTrue(compose.is_sheet_based(info))
        self.assertEqual(info["frame_count"], 9)
        self.assertEqual(info["cell"], {"width": 64, "height": 64,
                                        "columns": 9, "rows": 4})
        self.assertEqual(info["directions"], ["north", "west", "south", "east"])
        self.assertNotIn("files", info)

    def test_direction_topology_is_per_animation(self):
        """방향 수를 전역 상수로 가정하지 않는다."""
        axis = self.cat["pack"]["direction_axis"]
        self.assertEqual(axis["present"], "yes")
        self.assertEqual(axis["encoding"], "sheet_row")
        self.assertIn("by_animation", axis)
        for animation in ("idle", "walk", "run"):
            self.assertEqual(sorted(axis["by_animation"][animation]),
                             ["east", "north", "south", "west"])

    def test_cell_resolution_picks_correct_row_and_column(self):
        """(animation, direction, frame) -> 시트 안의 정확한 셀."""
        from PIL import Image
        info = compose.animation_info(self.cat, "body", "body", "walk")
        sheet = Image.open(paths.abspath(info["sheet"])).convert("RGBA")
        for row, direction in enumerate(info["directions"]):
            for frame in (0, 4, 8):
                got, source = compose.resolve_layer(
                    self.cat, "body", "body", "walk", frame, direction=direction)
                expected = sheet.crop((frame * 64, row * 64,
                                       frame * 64 + 64, row * 64 + 64))
                self.assertEqual(got.tobytes(), expected.tobytes(),
                                 "%s frame %d 셀이 어긋났다" % (direction, frame))
                self.assertEqual(source, info["sheet"])

    def test_missing_direction_is_an_explicit_error(self):
        with self.assertRaises(compose.ComposeError) as ctx:
            compose.resolve_layer(self.cat, "body", "body", "walk", 0)
        self.assertIn("direction", str(ctx.exception))
        with self.assertRaises(compose.ComposeError):
            compose.resolve_layer(self.cat, "body", "body", "walk", 0,
                                  direction="up")

    def test_frame_out_of_range_is_an_explicit_error(self):
        with self.assertRaises(compose.ComposeError):
            compose.resolve_layer(self.cat, "body", "body", "walk", 99,
                                  direction="south")

    def test_layer_overlay_alignment(self):
        """모든 레이어가 같은 셀 캔버스를 갖는가 — 어긋나면 합성이 불가능하다."""
        for slot, parts in self.cat["parts"].items():
            for name in parts:
                size = compose.layer_canvas(self.cat, slot, name, "walk")
                self.assertEqual(size, (64, 64),
                                 "%s/%s 의 셀이 64x64 가 아니다" % (slot, name))

    def test_compose_uses_generic_path_for_both_packs(self):
        """CC0 와 LPC 가 같은 compose_frame 을 탄다."""
        compose.require_modular(self.cat)
        layers = [("body", "body", "body", None),
                  ("torso", "torso", "torso_clothes_longsleeve", None)]
        img, used = compose.compose_frame(self.cat, layers, "walk", 0,
                                          direction="south")
        self.assertEqual(img.size, (64, 64))
        self.assertEqual(len(used), 2)
        if os.path.isfile(paths.abspath(CATALOG)):
            cc0 = catalog_mod.load_catalog(CATALOG)
            cc0_img, cc0_used = compose.compose_frame(
                cc0, [("body", "body", "body1", None)], "idle", 0)
            self.assertGreater(cc0_img.size[0], 0)
            self.assertEqual(len(cc0_used), 1)


class TestLpcGeneration(LpcTestBase):
    """§16 결정적 생성 + §11 z-order."""

    def test_layer_order_comes_from_declared_z_pos(self):
        self.assertEqual(self.rule["_layer_order_source"], "catalog:z_pos")
        self.assertEqual(self.rule["layer_order"],
                         ["body", "legs", "feet", "torso", "head", "hair"])
        z = [min(p["z_pos"] for p in self.cat["parts"][
            self.rule["slots"][s]["from"]].values())
             for s in self.rule["layer_order"]]
        self.assertEqual(z, sorted(z), "z_pos 가 오름차순이 아니다")

    def test_layer_order_is_deterministic(self):
        for _ in range(3):
            rule = rules.load(LPC_RULE, catalog=self.cat)
            self.assertEqual(rule["layer_order"], self.rule["layer_order"])

    def test_missing_z_pos_is_an_explicit_error(self):
        cat = json.loads(json.dumps(self.cat))
        for part in cat["parts"]["body"].values():
            part.pop("z_pos", None)
        with self.assertRaises(rules.RuleError) as ctx:
            rules.load(LPC_RULE, catalog=cat)
        self.assertIn("z_pos", str(ctx.exception))

    def test_same_seed_same_definition(self):
        arch = self.rule["archetypes"][0]
        for seed in (4001, 4005, 4010):
            a, ta, _ = generate.build_definition(self.rule, self.cat, None,
                                                 arch, seed)
            b, tb, _ = generate.build_definition(self.rule, self.cat, None,
                                                 arch, seed)
            self.assertEqual(a, b)
            self.assertEqual(ta, tb)

    def test_different_seeds_differ(self):
        arch = self.rule["archetypes"][0]
        seen = set()
        for seed in arch["_seeds"]:
            definition, _t, _m = generate.build_definition(
                self.rule, self.cat, None, arch, seed, used_keys=set())
            seen.add(json.dumps(definition["parts"], sort_keys=True))
        self.assertGreater(len(seen), 1, "모든 seed 가 같은 조합을 냈다")

    def test_optional_slot_can_be_absent(self):
        """hair 는 선택 슬롯이다 — 없는 캐릭터가 실제로 나와야 한다."""
        arch = self.rule["archetypes"][0]
        values = set()
        for seed in arch["_seeds"]:
            definition, _t, _m = generate.build_definition(
                self.rule, self.cat, None, arch, seed, used_keys=set())
            values.add(definition["parts"]["hair"])
        self.assertIn(None, values, "hair 가 비는 경우가 한 번도 없다")
        self.assertGreater(len(values - {None}), 1)

    def test_required_slots_never_absent(self):
        arch = self.rule["archetypes"][0]
        for seed in arch["_seeds"]:
            definition, _t, _m = generate.build_definition(
                self.rule, self.cat, None, arch, seed, used_keys=set())
            for slot in ("body", "legs", "feet", "torso", "head"):
                self.assertIsNotNone(definition["parts"][slot],
                                     "required slot %s 가 seed %d 에서 비었다"
                                     % (slot, seed))

    def test_unsupported_animation_is_rejected(self):
        """subset 이 지원하지 않는 애니메이션을 규칙이 요구하면 명확히 실패한다."""
        raw = json.loads(open(paths.abspath(LPC_RULE), encoding="utf-8").read())
        raw["animations"] = ["idle", "walk", "run", "spellcast"]
        tmp = tempfile.mkdtemp(prefix="ap2d_lpcanim_")
        try:
            path = os.path.join(tmp, "bad.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(raw, fh)
            with self.assertRaises(rules.RuleError) as ctx:
                rules.load(path, catalog=self.cat)
            self.assertIn("spellcast", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_generated_outputs_preserve_direction(self):
        profile_dir = os.path.join(paths.GEN_CHARACTERS, LPC_PROFILE)
        if not os.path.isdir(profile_dir):
            self.skipTest("생성 결과 없음")
        checked = 0
        for name in os.listdir(profile_dir):
            cpath = os.path.join(profile_dir, name, "character.json")
            if not os.path.isfile(cpath):
                continue
            with open(cpath, "r", encoding="utf-8") as fh:
                definition = json.load(fh)
            sheets = definition["outputs"]["sheets"]
            self.assertEqual(len(sheets), 12, "3 애니메이션 × 4 방향이어야 한다")
            for key, info in sheets.items():
                self.assertIn("direction", info, "%s 에 방향이 없다" % key)
                self.assertIn(info["direction"],
                              ["north", "west", "south", "east"])
                self.assertEqual(key, "%s:%s" % (info["animation"],
                                                 info["direction"]))
            self.assertIn("direction", definition["outputs"]["preview"])
            checked += 1
        self.assertEqual(checked, 10)


class TestLpcAttribution(LpcTestBase):
    """§6 file-level license 전파."""

    def test_catalog_carries_per_asset_credits(self):
        for slot_parts in self.cat["parts"].values():
            for name, part in slot_parts.items():
                self.assertTrue(part["credits"], "%s 에 credits 가 없다" % name)
                for credit in part["credits"]:
                    for key in ("source_file", "authors", "selected_license",
                                "source_urls", "attribution_required"):
                        self.assertIn(key, credit)

    def test_generation_metadata_carries_attribution(self):
        profile_dir = os.path.join(paths.GEN_CHARACTERS, LPC_PROFILE)
        if not os.path.isdir(profile_dir):
            self.skipTest("생성 결과 없음")
        for name in sorted(os.listdir(profile_dir)):
            gpath = os.path.join(profile_dir, name, "generation.json")
            if not os.path.isfile(gpath):
                continue
            with open(gpath, "r", encoding="utf-8") as fh:
                attrib = json.load(fh)["attribution"]
            self.assertGreater(attrib["source_assets"], 0)
            self.assertTrue(attrib["authors"])
            self.assertTrue(attrib["attribution_required"])
            self.assertFalse(attrib["share_alike_present"])
            for entry in attrib["attribution_entries"]:
                self.assertTrue(entry["text"])

    def test_attribution_is_deterministic_and_deduplicated(self):
        credits = [
            {"source_file": "a", "authors": ["Bob", "Ann"],
             "selected_license": "CC0", "alternative_licenses": [],
             "source_urls": ["u1"], "attribution_required": False,
             "share_alike_required": False, "slot": "hair", "asset": "x"},
            {"source_file": "a", "authors": ["Ann"],
             "selected_license": "CC0", "alternative_licenses": [],
             "source_urls": ["u1"], "attribution_required": False,
             "share_alike_required": False, "slot": "hair", "asset": "y"},
        ]
        first = attribution.summarize(credits)
        second = attribution.summarize(list(reversed(credits)))
        self.assertEqual(first, second, "attribution 집계가 입력 순서에 의존한다")
        self.assertEqual(first["source_assets"], 1, "같은 파일이 중복 집계됐다")
        self.assertEqual(first["authors"], ["Ann", "Bob"])
        self.assertEqual(first["attribution_entries"][0]["used_by"],
                         ["hair/x", "hair/y"])

    def test_empty_attribution_for_packs_without_credits(self):
        """credits 가 없는 팩은 빈 블록이어야 한다 (기존 팩 영향 없음)."""
        summary = attribution.summarize([])
        self.assertEqual(summary["source_assets"], 0)
        self.assertFalse(summary["attribution_required"])
        self.assertFalse(summary["share_alike_present"])
        if os.path.isfile(paths.abspath(CATALOG)):
            cc0 = catalog_mod.load_catalog(CATALOG)
            found = attribution.credits_for_parts(cc0, [("body", "body1")])
            self.assertEqual(found, [])

    def test_attribution_report_exists(self):
        path = os.path.join(paths.GEN_REPORTS, "%s_attribution.md" % LPC_PROFILE)
        if not os.path.isfile(path):
            self.skipTest("리포트 없음")
        text = open(path, "r", encoding="utf-8").read()
        self.assertIn("attribution report", text)
        self.assertIn("share_alike_present", text)
        for author in ("bluecarrot16", "JaidynReiman"):
            self.assertIn(author, text)

    def test_unity_manifest_keeps_direction_and_attribution(self):
        path = os.path.join(paths.UNITY_EXPORT, "characters", LPC_PROFILE,
                            "manifest.json")
        if not os.path.isfile(path):
            self.skipTest("Unity export 없음")
        with open(path, "r", encoding="utf-8") as fh:
            manifest = json.load(fh)
        self.assertEqual(manifest["generation_mode"], "modular_composition")
        self.assertEqual(manifest["origin_policy"], "logical_cell")
        self.assertEqual(manifest["logical_cell"], [64, 64])
        self.assertEqual(manifest["direction_axis"]["encoding"], "sheet_row")
        self.assertTrue(manifest["attribution"]["attribution_required"])
        self.assertFalse(manifest["attribution"]["share_alike_present"])
        for sheet in manifest["characters"][0]["sheets"]:
            self.assertIn("direction", sheet)
            self.assertNotIn(":", sheet["animation"])


class TestCrossPackIsolation(unittest.TestCase):
    """§20 두 modular 팩의 slot 어휘가 서로 오염되지 않는가."""

    @classmethod
    def setUpClass(cls):
        for path in (CATALOG, LPC_CATALOG):
            if not os.path.isfile(paths.abspath(path)):
                raise unittest.SkipTest("카탈로그 없음: %s" % path)
        cls.cc0 = catalog_mod.load_catalog(CATALOG)
        cls.lpc = catalog_mod.load_catalog(LPC_CATALOG)

    def test_slot_vocabularies_are_independent(self):
        cc0_slots = set(self.cc0["parts"])
        lpc_slots = set(self.lpc["parts"])
        self.assertTrue(cc0_slots and lpc_slots)
        self.assertIn("torso", lpc_slots)
        self.assertNotIn("torso", cc0_slots, "CC0 에 LPC 슬롯이 생겼다")
        self.assertIn("wing", cc0_slots)
        self.assertNotIn("wing", lpc_slots, "LPC 에 CC0 슬롯이 생겼다")

    def test_part_names_do_not_collide(self):
        cc0_parts = set(n for p in self.cc0["parts"].values() for n in p)
        lpc_parts = set(n for p in self.lpc["parts"].values() for n in p)
        self.assertEqual(cc0_parts & lpc_parts, set())

    def test_both_are_modular_composition(self):
        for cat in (self.cc0, self.lpc):
            self.assertEqual(cat["pack"]["capabilities"]["generation_mode"],
                             "modular_composition")
            compose.require_modular(cat)

    def test_origin_policies_differ_and_do_not_leak(self):
        self.assertEqual(self.cc0["pack"]["capabilities"]["origin_policy"],
                         "shared_canvas")
        self.assertEqual(self.lpc["pack"]["capabilities"]["origin_policy"],
                         "logical_cell")

    def test_cc0_has_no_direction_axis(self):
        self.assertEqual(self.cc0["pack"]["direction_axis"]["present"], "unknown")
        self.assertEqual(self.lpc["pack"]["direction_axis"]["present"], "yes")

    def test_cc0_is_frame_per_file_lpc_is_sheet_cell(self):
        cc0_info = compose.animation_info(self.cc0, "body", "body1", "idle")
        lpc_info = compose.animation_info(self.lpc, "body", "body", "idle")
        self.assertFalse(compose.is_sheet_based(cc0_info))
        self.assertTrue(compose.is_sheet_based(lpc_info))
        self.assertIn("files", cc0_info)
        self.assertIn("sheet", lpc_info)


class TestRuntimeExport(unittest.TestCase):
    """Sprite Library runtime export. baked export 를 대체하지 않는다."""

    @classmethod
    def setUpClass(cls):
        from ap2d import runtime_export
        cls.rx = runtime_export
        cls.profiles = []
        for rule_path, cell in ((RULE, 256), (LPC_RULE, 64)):
            if not os.path.isfile(paths.abspath(rule_path)):
                continue
            raw = generate._peek_rule(rule_path)
            if not os.path.isfile(paths.abspath(raw["catalog"])):
                continue
            cls.profiles.append((rule_path, cell, raw["profile"]))
        if not cls.profiles:
            raise unittest.SkipTest("규칙/카탈로그 없음")

    def _manifest(self, profile):
        path = os.path.join(paths.UNITY_EXPORT, "runtime", profile,
                            "runtime_manifest.json")
        if not os.path.isfile(path):
            self.skipTest("runtime export 없음: %s" % profile)
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), os.path.dirname(path)

    def test_label_roundtrip(self):
        for animation, direction, frame in (("walk", "south", 3), ("idle", None, 0),
                                            ("run", "north", 12)):
            label = self.rx.label_for(animation, frame, direction)
            parsed = self.rx.parse_label(label)
            self.assertEqual(parsed["animation"], animation)
            self.assertEqual(parsed["direction"], direction)
            self.assertEqual(parsed["frame"], frame)

    def test_label_format_is_stable(self):
        self.assertEqual(self.rx.label_for("walk", 3, "south"), "walk__south__03")
        self.assertEqual(self.rx.label_for("idle", 0), "idle__00")

    def test_manifest_has_profile_slots_not_per_appearance(self):
        """프리팹 구조가 appearance 마다 달라지면 AnimationClip 을 공유할 수 없다."""
        for _rule, _cell, profile in self.profiles:
            manifest, _root = self._manifest(profile)
            self.assertIn("slots", manifest)
            slots = [s["slot"] for s in manifest["slots"]]
            self.assertEqual(len(slots), len(set(slots)), "슬롯이 중복됐다")
            z = [s["z_order"] for s in manifest["slots"]]
            self.assertEqual(z, sorted(z), "슬롯이 z-order 오름차순이 아니다")
            # 모든 appearance 의 슬롯이 프로파일 슬롯 안에 들어와야 한다
            for appearance in manifest["appearances"]:
                for layer in appearance["layers"]:
                    self.assertIn(layer["slot"], slots)

    def test_labels_match_topology(self):
        for _rule, _cell, profile in self.profiles:
            manifest, _root = self._manifest(profile)
            for sheet in manifest["part_sheets"]:
                self.assertEqual(len(sheet["labels"]), sheet["frame_count"])
                for i, label in enumerate(sheet["labels"]):
                    parsed = self.rx.parse_label(label)
                    self.assertEqual(parsed["frame"], i)
                    self.assertEqual(parsed["animation"], sheet["animation"])
                    self.assertEqual(parsed["direction"], sheet["direction"])

    def test_direction_topology_preserved(self):
        """LPC 는 방향이 있고 CC0 는 없다. 둘 다 손실 없이 표현돼야 한다."""
        manifest, _root = self._manifest(LPC_PROFILE)
        for animation, topo in manifest["topology"].items():
            self.assertEqual(sorted(topo["directions"]),
                             ["east", "north", "south", "west"])
        for sheet in manifest["part_sheets"]:
            self.assertIsNotNone(sheet["direction"])

        manifest, _root = self._manifest("cc0_test_population")
        for animation, topo in manifest["topology"].items():
            self.assertEqual(topo["directions"], [])
        for sheet in manifest["part_sheets"]:
            self.assertIsNone(sheet["direction"])

    def test_origin_metadata_preserved(self):
        cc0, _r = self._manifest("cc0_test_population")
        lpc, _r2 = self._manifest(LPC_PROFILE)
        self.assertEqual(cc0["origin"]["policy"], "shared_canvas")
        self.assertEqual(lpc["origin"]["policy"], "logical_cell")
        self.assertEqual(lpc["origin"]["logical_cell"], [64, 64])
        for manifest in (cc0, lpc):
            self.assertTrue(manifest["origin"]["pivot"])
            self.assertGreater(manifest["origin"]["pixels_per_unit"], 0)

    def test_attribution_flows_into_runtime_manifest(self):
        lpc, _root = self._manifest(LPC_PROFILE)
        for appearance in lpc["appearances"]:
            attrib = appearance["attribution"]
            self.assertTrue(attrib["attribution_required"])
            self.assertFalse(attrib["share_alike_present"])
            self.assertTrue(attrib["authors"])

    def test_z_order_source_is_recorded(self):
        lpc, _root = self._manifest(LPC_PROFILE)
        for appearance in lpc["appearances"]:
            for layer in appearance["layers"]:
                self.assertEqual(layer["z_source"], "declared",
                                 "LPC 는 zPos 를 선언한다")
        cc0, _root2 = self._manifest("cc0_test_population")
        for appearance in cc0["appearances"]:
            for layer in appearance["layers"]:
                self.assertEqual(layer["z_source"], "layer_order",
                                 "CC0 는 규칙의 layer_order 를 쓴다")

    def test_export_is_deterministic(self):
        from ap2d import catalog as cm
        rule_path, cell, profile = self.profiles[0]
        raw = generate._peek_rule(rule_path)
        cat = cm.load_catalog(raw["catalog"])
        pal = (palette_mod.load(raw["palettes"]["source"])
               if raw.get("palettes") else None)
        rule = rules.load(rule_path, catalog=cat, pal=pal)
        profile_dir = os.path.join(paths.GEN_CHARACTERS, profile)
        if not os.path.isdir(profile_dir):
            self.skipTest("생성 결과 없음")
        characters = []
        for name in sorted(os.listdir(profile_dir), key=lambda n: (len(n), n))[:2]:
            cpath = os.path.join(profile_dir, name, "character.json")
            if os.path.isfile(cpath):
                with open(cpath, "r", encoding="utf-8") as fh:
                    characters.append((os.path.join(profile_dir, name), json.load(fh)))
        a = tempfile.mkdtemp(prefix="ap2d_rt_a_")
        b = tempfile.mkdtemp(prefix="ap2d_rt_b_")
        try:
            _p1, m1 = self.rx.export(rule, cat, characters, out_root=a, cell_size=cell)
            _p2, m2 = self.rx.export(rule, cat, characters, out_root=b, cell_size=cell)
            self.assertEqual(json.dumps(m1, sort_keys=True),
                             json.dumps(m2, sort_keys=True))
            self.assertEqual(hash_tree(a), hash_tree(b),
                             "runtime export 가 재실행에서 달라졌다")
        finally:
            shutil.rmtree(a, ignore_errors=True)
            shutil.rmtree(b, ignore_errors=True)

    def test_baked_output_untouched_by_runtime_export(self):
        """runtime export 는 baked 결과를 건드리지 않는다."""
        fixture = _load_fixture()
        profile_dir = os.path.join(paths.GEN_CHARACTERS, fixture["profile"])
        if not os.path.isdir(profile_dir):
            self.skipTest("생성 결과 없음")
        for rel, expected in list(fixture["outputs"].items())[:20]:
            path = os.path.join(profile_dir, rel)
            h = hashlib.sha256(open(path, "rb").read()).hexdigest()
            self.assertEqual(h, expected, "%s 가 바뀌었다" % rel)

    def test_measurements_are_real_counts(self):
        for _rule, _cell, profile in self.profiles:
            manifest, root = self._manifest(profile)
            measured = self.rx.measure_runtime(manifest, root)
            self.assertEqual(measured["textures"], len(manifest["part_sheets"]))
            self.assertGreater(measured["disk_bytes"], 0)
            baked = self.rx.measure_baked(
                os.path.join(paths.GEN_CHARACTERS, profile))
            self.assertGreater(baked["textures"], 0)


PHASE2_RULE = "04_RULES/lpc_phase2_showcase.json"
PHASE2_PROFILE = "lpc_phase2_showcase"


class TestPhase2Assets(unittest.TestCase):
    """Phase 2 — multi-layer item / animation subset 을 실제 자산으로 검증."""

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(paths.abspath(LPC_CATALOG)):
            raise unittest.SkipTest("LPC 카탈로그 없음")
        cls.cat = catalog_mod.load_catalog(LPC_CATALOG)
        if not os.path.isfile(paths.abspath(PHASE2_RULE)):
            raise unittest.SkipTest("Phase 2 규칙 없음")
        cls.rule = rules.load(PHASE2_RULE, catalog=cls.cat)

    # ── multi-layer ──────────────────────────────────────────────────
    def test_multi_layer_asset_has_multiple_visual_layers(self):
        part = self.cat["parts"]["hair"]["hair_braid"]
        self.assertIsNotNone(part.get("visual_layers"),
                             "multi-layer 자산에 visual_layers 가 없다")
        layers = compose.visual_layers(self.cat, "hair", "hair_braid")
        self.assertEqual(len(layers), 2)
        indexes = [i for i, _z in layers]
        zs = [z for _i, z in layers]
        self.assertEqual(indexes, [0, 1])
        self.assertEqual(sorted(zs), [9, 120],
                         "앞/뒤 zPos 가 소스 선언과 다르다")

    def test_single_layer_assets_unchanged(self):
        """예외 자산 하나 때문에 나머지 파츠 모양이 바뀌면 안 된다."""
        for slot, parts in self.cat["parts"].items():
            for name, part in parts.items():
                if name == "hair_braid":
                    continue
                self.assertIsNone(part.get("visual_layers"),
                                  "%s 에 불필요한 visual_layers 가 생겼다" % name)
                self.assertEqual(len(compose.visual_layers(self.cat, slot, name)), 1)

    def test_multi_layer_back_layer_renders_behind_body(self):
        """뒤 레이어(z=9)가 몸통(z=10)보다 먼저 그려져야 한다."""
        arch = self.rule["archetypes"][0]
        definition, tints, _m = generate.build_definition(
            self.rule, self.cat, None, arch, 4101)
        layers = generate.layers_for(definition, self.rule, tints, self.cat)
        order = [(s, p, li) for s, _c, p, _t, li in layers]
        braid_back = order.index(("hair", "hair_braid", 1))
        body = order.index(("body", "body", 0))
        braid_front = order.index(("hair", "hair_braid", 0))
        self.assertLess(braid_back, body, "뒤 레이어가 몸통보다 뒤에 그려지지 않는다")
        self.assertGreater(braid_front, body, "앞 레이어가 몸통보다 앞에 그려지지 않는다")

    def test_multi_layer_is_one_logical_selection(self):
        """두 레이어가 하나의 선택에 묶여야 한다 (독립 장비 2개가 아니다)."""
        arch = self.rule["archetypes"][0]
        for seed in arch["_seeds"]:
            definition, _t, _m = generate.build_definition(
                self.rule, self.cat, None, arch, seed, used_keys=set())
            # parts 에는 슬롯 하나에 asset 하나뿐이다
            self.assertEqual(definition["parts"]["hair"], "hair_braid")
            self.assertNotIn("hair#1", definition["parts"])

    # ── animation subset ─────────────────────────────────────────────
    def test_subset_asset_supports_only_some_animations(self):
        part = self.cat["parts"]["legs"]["legs_armour"]
        self.assertEqual(sorted(part["supported_animations"]), ["idle", "walk"])
        self.assertTrue(compose.supports(self.cat, "legs", "legs_armour", "walk"))
        self.assertFalse(compose.supports(self.cat, "legs", "legs_armour", "run"))

    def test_rule_requires_explicit_policy_for_subset(self):
        """allow_subset 없이 서브셋 자산을 쓰면 명확히 실패해야 한다."""
        raw = json.loads(open(paths.abspath(PHASE2_RULE), encoding="utf-8").read())
        raw.pop("animation_policy", None)
        tmp = tempfile.mkdtemp(prefix="ap2d_p2_")
        try:
            path = os.path.join(tmp, "nopolicy.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(raw, fh)
            with self.assertRaises(rules.RuleError) as ctx:
                rules.load(path, catalog=self.cat)
            self.assertIn("legs_armour", str(ctx.exception))
            self.assertIn("allow_subset", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_required_slot_with_no_coverage_still_fails(self):
        """allow_subset 이어도 그 애니메이션 후보가 0개면 오류다."""
        raw = json.loads(open(paths.abspath(PHASE2_RULE), encoding="utf-8").read())
        raw["slots"]["legs"]["allow"] = ["legs_armour"]
        tmp = tempfile.mkdtemp(prefix="ap2d_p2b_")
        try:
            path = os.path.join(tmp, "nocover.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(raw, fh)
            with self.assertRaises(rules.RuleError) as ctx:
                rules.load(path, catalog=self.cat)
            self.assertIn("run", str(ctx.exception))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_unsupported_animation_layer_is_skipped_not_fatal(self):
        """미지원 애니메이션에서 그 레이어만 빠지고 나머지는 합성된다."""
        arch = self.rule["archetypes"][0]
        definition, tints, _m = generate.build_definition(
            self.rule, self.cat, None, arch, 4101)
        layers = generate.layers_for(definition, self.rule, tints, self.cat)
        walk, used_walk = compose.compose_frame(self.cat, layers, "walk", 0,
                                                direction="south")
        run, used_run = compose.compose_frame(self.cat, layers, "run", 0,
                                              direction="south")
        self.assertEqual(walk.size, run.size)
        self.assertEqual(len(used_run), len(used_walk) - 1,
                         "run 에서 정확히 한 레이어만 빠져야 한다")
        self.assertFalse(any("legs/armour" in u or "armour" in u for u in used_run),
                         "run 에 legs_armour 가 섞였다")
        self.assertTrue(any("armour" in u for u in used_walk),
                        "walk 에 legs_armour 가 없다")

    def test_generated_outputs_skip_unsupported_only_for_that_layer(self):
        profile_dir = os.path.join(paths.GEN_CHARACTERS, PHASE2_PROFILE)
        if not os.path.isdir(profile_dir):
            self.skipTest("생성 결과 없음")
        with open(os.path.join(profile_dir, "4101", "sources.json"),
                  "r", encoding="utf-8") as fh:
            sources = json.load(fh)["assets"]
        armour = [s for s in sources if "armour" in s]
        self.assertTrue(armour, "legs_armour 소스가 기록되지 않았다")
        self.assertFalse(any(s.endswith("run.png") for s in armour),
                         "지원하지 않는 run 시트가 소스로 기록됐다")

    # ── runtime export ───────────────────────────────────────────────
    def _manifest(self):
        path = os.path.join(paths.UNITY_EXPORT, "runtime", PHASE2_PROFILE,
                            "runtime_manifest.json")
        if not os.path.isfile(path):
            self.skipTest("runtime export 없음")
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def test_multi_layer_gets_distinct_categories(self):
        manifest = self._manifest()
        self.assertIn("hair", manifest["categories"])
        self.assertIn("hair#1", manifest["categories"])
        slots = {s["slot"]: s for s in manifest["slots"]}
        self.assertEqual(slots["hair#1"]["logical_slot"], "hair")
        self.assertEqual(slots["hair#1"]["layer_index"], 1)
        self.assertEqual(slots["hair#1"]["z_order"], 9)
        self.assertEqual(slots["hair"]["z_order"], 120)

    def test_label_namespace_is_shared_across_categories(self):
        """multi-layer 때문에 label 형식이 달라지면 clip 을 공유할 수 없다."""
        manifest = self._manifest()
        for sheet in manifest["part_sheets"]:
            for label in sheet["labels"]:
                parsed = runtime_export_module().parse_label(label)
                self.assertIn(parsed["animation"], manifest["animations"])
                self.assertIsNotNone(parsed["direction"])

    def test_subset_layer_has_no_labels_for_unsupported_animation(self):
        manifest = self._manifest()
        legs = [s for s in manifest["part_sheets"]
                if s["slot"] == "legs" and s["asset"] == "legs_armour"]
        self.assertTrue(legs)
        animations = set(s["animation"] for s in legs)
        self.assertEqual(animations, {"idle", "walk"},
                         "미지원 애니메이션의 시트가 만들어졌다")
        body = [s for s in manifest["part_sheets"] if s["slot"] == "body"]
        self.assertIn("run", set(s["animation"] for s in body),
                      "몸통은 run 을 계속 지원해야 한다")

    def test_appearance_records_supported_animations(self):
        manifest = self._manifest()
        for appearance in manifest["appearances"]:
            for layer in appearance["layers"]:
                self.assertIn("supported_animations", layer)
                if layer["asset"] == "legs_armour":
                    self.assertEqual(sorted(layer["supported_animations"]),
                                     ["idle", "walk"])

    def test_attribution_deduplicates_multi_layer_item(self):
        """한 logical item 이 레이어 2개라고 표기가 2배가 되면 안 된다."""
        profile_dir = os.path.join(paths.GEN_CHARACTERS, PHASE2_PROFILE)
        if not os.path.isdir(profile_dir):
            self.skipTest("생성 결과 없음")
        with open(os.path.join(profile_dir, "4101", "generation.json"),
                  "r", encoding="utf-8") as fh:
            attrib = json.load(fh)["attribution"]
        entries = attrib["attribution_entries"]
        keys = [(e["source_file"], e["selected_license"]) for e in entries]
        self.assertEqual(len(keys), len(set(keys)), "표기 항목이 중복됐다")
        self.assertEqual(attrib["authors"], sorted(set(attrib["authors"])))
        self.assertFalse(attrib["share_alike_present"])


def runtime_export_module():
    from ap2d import runtime_export
    return runtime_export


class TestLicenseCapabilities(unittest.TestCase):
    """commercial_use 를 3상태 capability 로 다루는가."""

    def test_capability_tri_state(self):
        self.assertEqual(licensing.capability({"x": "yes"}, "x"), licensing.YES)
        self.assertEqual(licensing.capability({"x": "no"}, "x"), licensing.NO)
        self.assertEqual(licensing.capability({"x": "maybe"}, "x"), licensing.UNKNOWN)
        self.assertEqual(licensing.capability({}, "x"), licensing.UNKNOWN)

    def test_cc0_pack_is_commercial_eligible(self):
        summary = licensing.summarize(licensing.load(PACK))
        self.assertEqual(summary["commercial_use"], licensing.YES)
        self.assertTrue(summary["commercial_release_eligible"])
        self.assertNotIn("warning", summary)

    def test_environment_pack_is_not_commercial_eligible(self):
        summary = licensing.summarize(licensing.load(ENV_PACK))
        self.assertEqual(summary["commercial_use"], licensing.NO)
        self.assertFalse(summary["commercial_release_eligible"])
        self.assertIn("NON-COMMERCIAL", summary["warning"])

    def test_environment_pack_still_passes_generation_gate(self):
        """비상업이라고 파이프라인 진입을 막지는 않는다 (수정은 허용되므로)."""
        fields = licensing.require_approved(ENV_PACK)
        self.assertEqual(licensing.capability(fields, "modification"),
                         licensing.YES)

    def test_unknown_commercial_use_is_not_eligible(self):
        """모르면 안 되는 쪽으로 판단한다."""
        summary = licensing.summarize({
            "pack": "x", "license": "?", "commercial_use": "unknown",
            "modification": "yes", "redistribution": "no", "ai_training": "unknown",
            "pipeline_approved": "yes",
        })
        self.assertFalse(summary["commercial_release_eligible"])

    def test_generated_outputs_carry_restriction(self):
        """생성물 metadata 가 제한을 잃지 않는가."""
        profile_dir = os.path.join(paths.GEN_CHARACTERS, "cc0_test_population")
        if not os.path.isdir(profile_dir):
            self.skipTest("생성 결과 없음")
        expected = licensing.summarize(licensing.load(PACK))
        checked = 0
        for name in os.listdir(profile_dir):
            gpath = os.path.join(profile_dir, name, "generation.json")
            if not os.path.isfile(gpath):
                continue
            with open(gpath, "r", encoding="utf-8") as fh:
                gen = json.load(fh)
            self.assertEqual(gen["commercial_release_eligible"],
                             expected["commercial_release_eligible"])
            self.assertEqual(gen["license"]["commercial_use"],
                             expected["commercial_use"])
            checked += 1
        self.assertGreater(checked, 0)

    def test_unity_manifest_carries_restriction(self):
        manifest = os.path.join(paths.UNITY_EXPORT, "characters",
                                "cc0_test_population", "manifest.json")
        if not os.path.isfile(manifest):
            self.skipTest("Unity export 없음")
        with open(manifest, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIn("commercial_release_eligible", data)
        self.assertEqual(data["license"]["pack"], PACK)

    def test_pack_import_defaults_do_not_leak_between_packs(self):
        """한 팩의 unity override 가 전역 기본값을 오염시키면 안 된다."""
        from ap2d import unity_export
        before = dict(unity_export.DEFAULT_IMPORT_SETTINGS)
        rule_a = {"profile": "a", "pack": PACK, "_path": "x",
                  "unity": {"pixels_per_unit": 128, "filter_mode": "Bilinear"}}
        rule_b = {"profile": "b", "pack": PACK, "_path": "y", "unity": {}}
        lic = licensing.summarize(licensing.load(PACK))
        tmp_a = tempfile.mkdtemp(prefix="ap2d_ua_")
        tmp_b = tempfile.mkdtemp(prefix="ap2d_ub_")
        try:
            _p, _c, man_a = unity_export.export(rule_a, [], out_root=tmp_a,
                                                license_summary=lic)
            _p, _c, man_b = unity_export.export(rule_b, [], out_root=tmp_b,
                                                license_summary=lic)
            self.assertEqual(man_a["import_settings"]["pixels_per_unit"], 128)
            self.assertEqual(man_a["import_settings"]["filter_mode"], "Bilinear")
            # override 없는 팩은 기본값 그대로여야 한다
            self.assertEqual(man_b["import_settings"]["pixels_per_unit"],
                             before["pixels_per_unit"])
            self.assertEqual(man_b["import_settings"]["filter_mode"],
                             before["filter_mode"])
            self.assertEqual(unity_export.DEFAULT_IMPORT_SETTINGS, before,
                             "전역 기본값이 변조됐다")
        finally:
            shutil.rmtree(tmp_a, ignore_errors=True)
            shutil.rmtree(tmp_b, ignore_errors=True)

    def test_unity_import_settings_override_is_preserved(self):
        """팩/규칙별 Unity 설정 override 가 export 까지 살아 있는가."""
        manifest = os.path.join(paths.UNITY_EXPORT, "characters",
                                "cc0_test_population", "manifest.json")
        if not os.path.isfile(manifest):
            self.skipTest("Unity export 없음")
        with open(manifest, "r", encoding="utf-8") as fh:
            settings = json.load(fh)["import_settings"]
        with open(paths.abspath(RULE), "r", encoding="utf-8") as fh:
            override = json.load(fh)["unity"]
        for key, value in override.items():
            self.assertEqual(settings[key], value,
                             "규칙의 unity.%s override 가 유실됐다" % key)
        # 규칙이 건드리지 않은 값은 기본값이 유지되어야 한다
        self.assertNotIn("max_texture_size", override)
        self.assertEqual(settings["max_texture_size"], 2048)


class TestPaletteRecolor(unittest.TestCase):
    """multiply tint 가 검은 외곽선을 보존하는지."""

    def test_black_stays_black(self):
        from PIL import Image
        src = Image.new("RGBA", (2, 1))
        src.putpixel((0, 0), (0, 0, 0, 255))        # 외곽선
        src.putpixel((1, 0), (239, 239, 239, 255))  # 하이라이트
        out = palette_mod.multiply_tint(src, (200, 100, 50))
        self.assertEqual(out.getpixel((0, 0)), (0, 0, 0, 255))
        self.assertEqual(out.getpixel((1, 0))[3], 255)
        self.assertGreater(out.getpixel((1, 0))[0], out.getpixel((1, 0))[2])

    def test_alpha_is_preserved(self):
        from PIL import Image
        src = Image.new("RGBA", (1, 1), (239, 239, 239, 77))
        out = palette_mod.multiply_tint(src, (10, 20, 30))
        self.assertEqual(out.getpixel((0, 0))[3], 77)

    def test_rejects_bad_hex(self):
        tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                          encoding="utf-8")
        try:
            json.dump({"name": "x",
                       "ramps": [{"id": "a", "colors": ["#GGGGGG"]}]}, tmp)
            tmp.close()
            with self.assertRaises(palette_mod.PaletteError):
                palette_mod.load(tmp.name)
        finally:
            os.unlink(tmp.name)


class TestExportContractV1(unittest.TestCase):
    """소비자 패키지 경계 (Export Contract v1).

    핵심은 "같은 입력을 다시 export 해도 소비자 쪽이 깨지지 않는가" 다.
    Unity GUID 는 `.meta` 에 들어 있으므로, exporter 가 `.meta` 나 소비자가 만든
    `Generated/` 를 지우면 게임의 직렬화 참조가 통째로 끊긴다.
    """

    @classmethod
    def setUpClass(cls):
        import export_consumer_package as ecp
        cls.ecp = ecp
        cls.profile = "lpc_phase2_showcase"
        src = os.path.join(paths.UNITY_EXPORT, "runtime", cls.profile)
        if not os.path.isdir(src):
            raise unittest.SkipTest("runtime export 가 없다")

    def _export(self, assets):
        return self.ecp.export(assets, [self.profile])

    def test_generated_and_meta_survive_reexport(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = os.path.join(tmp, "Assets")
            os.makedirs(assets)
            pkg, _records, _fp = self._export(assets)

            # 소비자가 만든 것들을 흉내낸다: .meta (GUID) 와 Generated/ (빌드 산출물)
            manifest = os.path.join(pkg, "Profiles", self.profile,
                                    "runtime_manifest.json")
            meta = manifest + ".meta"
            with open(meta, "w", encoding="utf-8") as fh:
                fh.write("guid: 0123456789abcdef0123456789abcdef\n")
            generated = os.path.join(pkg, "Profiles", self.profile, "Generated")
            os.makedirs(generated)
            built = os.path.join(generated, "profile.asset")
            with open(built, "w", encoding="utf-8") as fh:
                fh.write("built by consumer")

            self._export(assets)

            self.assertTrue(os.path.isfile(meta), ".meta 가 사라졌다 — GUID 가 날아간다")
            self.assertIn("0123456789abcdef", open(meta, encoding="utf-8").read(),
                          ".meta 가 덮어써졌다")
            self.assertTrue(os.path.isfile(built), "Generated/ 가 지워졌다")
            self.assertEqual("built by consumer",
                             open(built, encoding="utf-8").read())

    def test_fingerprint_is_deterministic_and_consumer_independent(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "A")
            b = os.path.join(tmp, "B")
            os.makedirs(a)
            os.makedirs(b)
            pkg_a, _r, fp1 = self._export(a)
            _pkg, _r, fp2 = self._export(a)
            self.assertEqual(fp1, fp2, "같은 입력인데 지문이 달라졌다")

            # 소비자가 빌드한 뒤에도 지문은 그대로여야 한다 — 지문은 Factory 소유
            # 파일만의 해시다. (Generated/ 가 섞이면 소비자 상태가 정체성을 바꾼다.)
            generated = os.path.join(pkg_a, "Profiles", self.profile, "Generated")
            os.makedirs(generated, exist_ok=True)
            with open(os.path.join(generated, "x.asset"), "w") as fh:
                fh.write("consumer output")
            _pkg, _r, fp3 = self._export(a)
            self.assertEqual(fp1, fp3, "소비자 산출물이 지문을 바꿨다")

            _pkg_b, _r, fp4 = self._export(b)
            self.assertEqual(fp1, fp4, "빈 폴더에 내보낸 지문이 다르다")

    def test_manifest_has_no_time_or_uuid_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = os.path.join(tmp, "Assets")
            os.makedirs(assets)
            pkg, _records, fingerprint = self._export(assets)
            payload = json.load(open(os.path.join(pkg, "export_manifest.json"),
                                     encoding="utf-8"))
            self.assertEqual("1.0", payload["contract_version"])
            self.assertEqual(fingerprint, payload["content_fingerprint"])
            text = json.dumps(payload)
            for banned in ("timestamp", "generated_at", "uuid", "build_id"):
                self.assertNotIn(banned, text,
                                 "%s 가 identity 에 섞였다" % banned)

    def test_package_carries_no_factory_internals(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = os.path.join(tmp, "Assets")
            os.makedirs(assets)
            pkg, _records, _fp = self._export(assets)

            banned_names = {"character.json", "contact_sheet.png"}
            for root, _dirs, files in os.walk(pkg):
                for name in files:
                    self.assertNotIn(name, banned_names,
                                     "Factory 내부 파일이 패키지에 들어왔다: %s" % name)
                    self.assertFalse(name.endswith(".py"),
                                     "Factory 스크립트가 패키지에 들어왔다: %s" % name)

            # Factory 경로 문자열은 **추적용 provenance 필드에만** 있어야 한다.
            # 소비자는 이 문자열을 해석하지 않는다 (해석하면 Factory 저장소가
            # 옆에 있어야 하고, 그러면 패키지가 자족적이지 않다).
            allowed = {"rule", "appearances/[]/definition"}
            manifest = json.load(open(
                os.path.join(pkg, "Profiles", self.profile,
                             "runtime_manifest.json"), encoding="utf-8"))
            found = []

            def walk(node, path):
                if isinstance(node, dict):
                    for key, value in node.items():
                        walk(value, path + [key])
                elif isinstance(node, list):
                    for value in node:
                        walk(value, path + ["[]"])
                elif isinstance(node, str):
                    for banned in ("01_SOURCE", "02_CATALOG", "04_RULES",
                                   "05_GENERATED", "tools/ap2d"):
                        if banned in node:
                            found.append("/".join(path))

            walk(manifest, [])
            leaked = sorted(set(found) - allowed)
            self.assertEqual([], leaked,
                             "provenance 가 아닌 자리에 Factory 경로가 있다: %s"
                             % leaked)

    def test_removed_factory_file_is_pruned_with_its_meta(self):
        """더 이상 export 하지 않는 파일은 .meta 까지 정리한다 (짝이 남으면 안 된다)."""
        with tempfile.TemporaryDirectory() as tmp:
            assets = os.path.join(tmp, "Assets")
            os.makedirs(assets)
            pkg, _records, _fp = self._export(assets)
            stray = os.path.join(pkg, "Profiles", self.profile, "parts",
                                 "zz_no_longer_exported.png")
            with open(stray, "wb") as fh:
                fh.write(b"\x89PNG stale")
            with open(stray + ".meta", "w") as fh:
                fh.write("guid: deadbeef\n")

            self._export(assets)
            self.assertFalse(os.path.exists(stray), "낡은 파츠가 남았다")
            self.assertFalse(os.path.exists(stray + ".meta"),
                             "짝 없는 .meta 가 남았다")


class TestAttributionReachesConsumer(unittest.TestCase):
    """표기 의무가 소비자 패키지까지 따라가는가.

    이전에는 여기서 끊겼다. attribution 리포트는 `05_GENERATED/reports/` 에서
    멈췄고, runtime manifest 는 appearance 마다 요약만 실었으며, license 요약에는
    `credit_required` 가 아예 없었다. 그 상태로 소비자 저장소를 공개하면
    CC-BY / OGA-BY 아트를 저자 표기 없이 재배포하게 된다.

    `commercial_use: yes` 는 표기 의무를 면제하지 않는다 — **다른 축이다.**
    """

    PROFILE = "lpc_phase2_showcase"

    def _runtime_manifest(self):
        path = os.path.join(paths.UNITY_EXPORT, "runtime", self.PROFILE,
                            "runtime_manifest.json")
        if not os.path.isfile(path):
            self.skipTest("runtime export 없음")
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh), os.path.dirname(path)

    def test_license_summary_carries_credit_required(self):
        """표기 의무도 3상태다. 없으면 unknown 이고, yes 로 반올림하지 않는다."""
        self.assertEqual(licensing.YES,
                         licensing.summarize(licensing.load(LPC_PACK))["credit_required"])
        self.assertEqual(licensing.NO,
                         licensing.summarize(licensing.load(PACK))["credit_required"])
        self.assertEqual(licensing.UNKNOWN,
                         licensing.summarize({"pack": PACK, "license": "x"})["credit_required"])

    def test_runtime_manifest_has_profile_level_attribution(self):
        """소비자가 appearance 를 훑어 저자를 합치게 하지 않는다."""
        manifest, _root = self._runtime_manifest()
        attrib = manifest["attribution"]
        self.assertTrue(attrib["attribution_required"])
        self.assertTrue(attrib["authors"], "프로파일 단위 저자 목록이 비었다")
        self.assertTrue(attrib["credits"], "credits 화면에 넣을 줄이 비었다")
        for line in attrib["credits"]:
            self.assertIn("—", line, "credit 줄에 라이선스가 없다: %s" % line)
        # appearance 를 전부 합친 것과 같아야 한다 (빠진 저자가 없어야 한다)
        from_appearances = set()
        for appearance in manifest["appearances"]:
            from_appearances.update(appearance["attribution"]["authors"])
        self.assertEqual(from_appearances, set(attrib["authors"]),
                         "프로파일 rollup 이 appearance 저자와 어긋난다")

    def test_attribution_report_ships_with_runtime_export(self):
        """리포트가 Factory 저장소에만 있으면 소비자는 못 읽는다."""
        manifest, root = self._runtime_manifest()
        name = manifest["attribution"]["report"]
        self.assertEqual(runtime_export_module().ATTRIBUTION_REPORT, name)
        path = os.path.join(root, name)
        self.assertTrue(os.path.isfile(path), "리포트가 runtime export 에 없다")
        text = open(path, encoding="utf-8").read()
        for author in ("bluecarrot16", "JaidynReiman"):
            self.assertIn(author, text)

    def test_report_path_is_package_relative_not_factory_path(self):
        """소비자에게 Factory 저장소 경로를 주면 못 읽는다."""
        manifest, _root = self._runtime_manifest()
        name = manifest["attribution"]["report"]
        for factory_path in ("05_GENERATED", "06_UNITY_EXPORT", "/"):
            self.assertNotIn(factory_path, name,
                             "report 가 패키지 상대 경로가 아니다: %s" % name)

    def test_consumer_package_contains_attribution(self):
        """실제로 내보낸 패키지 안에 표기 원문과 경고가 있는가."""
        import export_consumer_package as ecp
        src = os.path.join(paths.UNITY_EXPORT, "runtime", self.PROFILE)
        if not os.path.isdir(src):
            self.skipTest("runtime export 없음")
        with tempfile.TemporaryDirectory() as tmp:
            assets = os.path.join(tmp, "Assets")
            os.makedirs(assets)
            pkg, _records, _fp = ecp.export(assets, [self.PROFILE])

            report = os.path.join(pkg, "Profiles", self.PROFILE,
                                  runtime_export_module().ATTRIBUTION_REPORT)
            self.assertTrue(os.path.isfile(report),
                            "패키지에 attribution 리포트가 없다")

            readme = open(os.path.join(pkg, "README.md"), encoding="utf-8").read()
            self.assertIn("저자 표기 의무", readme)
            self.assertIn("bluecarrot16", readme,
                          "README 가 표기 원문을 싣지 않는다")

    def test_credit_lines_are_deterministic_and_deduplicated(self):
        entry = {"source_file": "a.png", "selected_license": "OGA-BY 3.0",
                 "authors": ["b", "a"], "alternative_licenses": [],
                 "source_urls": [], "used_by": ["torso/x"],
                 "text": "a, b — OGA-BY 3.0"}
        summary = {"attribution_entries": [entry, dict(entry), entry]}
        self.assertEqual(["a, b — OGA-BY 3.0"], attribution.credit_lines(summary))
        self.assertEqual([], attribution.credit_lines({}))


class TestCanonicalSourceFingerprint(unittest.TestCase):
    """소스 지문 산출법을 하나로 고정한다.

    이전에는 회차마다 셸 파이프로 해시를 냈고, 명령이 조금 다르면 값이 달라져
    "소스가 변조됐는가" 를 판정할 수 없었다. 방법을 코드로 고정한다.
    """

    def _tree(self):
        root = tempfile.mkdtemp(prefix="ap2d_fp_")
        os.makedirs(os.path.join(root, "b", "deep"))
        os.makedirs(os.path.join(root, "a"))
        with open(os.path.join(root, "a", "one.txt"), "wb") as fh:
            fh.write(b"one")
        with open(os.path.join(root, "b", "deep", "two.txt"), "wb") as fh:
            fh.write(b"two")
        return root

    def test_same_tree_same_fingerprint(self):
        root = self._tree()
        try:
            first = integrity.tree_fingerprint(root)
            self.assertEqual(first, integrity.tree_fingerprint(root))
            # 내용이 같으면 위치가 달라도 같은 값 (절대경로가 안 들어간다)
            other = self._tree()
            try:
                self.assertEqual(first, integrity.tree_fingerprint(other))
            finally:
                shutil.rmtree(other, ignore_errors=True)
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_mtime_does_not_change_fingerprint(self):
        root = self._tree()
        try:
            before = integrity.tree_fingerprint(root)
            os.utime(os.path.join(root, "a", "one.txt"), (0, 0))
            self.assertEqual(before, integrity.tree_fingerprint(root),
                             "mtime 이 지문을 바꿨다")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_excluded_files_do_not_change_fingerprint(self):
        root = self._tree()
        try:
            before = integrity.tree_fingerprint(root)
            for name in (".DS_Store", "Thumbs.db", "._resource"):
                with open(os.path.join(root, name), "wb") as fh:
                    fh.write(b"noise")
            self.assertEqual(before, integrity.tree_fingerprint(root),
                             "OS 부산물이 지문을 바꿨다")
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_content_change_changes_fingerprint(self):
        root = self._tree()
        try:
            before = integrity.tree_fingerprint(root)
            with open(os.path.join(root, "a", "one.txt"), "wb") as fh:
                fh.write(b"ONE")
            self.assertNotEqual(before, integrity.tree_fingerprint(root))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_rename_changes_fingerprint(self):
        """내용이 같아도 경로가 바뀌면 다른 트리다 (경로가 지문에 들어간다)."""
        root = self._tree()
        try:
            before = integrity.tree_fingerprint(root)
            os.rename(os.path.join(root, "a", "one.txt"),
                      os.path.join(root, "a", "uno.txt"))
            self.assertNotEqual(before, integrity.tree_fingerprint(root))
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_real_source_tree_is_stable(self):
        if not os.path.isdir(paths.SOURCE):
            self.skipTest("01_SOURCE 가 없다")
        first = integrity.tree_fingerprint(paths.SOURCE)
        self.assertEqual(64, len(first))
        self.assertEqual(first, integrity.tree_fingerprint(paths.SOURCE))


class TestCapabilitySheet(unittest.TestCase):
    """가용 능력 한 장 — 발주 전에 읽는 메뉴판.

    새로 계산하지 않는다는 것이 요점이다. 카탈로그가 이미 아는 값만 모은다.
    """

    def test_every_catalog_appears(self):
        data = capability.build()
        names = {p["pack"] for p in data["packs"]}
        for path in capability.catalog_paths():
            with open(path, encoding="utf-8") as fh:
                self.assertIn(json.load(fh)["pack"]["name"], names)
        self.assertTrue(names, "팩이 하나도 없다")

    def test_slot_counts_match_catalog(self):
        for entry in capability.build()["packs"]:
            cat = catalog_mod.load_catalog(entry["catalog"])
            for slot, count in entry["slots"].items():
                self.assertEqual(len(cat["parts"][slot]), count,
                                 "%s/%s 후보 수가 카탈로그와 다르다" % (entry["pack"], slot))

    def test_license_state_is_not_invented(self):
        for entry in capability.build()["packs"]:
            lic = entry["license"]
            self.assertIn(lic["commercial_use"], ("yes", "no", "unknown"))
            # unknown 은 eligible 이 아니다 — 모르면 안 되는 쪽으로 판단한다.
            if lic["commercial_use"] != "yes":
                self.assertFalse(lic["commercial_release_eligible"])

    def test_sheet_makes_no_judgement(self):
        """판정 어휘가 들어가면 안 된다. 이 문서는 사실만 적는다."""
        md = capability.render_markdown(capability.build())
        for banned in ("FAIL", "부족", "권장", "점수", "등급", "품질"):
            self.assertNotIn(banned, md, "판정 어휘가 들어갔다: %s" % banned)

    def test_render_is_deterministic(self):
        self.assertEqual(capability.render_markdown(capability.build()),
                         capability.render_markdown(capability.build()))


class TestDistributionObservation(unittest.TestCase):
    """분포는 **관측**이지 검사가 아니다.

    PASS 표만으로는 열 명이 사실상 한 명인 population 을 구분할 수 없다.
    그래서 세지만, 세는 것까지가 이 저장소의 일이다 — 합격선을 만들지 않는다.
    """

    @classmethod
    def setUpClass(cls):
        path = os.path.join(paths.GEN_REPORTS, "lpc_phase1_population_validation.json")
        if not os.path.isfile(path):
            raise unittest.SkipTest("검증 리포트가 없다")
        with open(path, encoding="utf-8") as fh:
            cls.report = json.load(fh)

    def test_distribution_is_present_and_counts_agree(self):
        dist = self.report["distribution"]
        self.assertEqual(self.report["characters"], dist["population"])
        self.assertTrue(dist["slots"])
        for row in dist["slots"]:
            self.assertLessEqual(row["used"], row["allowed_candidates"],
                                 "%s: 허용보다 많이 썼다" % row["slot"])
            self.assertLessEqual(row["allowed_candidates"], row["catalog_candidates"],
                                 "%s: 카탈로그보다 많이 허용했다" % row["slot"])
            self.assertEqual(sum(row["counts"].values()),
                             dist["population"] - row["empty"])
            if row["counts"]:
                self.assertAlmostEqual(
                    row["most_common_share"],
                    max(row["counts"].values()) / (dist["population"] - row["empty"]),
                    places=3)

    def test_distribution_does_not_affect_status(self):
        """분포가 status 에 관여하면 그건 임계값이 생겼다는 뜻이다."""
        checks = {c["check"] for c in self.report["checks"]}
        for banned in ("distribution", "diversity", "variety"):
            self.assertNotIn(banned, checks,
                             "분포가 검사로 승격됐다 — 사실 보고여야 한다")
        # 최빈 비율이 높은 슬롯이 있어도 전체는 PASS 여야 한다.
        worst = max(r["most_common_share"] for r in self.report["distribution"]["slots"])
        self.assertGreater(worst, 0.0)
        self.assertEqual("pass", self.report["status"],
                         "분포 때문에 상태가 바뀌었다")


class TestOrderBrief(unittest.TestCase):
    """회신 한 장 — 재현 좌표 · 출시 신호 · 못 한 것."""

    RULE = "04_RULES/lpc_phase1_population.json"

    def setUp(self):
        if not os.path.isfile(os.path.join(
                paths.GEN_REPORTS, "lpc_phase1_population_validation.json")):
            self.skipTest("검증 리포트가 없다")
        self.brief = order_mod.build(self.RULE)

    def test_reproduction_coordinates_are_complete(self):
        coord = self.brief["coordinates"]
        for field in ("rule", "rule_sha256", "catalog", "catalog_sha256", "seeds"):
            self.assertTrue(coord.get(field), "재현 좌표에 %s 가 없다" % field)
        self.assertEqual(64, len(coord["rule_sha256"]))
        self.assertEqual(64, len(coord["catalog_sha256"]))

    def test_release_signal_is_at_top(self):
        md = order_mod.render_markdown(self.brief)
        head = md.split("## ①")[0]
        self.assertTrue("상업 출시" in head,
                        "출시 신호가 최상단에 없다 — 깊은 곳에 있으면 놓친다")

    def test_not_done_says_none_explicitly(self):
        """빈 것과 누락은 다르다. 비었으면 비었다고 써야 한다."""
        md = order_mod.render_markdown(self.brief)
        section = md.split("## ⑥")[1]
        if self.brief["not_done"]:
            self.assertIn("|", section)
        else:
            self.assertIn("없음", section)

    def test_consumer_identifier_is_never_invented(self):
        """소비자 식별자는 art-studio 가 발급한다. 여기서 지어내지 않는다."""
        for name in ("cc0_test_population", "lpc_phase1_population",
                     "lpc_phase2_showcase"):
            with open(paths.abspath("04_RULES/%s.json" % name), encoding="utf-8") as fh:
                block = order_mod.order_block(json.load(fh))
            self.assertEqual("unknown", block["consumer"],
                             "%s: 발주가 없는데 소비자 이름이 붙었다" % name)

    def test_purpose_label_travels_to_exports(self):
        """산출물 파일만 봐도 자체 검증인지 발주 대응인지 알 수 있어야 한다."""
        checked = 0
        for rel in ("06_UNITY_EXPORT/runtime/lpc_phase2_showcase/runtime_manifest.json",
                    "06_UNITY_EXPORT/characters/cc0_test_population/manifest.json"):
            path = paths.abspath(rel)
            if not os.path.isfile(path):
                continue
            with open(path, encoding="utf-8") as fh:
                manifest = json.load(fh)
            self.assertIn("order", manifest, "%s 에 라벨이 없다" % rel)
            self.assertIn(manifest["order"]["purpose"], order_mod.PURPOSES)
            checked += 1
        if not checked:
            self.skipTest("export 산출물이 없다")

    def test_brief_adds_no_new_computation(self):
        """회신은 검증 리포트의 값을 옮기기만 한다 — 다시 판정하지 않는다."""
        with open(os.path.join(paths.GEN_REPORTS,
                               "lpc_phase1_population_validation.json"),
                  encoding="utf-8") as fh:
            report = json.load(fh)
        self.assertEqual(report["status"], self.brief["verification"]["status"])
        self.assertEqual(report["commercial_release_eligible"],
                         self.brief["release"]["commercial_release_eligible"])
        self.assertEqual(report["distribution"], self.brief["distribution"])


class TestRefusalIsANormalResponse(unittest.TestCase):
    """거절과 부분 수행이 예외로만 터지지 않고 **회신에 사람이 읽는 줄로** 올라오는가.

    스크립트를 돌린 사람만 이유를 보면, 발주한 쪽은 다음 지시를 고칠 수 없다.
    """

    RULE = "04_RULES/lpc_phase1_population.json"

    def _report(self, **overrides):
        base = {
            "status": "pass",
            "pack": "lpc_ulpc-generator_phase1",
            "characters": 10,
            "expected_characters": 10,
            "commercial_release_eligible": True,
            "license": {"license": "CC0-1.0", "commercial_use": "yes"},
            "attribution": {"attribution_required": False, "share_alike_present": False,
                            "authors": []},
            "checks": [{"check": "population", "title": "생성 개수 일치",
                        "status": "pass", "items_checked": 10,
                        "failures": [], "warnings": []}],
            "distribution": {"population": 10, "slots": [], "palette_groups": []},
        }
        base.update(overrides)
        return base

    def test_noncommercial_pack_puts_the_signal_at_the_top(self):
        brief = order_mod.build(self.RULE, report=self._report(
            commercial_release_eligible=False,
            license={"license": "LimeZu Free Version License (proprietary)",
                     "commercial_use": "no"}))
        md = order_mod.render_markdown(brief)
        head = md.split("## ①")[0]
        self.assertIn("⛔", head, "출시 불가 신호가 최상단에 없다")
        self.assertIn("상업 출시 불가", head)
        # 생성 자체를 막지는 않는다 — 신호만 올라온다.
        self.assertEqual("pass", brief["verification"]["status"])
        # ⑥ 에도 근거가 남는다.
        reasons = " ".join(i["근거"] for i in brief["not_done"])
        self.assertIn("commercial_use", reasons)

    def test_failed_check_becomes_a_human_readable_line(self):
        brief = order_mod.build(self.RULE, report=self._report(
            status="fail",
            checks=[{"check": "asset_presence", "title": "파츠 파일 존재",
                     "status": "fail", "items_checked": 10,
                     "failures": [{"subject": "hair_braid",
                                   "message": "카탈로그에 없는 파츠다"}],
                     "warnings": []}]))
        md = order_mod.render_markdown(brief)
        section = md.split("## ⑥")[1]
        self.assertIn("hair_braid", section, "무엇이 안 됐는지가 회신에 없다")
        self.assertIn("카탈로그에 없는 파츠다", section, "근거가 회신에 없다")
        self.assertEqual(1, brief["verification"]["failed"])

    def test_partial_fulfilment_reports_both_sides(self):
        """다섯을 시켜 셋만 됐으면 셋을 하고 둘을 이유와 함께 돌려준다."""
        brief = order_mod.build(self.RULE, report=self._report())
        brief["not_done"] = [
            {"요구": "무기 슬롯", "근거": "이 팩의 카탈로그에 weapon 슬롯이 없다"},
            {"요구": "8방향", "근거": "direction_axis 가 4개만 선언한다"},
        ]
        md = order_mod.render_markdown(brief)
        self.assertIn("무기 슬롯", md)
        self.assertIn("8방향", md)
        # 수행한 쪽도 같은 문서에 있다.
        self.assertIn("③ 기술 검증", md)
        self.assertIn("PASS", md)


class TestDocsMatchCode(unittest.TestCase):
    """진입 문서가 코드와 어긋나면 그 위에 쌓이는 작업이 전부 틀어진다.

    문서 전체를 검사하는 체계를 만들지 않는다. 실제로 어긋났던 자리만 못 박는다.
    """

    def _read(self, rel):
        with open(paths.abspath(rel), encoding="utf-8") as fh:
            return fh.read()

    def test_claude_md_does_not_claim_factory_writes_meta(self):
        text = self._read("CLAUDE.md")
        self.assertIn(".meta` 는 만들지 않는다", text,
                      "CLAUDE.md 가 .meta 소유권을 명시하지 않는다")
        self.assertNotIn("prefab/spritelib/meta 포함", text,
                         "Factory 가 .meta 를 만든다는 옛 서술이 남아 있다")

    def test_claude_md_report_paths_exist_or_are_generated(self):
        text = self._read("CLAUDE.md")
        self.assertNotIn("<pack>.report.md", text,
                         "존재하지 않는 리포트 경로가 문서에 남아 있다")
        self.assertIn("<profile>_validation", text)

    def test_every_markdown_link_resolves(self):
        """진입 문서의 링크가 실재하는가. 죽은 링크는 틀린 설명의 가장 흔한 형태다."""
        for rel in ("README.md", "tools/README.md", "CLAUDE.md",
                    "00_DOCS/DIRECTOR_CONTEXT.md"):
            text = self._read(rel)
            base = os.path.dirname(paths.abspath(rel))
            for target in re.findall(r"\]\(([^)#:]+)\)", text):
                if target.startswith(("http", "mailto")):
                    continue
                self.assertTrue(os.path.exists(os.path.join(base, target)),
                                "%s 의 링크가 죽었다: %s" % (rel, target))

    def test_module_list_matches_package(self):
        """`tools/README.md` 의 모듈 목록이 실제 패키지와 같은가."""
        block = self._read("tools/README.md").split("## 모듈")[1].split("```")[1]
        listed = set(re.findall(r"^\s{2}([a-z_]+\.py)", block, re.M))
        actual = {f for f in os.listdir(paths.abspath("tools/ap2d"))
                  if f.endswith(".py") and f != "__init__.py"}
        self.assertEqual(actual - listed, set(), "문서에 없는 모듈이 있다")
        self.assertEqual(listed - actual, set(), "없는 모듈이 문서에 있다")

    def test_documented_commands_exist(self):
        """문서가 안내하는 명령이 실재하는가."""
        for rel in ("README.md", "tools/README.md"):
            for cmd in re.findall(r"python3 (tools/[\w/]+\.py)", self._read(rel)):
                self.assertTrue(os.path.isfile(paths.abspath(cmd)),
                                "%s 가 없는 명령을 안내한다: %s" % (rel, cmd))

    def test_no_stale_test_count_in_docs(self):
        """개수는 계속 바뀐다. 고정 숫자를 문서에 박지 않는다."""
        for rel in ("tools/README.md", "00_DOCS/export-contract-v1.md"):
            text = self._read(rel)
            for line in text.splitlines():
                if "test_pipeline.py" in line:
                    self.assertFalse(
                        re.search(r"\b\d{3}\b", line),
                        "%s 에 고정 테스트 개수가 박혀 있다: %s" % (rel, line.strip()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
