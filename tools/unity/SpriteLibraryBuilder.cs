using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.U2D.Animation;

namespace ArtFactory.EditorTools
{
    /// <summary>
    /// `06_UNITY_EXPORT/runtime/&lt;profile&gt;/runtime_manifest.json` 을 읽어
    ///   1) 파츠 시트를 셀 격자로 슬라이스하고
    ///   2) appearance 마다 SpriteLibraryAsset 을 만들고
    ///   3) CharacterAppearance ScriptableObject 를 만들고
    ///   4) CharacterView 프리팹을 만든다.
    ///
    /// 사람이 에디터에서 클릭해 라이브러리를 만들지 않는다. 전부 파이프라인 metadata 기반이다.
    /// 같은 manifest 로 다시 돌리면 같은 결과가 나온다 (결정적).
    /// </summary>
    public static class SpriteLibraryBuilder
    {
        const string ExpectedSchema = "ap2d.unity_runtime/1";

#pragma warning disable 0649
        [Serializable] class Origin { public string policy; public string pivot; public float pixels_per_unit; public int[] logical_cell; }
        [Serializable] class DirectionAxis { public string present; public string encoding; public string[] values; }
        [Serializable] class TopologyEntry { public string animation; public int frame_count; public string[] directions; }

        [Serializable]
        class PartSheet
        {
            public string slot;
            public string asset;
            public string animation;
            public string direction;
            public string file;
            public int frame_count;
            public int cell_width;
            public int cell_height;
            public int[] size;
            public string[] labels;
        }

        [Serializable]
        class LayerRef
        {
            public string slot;
            public string logical_slot;
            public int layer_index;
            public string asset;
            public int z_order;
            public string z_source;
            public string[] supported_animations;
        }
        [Serializable] class ProfileSlot { public string slot; public string logical_slot; public int layer_index; public int z_order; }
        [Serializable] class AttributionRef { public int source_assets; public string[] authors; public string[] licenses; public bool attribution_required; public bool share_alike_present; }

        [Serializable]
        class Appearance
        {
            public int seed;
            public string archetype;
            public string definition;
            public LayerRef[] layers;
            public AttributionRef attribution;
        }

        [Serializable]
        class Manifest
        {
            public string schema;
            public string profile;
            public string pack;
            public string runtime_mode;
            public string[] categories;
            public ProfileSlot[] slots;
            public string[] animations;
            public TopologyEntry[] topology_list;
            public DirectionAxis direction_axis;
            public int frame_rate;
            public Origin origin;
            public string missing_animation_policy;
            public PartSheet[] part_sheets;
            public Appearance[] appearances;
        }
#pragma warning restore 0649

        [MenuItem("2D Art Factory/Build Sprite Libraries")]
        public static void BuildFromMenu()
        {
            string picked = EditorUtility.OpenFilePanel(
                "runtime_manifest.json 고르기", Application.dataPath, "json");
            if (string.IsNullOrEmpty(picked)) return;
            string assetPath = ToAssetPath(picked);
            if (assetPath == null)
            {
                EditorUtility.DisplayDialog("2D Art Factory",
                    "manifest 가 이 프로젝트의 Assets/ 아래에 있어야 한다.", "확인");
                return;
            }
            int built = Build(assetPath);
            EditorUtility.DisplayDialog("2D Art Factory",
                string.Format("appearance {0}개를 만들었다.", built), "확인");
        }

        /// <summary>manifest 하나를 처리한다. 반환값은 만든 appearance 수.</summary>
        public static int Build(string manifestAssetPath)
        {
            string projectRoot = Path.GetDirectoryName(Application.dataPath);
            string absolute = Path.Combine(projectRoot, manifestAssetPath);
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(absolute));

            if (manifest == null || manifest.appearances == null)
                throw new Exception("manifest 를 읽지 못했다: " + manifestAssetPath);
            if (manifest.schema != ExpectedSchema)
                throw new Exception(string.Format("schema 가 {0} 이어야 한다 (현재: {1})",
                                                  ExpectedSchema, manifest.schema));

            string root = Path.GetDirectoryName(manifestAssetPath).Replace('\\', '/');
            string outDir = root + "/Generated";
            EnsureFolder(outDir);

            // 1단계: 파츠 시트를 셀 격자로 슬라이스한다.
            //         자동 격자 검출이 아니라 manifest 가 선언한 cell 크기를 그대로 쓴다.
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (PartSheet sheet in manifest.part_sheets)
                    SliceSheet(root + "/" + sheet.file, sheet, manifest.origin);
            }
            finally
            {
                AssetDatabase.StopAssetEditing();
                AssetDatabase.Refresh();
            }

