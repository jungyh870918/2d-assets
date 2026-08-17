using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace ArtFactory.EditorTools
{
    /// <summary>
    /// 06_UNITY_EXPORT/characters/&lt;profile&gt;/manifest.json 을 읽어
    ///   1) 텍스처 임포트 설정 적용 (시트는 cell 크기로 슬라이스)
    ///   2) 캐릭터당 GeneratedCharacter 에셋 생성
    ///   3) 스프라이트 참조 연결
    /// 딱 여기까지만 한다. Animator / Addressables / prefab factory 는 만들지 않는다.
    ///
    /// 쓰는 법: export 폴더를 Assets/ 아래로 복사한 뒤
    ///   메뉴 > 2D Art Factory > Import Generated Characters
    /// </summary>
    public static class GeneratedCharacterImporter
    {
        const string MenuPath = "2D Art Factory/Import Generated Characters";

        // ── manifest.json 매핑 ────────────────────────────────────────────
        // JsonUtility 는 필드 이름을 그대로 대조하므로 JSON 의 snake_case 를 유지한다.
        // (JsonUtility 는 Dictionary 를 못 읽어서, export 쪽에서 이미 배열로 펴 두었다.)
#pragma warning disable 0649
        [Serializable]
        class ImportSettings
        {
            public float pixels_per_unit = 100f;
            public string filter_mode = "Point";
            public string compression = "None";
            public string mesh_type = "FullRect";
            public string pivot = "BottomCenter";
            public int max_texture_size = 2048;
            public bool generate_mip_maps;
            public int frame_rate = 12;
        }

        [Serializable] class PartEntry { public string slot; public string part; public string ramp; }
        [Serializable] class GroupEntry { public string group; public string ramp; }
        [Serializable] class PaletteEntry { public string name; public string source; public int tint_index; public GroupEntry[] groups; }
        [Serializable] class PreviewEntry { public string file; public string sprite_mode; public int[] size; }

        [Serializable]
        class SheetEntry
        {
            public string animation;
            public string file;
            public string sprite_mode;
            public int frame_count;
            public int cell_width;
            public int cell_height;
            public int[] size;
            public int frame_rate;
        }

        [Serializable]
        class CharacterEntry
        {
            public int seed;
            public string archetype;
            public string directory;
            public string definition;
            public PartEntry[] parts;
            public PaletteEntry palette;
            public string[] animations;
            public PreviewEntry preview;
            public SheetEntry[] sheets;
        }

        [Serializable]
        class Manifest
        {
            public string schema;
            public string profile;
            public string pack;
            public string rule;
            public int character_count;
            public ImportSettings import_settings;
            public CharacterEntry[] characters;
        }
#pragma warning restore 0649

        const string ExpectedSchema = "ap2d.unity_manifest/1";

        [MenuItem(MenuPath)]
        public static void ImportFromMenu()
        {
            string picked = EditorUtility.OpenFilePanel(
                "manifest.json 고르기", Application.dataPath, "json");
            if (string.IsNullOrEmpty(picked)) return;

            string assetPath = ToAssetPath(picked);
            if (assetPath == null)
            {
                EditorUtility.DisplayDialog(
                    "2D Art Factory",
                    "manifest.json 이 이 프로젝트의 Assets/ 아래에 있어야 한다.\n" +
                    "06_UNITY_EXPORT 의 export 폴더를 Assets/ 로 먼저 복사해라.",
                    "확인");
                return;
            }

            try
            {
                int count = Import(assetPath);
                EditorUtility.DisplayDialog(
                    "2D Art Factory", string.Format("캐릭터 {0}개를 임포트했다.", count), "확인");
            }
            catch (Exception e)
            {
                Debug.LogException(e);
                EditorUtility.DisplayDialog("2D Art Factory", "임포트 실패: " + e.Message, "확인");
            }
        }

        /// <summary>manifest 를 읽어 임포트한다. 반환값은 처리한 캐릭터 수.</summary>
        public static int Import(string manifestAssetPath)
        {
            string absolute = Path.Combine(
                Path.GetDirectoryName(Application.dataPath), manifestAssetPath);
            Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(absolute));

            if (manifest == null || manifest.characters == null)
                throw new Exception("manifest 를 읽지 못했다: " + manifestAssetPath);
            if (manifest.schema != ExpectedSchema)
                throw new Exception(string.Format(
                    "manifest schema 가 {0} 이어야 한다 (현재: {1})",
                    ExpectedSchema, manifest.schema));

            string root = Path.GetDirectoryName(manifestAssetPath).Replace('\\', '/');
            ImportSettings settings = manifest.import_settings ?? new ImportSettings();

            // 1단계: 텍스처 설정을 먼저 전부 적용한다.
            // 스프라이트는 재임포트가 끝나야 서브에셋으로 존재하므로 단계를 나눠야 한다.
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (CharacterEntry c in manifest.characters)
                {
                    if (c.preview != null && !string.IsNullOrEmpty(c.preview.file))
                        ConfigureSingle(root + "/" + c.preview.file, settings);

                    if (c.sheets == null) continue;
                    foreach (SheetEntry s in c.sheets)
                        ConfigureSheet(root + "/" + s.file, s, c.seed, settings);
                }
            }
            finally
            {
                AssetDatabase.StopAssetEditing();
                AssetDatabase.Refresh();
            }

            // 2단계: GeneratedCharacter 에셋 생성 + 스프라이트 연결.
            int imported = 0;
            foreach (CharacterEntry c in manifest.characters)
            {
                BuildAsset(root, manifest, c, settings);
                imported++;
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log(string.Format(
                "[2D Art Factory] {0} — 캐릭터 {1}개 임포트 완료 ({2})",
                manifest.profile, imported, root));
            return imported;
        }

        // ── 텍스처 설정 ───────────────────────────────────────────────────

        static TextureImporter GetImporter(string assetPath)
        {
            var importer = AssetImporter.GetAtPath(assetPath) as TextureImporter;
            if (importer == null)
                throw new Exception("텍스처를 찾지 못했다: " + assetPath);
            return importer;
        }

        static void ApplyCommon(TextureImporter importer, ImportSettings s)
        {
            importer.textureType = TextureImporterType.Sprite;
            importer.spritePixelsPerUnit = s.pixels_per_unit;
            importer.filterMode = ParseFilterMode(s.filter_mode);
            importer.textureCompression = ParseCompression(s.compression);
            // spriteMeshType 은 TextureImporter 가 아니라 TextureImporterSettings 에 있다.
            var meshSettings = new TextureImporterSettings();
            importer.ReadTextureSettings(meshSettings);
            meshSettings.spriteMeshType = s.mesh_type == "FullRect"
                ? SpriteMeshType.FullRect
                : SpriteMeshType.Tight;
            importer.SetTextureSettings(meshSettings);
            importer.mipmapEnabled = s.generate_mip_maps;
            importer.maxTextureSize = s.max_texture_size;
            importer.alphaIsTransparency = true;
            importer.npotScale = TextureImporterNPOTScale.None;
        }

        static void ConfigureSingle(string assetPath, ImportSettings s)
        {
            TextureImporter importer = GetImporter(assetPath);
            ApplyCommon(importer, s);
            importer.spriteImportMode = SpriteImportMode.Single;
            importer.spriteBorder = Vector4.zero;

            TextureImporterSettings tis = new TextureImporterSettings();
            importer.ReadTextureSettings(tis);
            tis.spriteAlignment = (int)ParseAlignment(s.pivot);
            tis.spritePivot = ParsePivot(s.pivot);
            importer.SetTextureSettings(tis);

            EditorUtility.SetDirty(importer);
            importer.SaveAndReimport();
        }

        static void ConfigureSheet(string assetPath, SheetEntry sheet, int seed, ImportSettings s)
        {
            TextureImporter importer = GetImporter(assetPath);
            ApplyCommon(importer, s);
            importer.spriteImportMode = SpriteImportMode.Multiple;

            SpriteAlignment alignment = ParseAlignment(s.pivot);
            Vector2 pivot = ParsePivot(s.pivot);

            // 시트는 가로 한 줄이고 높이가 곧 셀 높이다 (compose.py 가 그렇게 만든다).
            // SpriteMetaData 는 Unity 2021+ 에서 deprecated 지만 아직 동작한다.
            // 이 임포터를 최소로 유지하려고 신형 SpriteDataProvider 대신 이걸 쓴다.
#pragma warning disable 0618
            var metas = new SpriteMetaData[sheet.frame_count];
            for (int i = 0; i < sheet.frame_count; i++)
            {
                metas[i] = new SpriteMetaData
                {
                    name = SpriteName(seed, sheet.animation, i),
                    rect = new Rect(i * sheet.cell_width, 0, sheet.cell_width, sheet.cell_height),
                    alignment = (int)alignment,
                    pivot = pivot,
                };
            }
            importer.spritesheet = metas;
#pragma warning restore 0618

            EditorUtility.SetDirty(importer);
            importer.SaveAndReimport();
        }

        static string SpriteName(int seed, string animation, int frame)
        {
            return string.Format("{0}_{1}_{2:D2}", seed, animation, frame);
        }

        // ── 에셋 생성 ─────────────────────────────────────────────────────

        static void BuildAsset(string root, Manifest manifest, CharacterEntry c, ImportSettings s)
        {
            string dir = root + "/" + c.directory;
            string assetPath = string.Format("{0}/character_{1}.asset", dir, c.seed);

            var asset = AssetDatabase.LoadAssetAtPath<GeneratedCharacter>(assetPath);
            bool isNew = asset == null;
            if (isNew) asset = ScriptableObject.CreateInstance<GeneratedCharacter>();

            asset.pack = manifest.pack;
            asset.profile = manifest.profile;
            asset.archetype = c.archetype;
            asset.seed = c.seed;
            asset.paletteName = c.palette != null ? c.palette.name : string.Empty;

            var slots = new List<GeneratedCharacter.PartSlot>();
            if (c.parts != null)
            {
                foreach (PartEntry p in c.parts)
                {
                    slots.Add(new GeneratedCharacter.PartSlot
                    {
                        slot = p.slot, part = p.part, ramp = p.ramp,
                    });
                }
            }
            asset.parts = slots.ToArray();

            if (c.preview != null && !string.IsNullOrEmpty(c.preview.file))
                asset.preview = AssetDatabase.LoadAssetAtPath<Sprite>(root + "/" + c.preview.file);

            var sheets = new List<GeneratedCharacter.AnimationClipSheet>();
            if (c.sheets != null)
            {
                foreach (SheetEntry sheet in c.sheets)
                {
                    Sprite[] frames = LoadFrames(root + "/" + sheet.file, c.seed, sheet);
                    sheets.Add(new GeneratedCharacter.AnimationClipSheet
                    {
                        animation = sheet.animation,
                        frameRate = sheet.frame_rate > 0 ? sheet.frame_rate : s.frame_rate,
                        frames = frames,
                    });
                }
            }
            asset.sheets = sheets.ToArray();

            if (isNew) AssetDatabase.CreateAsset(asset, assetPath);
            else EditorUtility.SetDirty(asset);
        }

        /// <summary>슬라이스된 서브에셋을 이름으로 찾아 프레임 순서대로 돌려준다.</summary>
        static Sprite[] LoadFrames(string sheetAssetPath, int seed, SheetEntry sheet)
        {
            var byName = new Dictionary<string, Sprite>();
            foreach (UnityEngine.Object o in AssetDatabase.LoadAllAssetsAtPath(sheetAssetPath))
            {
                var sprite = o as Sprite;
                if (sprite != null) byName[sprite.name] = sprite;
            }

            var frames = new Sprite[sheet.frame_count];
            for (int i = 0; i < sheet.frame_count; i++)
            {
                string name = SpriteName(seed, sheet.animation, i);
                if (!byName.TryGetValue(name, out frames[i]))
                {
                    Debug.LogWarningFormat(
                        "[2D Art Factory] 스프라이트를 못 찾았다: {0} ({1})", name, sheetAssetPath);
                }
            }
            return frames;
        }

        // ── 값 변환 ───────────────────────────────────────────────────────

        static FilterMode ParseFilterMode(string value)
        {
            switch (value)
            {
                case "Point": return FilterMode.Point;
                case "Trilinear": return FilterMode.Trilinear;
                default: return FilterMode.Bilinear;
            }
        }

        static TextureImporterCompression ParseCompression(string value)
        {
            switch (value)
            {
                case "None": return TextureImporterCompression.Uncompressed;
                case "HighQuality": return TextureImporterCompression.CompressedHQ;
                case "LowQuality": return TextureImporterCompression.CompressedLQ;
                default: return TextureImporterCompression.Compressed;
            }
        }

        static SpriteAlignment ParseAlignment(string pivot)
        {
            switch (pivot)
            {
                case "BottomCenter": return SpriteAlignment.BottomCenter;
                case "BottomLeft": return SpriteAlignment.BottomLeft;
                case "BottomRight": return SpriteAlignment.BottomRight;
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
                case "BottomRight": return new Vector2(1f, 0f);
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