            // 2단계: (slot, asset) -> label -> Sprite 색인
            var index = new Dictionary<string, Dictionary<string, Sprite>>();
            foreach (PartSheet sheet in manifest.part_sheets)
            {
                string key = sheet.slot + "/" + sheet.asset;
                Dictionary<string, Sprite> byLabel;
                if (!index.TryGetValue(key, out byLabel))
                {
                    byLabel = new Dictionary<string, Sprite>();
                    index[key] = byLabel;
                }
                var loaded = new Dictionary<string, Sprite>();
                foreach (UnityEngine.Object o in
                         AssetDatabase.LoadAllAssetsAtPath(root + "/" + sheet.file))
                {
                    var sprite = o as Sprite;
                    if (sprite != null) loaded[sprite.name] = sprite;
                }
                foreach (string label in sheet.labels)
                {
                    Sprite sprite;
                    if (loaded.TryGetValue(SpriteName(sheet, label), out sprite))
                        byLabel[label] = sprite;
                    else
                        Debug.LogWarningFormat("[2D Art Factory] 스프라이트 없음: {0} ({1})",
                                               label, sheet.file);
                }
            }

            // 3단계: appearance 마다 라이브러리 + 정의 + 프리팹
            int built = 0;
            foreach (Appearance appearance in manifest.appearances)
            {
                SpriteLibraryAsset library = BuildLibrary(manifest, appearance, index, outDir);
                CharacterAppearance definition = BuildDefinition(manifest, appearance,
                                                                 library, outDir);
                BuildPrefab(manifest, definition, outDir);
                built++;
            }

            // 4단계: AnimationClip + AnimatorController.
            //         profile 당 한 벌만 만든다 — 모든 appearance 가 공유한다.
            BuildAnimation(manifest, outDir);

            // 5단계: profile 인덱스. 소비자가 아는 유일한 에셋이다.
            //         이게 없으면 게임 코드가 에셋 경로 규칙을 알아야 한다.
            BuildProfileAsset(manifest, manifestAssetPath, outDir);

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.LogFormat("[2D Art Factory] {0}: appearance {1}개 / 파츠 시트 {2}장",
                            manifest.profile, built, manifest.part_sheets.Length);
            return built;
        }

        /// <summary>controller 생성이 만든 매핑. profile 에셋이 그대로 받아 간다.</summary>
        static Dictionary<string, int> _lastMotionMapping = new Dictionary<string, int>();

        static void BuildProfileAsset(Manifest manifest, string manifestAssetPath,
                                      string outDir)
        {
            string path = string.Format("{0}/{1}_profile.asset", outDir, manifest.profile);
            var asset = AssetDatabase.LoadAssetAtPath<CharacterProfile>(path);
            bool isNew = asset == null;
            if (isNew) asset = ScriptableObject.CreateInstance<CharacterProfile>();

            asset.profile = manifest.profile;
            asset.pack = manifest.pack;
            asset.sourceManifest = manifestAssetPath;
            asset.animations = manifest.animations;
            asset.motionParameterName = AnimationClipBuilder.MotionParameter;
            var motions = new List<CharacterProfile.MotionEntry>();
            foreach (KeyValuePair<string, int> pair in _lastMotionMapping)
            {
                motions.Add(new CharacterProfile.MotionEntry
                {
                    animation = pair.Key, value = pair.Value,
                });
            }
            motions.Sort((x, y) => x.value.CompareTo(y.value));
            asset.motions = motions.ToArray();
            asset.directions = manifest.direction_axis != null &&
                               manifest.direction_axis.present == "yes"
                ? manifest.direction_axis.values : new string[0];

            // appearance 는 seed 순으로 모은다 — 순서가 결정적이어야
            // 소비자의 population 도 재현 가능하다.
            //
            // **디스크에 있는 것을 그대로 담지 않는다.** 이전 export 에 있었지만 이번
            // manifest 에는 없는 외형은 파츠 텍스처가 이미 지워졌으므로, 담아 두면
            // 스프라이트가 전부 null 인 외형이 조용히 섞인다. 그래서 이번 manifest 가
            // 선언한 seed 만 담고, 남은 것은 stale 로 **보고만** 한다.
            // 자동 삭제도, 다른 외형으로의 자동 대체도 하지 않는다.
            var declared = new HashSet<int>();
            foreach (Appearance a in manifest.appearances) declared.Add(a.seed);

            var found = new List<CharacterAppearance>();
            var stale = new List<string>();
            foreach (string guid in AssetDatabase.FindAssets("t:CharacterAppearance",
                                                             new[] { outDir }))
            {
                string assetPath = AssetDatabase.GUIDToAssetPath(guid);
                var a = AssetDatabase.LoadAssetAtPath<CharacterAppearance>(assetPath);
                if (a == null || a.profile != manifest.profile) continue;
                if (declared.Contains(a.seed)) found.Add(a);
                else stale.Add(string.Format("{0} (seed {1})", assetPath, a.seed));
            }
            found.Sort((x, y) => x.seed.CompareTo(y.seed));
            asset.appearances = found.ToArray();

            stale.Sort(System.StringComparer.Ordinal);
            asset.staleAppearances = stale.ToArray();
            if (stale.Count > 0)
            {
                Debug.LogWarningFormat(
                    "[2D Art Factory] {0}: 이번 export 에 없는 외형 {1}개가 Generated/ 에 "
                    + "남아 있다. profile 에서 제외했다. 이 에셋을 참조하던 게임 쪽 "
                    + "reference 는 **직접 고쳐야 한다** — 자동 대체하지 않는다.\n  {2}",
                    manifest.profile, stale.Count, string.Join("\n  ", stale.ToArray()));
            }

            // 프리팹은 profile 당 하나면 충분하다 (topology 가 같으므로).
            foreach (string guid in AssetDatabase.FindAssets("t:Prefab", new[] { outDir }))
            {
                string prefabPath = AssetDatabase.GUIDToAssetPath(guid);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefab != null && prefab.GetComponent<CharacterView>() != null)
                {
                    asset.prefab = prefab;
                    break;
                }
            }

            if (isNew) AssetDatabase.CreateAsset(asset, path);
            else EditorUtility.SetDirty(asset);
            Debug.LogFormat("[2D Art Factory] {0}: profile 에셋 (appearance {1}, " +
                            "directions {2}, motions {3})", manifest.profile,
                            asset.appearances.Length, asset.directions.Length,
                            asset.motions.Length);
        }

        static void BuildAnimation(Manifest manifest, string outDir)
        {
            // topology 는 manifest 가 준다. 시트에서 프레임 수를 다시 세지 않는다.
            var specs = new List<AnimationClipBuilder.ClipSpec>();
            var order = new List<string>();
            int rate = manifest.frame_rate > 0 ? manifest.frame_rate : 12;
            if (manifest.topology_list != null)
            {
                foreach (TopologyEntry entry in manifest.topology_list)
                {
                    specs.Add(new AnimationClipBuilder.ClipSpec
                    {
                        animation = entry.animation,
                        frameCount = entry.frame_count,
                        frameRate = rate,
                    });
                    order.Add(entry.animation);
                }
            }
            if (specs.Count == 0) return;

            Dictionary<string, AnimationClip> clips =
                AnimationClipBuilder.BuildClips(outDir, manifest.profile, specs);
            // controller state 를 만들면서 나온 **명시적** 매핑을 그대로 받는다.
            var motionMapping = new Dictionary<string, int>();
            UnityEditor.Animations.AnimatorController controller =
                AnimationClipBuilder.BuildController(outDir, manifest.profile, clips,
                                                     order, motionMapping);
            _lastMotionMapping = motionMapping;

            // 프리팹들에 Animator 를 붙이고 같은 controller 를 물린다.
            foreach (string guid in AssetDatabase.FindAssets("t:Prefab", new[] { outDir }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab == null || prefab.GetComponent<CharacterView>() == null) continue;
                GameObject instance = PrefabUtility.LoadPrefabContents(path);
                try
                {
                    var animator = instance.GetComponent<Animator>();
                    if (animator == null) animator = instance.AddComponent<Animator>();
                    animator.runtimeAnimatorController = controller;
                    animator.applyRootMotion = false;
                    animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                    PrefabUtility.SaveAsPrefabAsset(instance, path);
                }
                finally
                {
                    PrefabUtility.UnloadPrefabContents(instance);
                }
            }
        }

        // ── 슬라이스 ──────────────────────────────────────────────────────

        static string SpriteName(PartSheet sheet, string label)
        {
            return sheet.slot + "_" + sheet.asset + "_" + label;
        }

        static void SliceSheet(string assetPath, PartSheet sheet, Origin origin)
        {
            var importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (importer == null)
                throw new Exception("텍스처를 찾지 못했다: " + assetPath);

            importer.textureType = TextureImporterType.Sprite;
            importer.spriteImportMode = SpriteImportMode.Multiple;
            importer.spritePixelsPerUnit = origin != null && origin.pixels_per_unit > 0
                ? origin.pixels_per_unit : 100f;
            importer.filterMode = FilterMode.Point;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.mipmapEnabled = false;
            importer.alphaIsTransparency = true;
            importer.npotScale = TextureImporterNPOTScale.None;
            importer.maxTextureSize = 4096;

            SpriteAlignment alignment = ParseAlignment(origin != null ? origin.pivot : null);
            Vector2 pivot = ParsePivot(origin != null ? origin.pivot : null);

            // spriteMeshType / 기본 pivot 은 TextureImporter 가 아니라
            // TextureImporterSettings 에 있다.
            var settings = new TextureImporterSettings();
            importer.ReadTextureSettings(settings);
            settings.spriteMeshType = SpriteMeshType.FullRect;
            settings.spriteAlignment = (int)alignment;
            settings.spritePivot = pivot;
            importer.SetTextureSettings(settings);

            // 가로 한 줄, 셀 크기는 manifest 선언값. 검출하지 않는다.
#pragma warning disable 0618
            var metas = new SpriteMetaData[sheet.frame_count];
            for (int i = 0; i < sheet.frame_count; i++)
            {
                metas[i] = new SpriteMetaData
                {
                    name = SpriteName(sheet, sheet.labels[i]),
                    rect = new Rect(i * sheet.cell_width, 0,
                                    sheet.cell_width, sheet.cell_height),
                    alignment = (int)alignment,
                    pivot = pivot,
                };
            }
            importer.spritesheet = metas;
#pragma warning restore 0618

            EditorUtility.SetDirty(importer);
            importer.SaveAndReimport();
        }

        // ── 라이브러리 ────────────────────────────────────────────────────

        static SpriteLibraryAsset BuildLibrary(Manifest manifest, Appearance appearance,
                                               Dictionary<string, Dictionary<string, Sprite>> index,
                                               string outDir)
        {
            string path = string.Format("{0}/{1}_{2}_library.asset",
                                        outDir, manifest.profile, appearance.seed);
            // 지우고 다시 만들지 않는다 — GUID 가 바뀌면 CharacterAppearance 와
            // 게임 쪽 참조가 끊긴다. 기존 에셋이 있으면 내용만 비우고 다시 채운다.
            var library = AssetDatabase.LoadAssetAtPath<SpriteLibraryAsset>(path);
            bool isNewLibrary = library == null;
            if (isNewLibrary) library = ScriptableObject.CreateInstance<SpriteLibraryAsset>();
            else ClearLibrary(library);

            foreach (LayerRef layer in appearance.layers)
            {
                Dictionary<string, Sprite> byLabel;
                if (!index.TryGetValue(layer.slot + "/" + layer.asset, out byLabel))
                {
                    Debug.LogWarningFormat("[2D Art Factory] 파츠 시트 없음: {0}/{1}",
                                           layer.slot, layer.asset);
                    continue;
                }
                // category 이름은 슬롯이다. appearance 가 달라도 같은 이름이라
                // AnimationClip 을 그대로 공유할 수 있다.
                foreach (KeyValuePair<string, Sprite> pair in byLabel)
                    library.AddCategoryLabel(pair.Value, layer.slot, pair.Key);
            }

            if (isNewLibrary) AssetDatabase.CreateAsset(library, path);
            else EditorUtility.SetDirty(library);
            return library;
        }

        /// <summary>라이브러리의 category/label 을 전부 비운다 (에셋 자체는 유지).</summary>
        static void ClearLibrary(SpriteLibraryAsset library)
        {
            foreach (string category in new List<string>(library.GetCategoryNames()))
            {
                foreach (string label in new List<string>(
                             library.GetCategoryLabelNames(category)))
                {
                    library.RemoveCategoryLabel(category, label, true);
                }
            }
        }

        static CharacterAppearance BuildDefinition(Manifest manifest, Appearance appearance,
                                                   SpriteLibraryAsset library, string outDir)
        {
            string path = string.Format("{0}/{1}_{2}_appearance.asset",
                                        outDir, manifest.profile, appearance.seed);
            var definition = AssetDatabase.LoadAssetAtPath<CharacterAppearance>(path);
            bool isNew = definition == null;
            if (isNew) definition = ScriptableObject.CreateInstance<CharacterAppearance>();

            definition.profile = manifest.profile;
            definition.pack = manifest.pack;
            definition.seed = appearance.seed;
            definition.archetype = appearance.archetype;
            definition.library = library;
            definition.originPolicy = manifest.origin != null ? manifest.origin.policy : "";
            definition.pixelsPerUnit = manifest.origin != null ? manifest.origin.pixels_per_unit : 100f;

            var layers = new List<CharacterAppearance.VisualLayer>();
            foreach (LayerRef layer in appearance.layers)
            {
                layers.Add(new CharacterAppearance.VisualLayer
                {
                    slot = layer.slot, asset = layer.asset, zOrder = layer.z_order,
                });
            }
            layers.Sort((a, b) => a.zOrder.CompareTo(b.zOrder));
            definition.layers = layers.ToArray();

            if (appearance.attribution != null)
            {
                definition.attributionRequired = appearance.attribution.attribution_required;
                definition.shareAlikePresent = appearance.attribution.share_alike_present;
                definition.authors = appearance.attribution.authors;
                definition.licenses = appearance.attribution.licenses;
            }

            if (isNew) AssetDatabase.CreateAsset(definition, path);
            else EditorUtility.SetDirty(definition);
            return definition;
        }

        // ── 프리팹 ────────────────────────────────────────────────────────

        static void BuildPrefab(Manifest manifest, CharacterAppearance definition,
                                string outDir)
        {
            string path = string.Format("{0}/{1}_{2}.prefab",
                                        outDir, manifest.profile, definition.seed);
            var root = new GameObject(manifest.profile + "_" + definition.seed);
            try
            {
                var library = root.AddComponent<SpriteLibrary>();
                library.spriteLibraryAsset = definition.library;
                var view = root.AddComponent<CharacterView>();

                // **프로파일 전체 슬롯**으로 만든다. appearance 가 안 쓰는 슬롯도 포함한다.
                // 그래야 appearance 마다 프리팹 구조가 같아지고 AnimationClip 을 공유할 수 있다.
                // 안 쓰는 슬롯은 라이브러리에 category 가 없어 스프라이트가 null -> 숨겨진다.
                var slots = new List<string>();
                var resolvers = new List<SpriteResolver>();
                var renderers = new List<SpriteRenderer>();
                foreach (ProfileSlot slot in manifest.slots)
                {
                    var go = new GameObject(slot.slot);
                    go.transform.SetParent(root.transform, false);
                    var renderer = go.AddComponent<SpriteRenderer>();
                    // z-order 를 sortingOrder 로 그대로 옮긴다. 소스가 선언한 값이다.
                    renderer.sortingOrder = slot.z_order;
                    var resolver = go.AddComponent<SpriteResolver>();
                    slots.Add(slot.slot);
                    resolvers.Add(resolver);
                    renderers.Add(renderer);
                }
                view.Bind(definition, library, slots.ToArray(),
                          resolvers.ToArray(), renderers.ToArray());

                PrefabUtility.SaveAsPrefabAsset(root, path);
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        // ── 잡다 ─────────────────────────────────────────────────────────

        static void EnsureFolder(string assetPath)
        {
            if (AssetDatabase.IsValidFolder(assetPath)) return;
            string parent = Path.GetDirectoryName(assetPath).Replace('\\', '/');
            string leaf = Path.GetFileName(assetPath);
            if (!AssetDatabase.IsValidFolder(parent)) EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, leaf);
        }

        static SpriteAlignment ParseAlignment(string pivot)
        {
            switch (pivot)
            {
                case "BottomCenter": return SpriteAlignment.BottomCenter;
                case "BottomLeft": return SpriteAlignment.BottomLeft;
                case "TopCenter": return SpriteAlignment.TopCenter;
                default: return SpriteAlignment.Center;
            }
        }

        static Vector2 ParsePivot(string pivot)
        {
            switch (pivot)
            {
                case "BottomCenter": return new Vector2(0.5f, 0f);
                case "BottomLeft": return new Vector2(0f, 0f);
                case "TopCenter": return new Vector2(0.5f, 1f);
                default: return new Vector2(0.5f, 0.5f);
            }
        }

        static string ToAssetPath(string absolute)
        {
            absolute = absolute.Replace('\\', '/');
            string data = Application.dataPath.Replace('\\', '/');
            if (!absolute.StartsWith(data + "/")) return null;
            return "Assets/" + absolute.Substring(data.Length + 1);
        }
    }
}
