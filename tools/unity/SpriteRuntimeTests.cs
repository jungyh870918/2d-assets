using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.U2D.Animation;

namespace ArtFactory.EditorTools
{
    /// <summary>
    /// Sprite Library / Resolver POC 검증. Unity 를 batchmode 로 띄워 실행한다.
    ///
    ///   Unity -batchmode -nographics -quit -projectPath &lt;proj&gt; \
    ///         -executeMethod ArtFactory.EditorTools.SpriteRuntimeTests.RunAll
    ///
    /// NUnit 대신 직접 어서션을 쓴다 — Test Framework 패키지 없이 돌리기 위해서다.
    /// 실패하면 종료 코드가 0이 아니다.
    /// </summary>
    public static class SpriteRuntimeTests
    {
        static readonly List<string> Failures = new List<string>();
        static int _checks;

        static void Check(bool condition, string message)
        {
            _checks++;
            if (!condition)
            {
                Failures.Add(message);
                Debug.LogError("[FAIL] " + message);
            }
        }

        public static void RunAll()
        {
            Failures.Clear();
            _checks = 0;
            try
            {
                foreach (string manifest in FindManifests())
                {
                    Debug.Log("=== manifest: " + manifest + " ===");
                    SpriteLibraryBuilder.Build(manifest);
                    RunProfileTests(manifest);
                }
                TestAppearanceSwapKeepsAnimatorState();
                TestAnimatorPlayback();
                TestMultiLayerAndSubset();
            }
            catch (System.Exception e)
            {
                Failures.Add("예외: " + e);
                Debug.LogException(e);
            }

            Debug.LogFormat("[RESULT] checks={0} failures={1}", _checks, Failures.Count);
            foreach (string f in Failures) Debug.Log("[FAILURE] " + f);
            EditorApplication.Exit(Failures.Count == 0 ? 0 : 1);
        }

        static IEnumerable<string> FindManifests()
        {
            var found = new List<string>();
            foreach (string guid in AssetDatabase.FindAssets("runtime_manifest"))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (path.EndsWith("runtime_manifest.json")) found.Add(path);
            }
            found.Sort();
            return found;
        }

        static void RunProfileTests(string manifestPath)
        {
            string dir = Path.GetDirectoryName(manifestPath).Replace('\\', '/') + "/Generated";
            var appearances = new List<CharacterAppearance>();
            foreach (string guid in AssetDatabase.FindAssets("t:CharacterAppearance", new[] { dir }))
            {
                var asset = AssetDatabase.LoadAssetAtPath<CharacterAppearance>(
                    AssetDatabase.GUIDToAssetPath(guid));
                if (asset != null) appearances.Add(asset);
            }
            appearances.Sort((a, b) => a.seed.CompareTo(b.seed));
            Check(appearances.Count >= 2,
                  dir + ": appearance 가 2개 이상이어야 swap 을 시험할 수 있다");
            if (appearances.Count == 0) return;

            // 1. 라이브러리가 실제로 만들어졌고 category/label 이 붙어 있는가
            foreach (CharacterAppearance appearance in appearances)
            {
                Check(appearance.library != null,
                      appearance.name + ": SpriteLibraryAsset 이 없다");
                if (appearance.library == null) continue;

                var categories = new List<string>(appearance.library.GetCategoryNames());
                Check(categories.Count > 0, appearance.name + ": category 가 없다");

                foreach (CharacterAppearance.VisualLayer layer in appearance.layers)
                {
                    Check(categories.Contains(layer.slot),
                          string.Format("{0}: category '{1}' 이 라이브러리에 없다",
                                        appearance.name, layer.slot));
                }

                // 2. category/label 충돌이 없는가 (같은 라벨이 두 번 등록되면 사전이 덮인다)
                foreach (string category in categories)
                {
                    var labels = new List<string>(appearance.library.GetCategoryLabelNames(category));
                    var seen = new HashSet<string>();
                    foreach (string label in labels)
                    {
                        Check(seen.Add(label),
                              string.Format("{0}/{1}: 라벨 중복 '{2}'",
                                            appearance.name, category, label));
                    }
                    Check(labels.Count > 0,
                          string.Format("{0}/{1}: 라벨이 없다", appearance.name, category));
                }
            }

            // 3. 두 appearance 의 **프리팹 구조가 같은가** (clip 공유의 실제 전제).
            //    라이브러리 category 집합은 달라도 된다 — 선택 슬롯을 안 쓰는 캐릭터는
            //    그 category 가 없고, 해당 레이어만 숨겨지면 된다.
            //    중요한 건 슬롯 GameObject/Resolver 구성이 동일한 것이다.
            if (appearances.Count >= 2)
            {
                string sigA = PrefabSlotSignature(dir, appearances[0]);
                string sigB = PrefabSlotSignature(dir, appearances[1]);
                Check(sigA == sigB && sigA != null,
                      string.Format("두 appearance 의 프리팹 슬롯 구조가 다르다 — "
                                    + "AnimationClip 을 공유할 수 없다\n  A: {0}\n  B: {1}",
                                    sigA, sigB));
            }

            // 4. appearance 정의의 레이어가 z-order 오름차순인가
            foreach (CharacterAppearance appearance in appearances)
            {
                for (int i = 1; i < appearance.layers.Length; i++)
                {
                    Check(appearance.layers[i - 1].zOrder <= appearance.layers[i].zOrder,
                          appearance.name + ": layers 가 z-order 오름차순이 아니다");
                }
            }

            // 5. 프리팹의 sortingOrder 가 z-order 오름차순으로 붙어 있는가
            foreach (CharacterAppearance appearance in appearances)
            {
                string prefabPath = string.Format("{0}/{1}_{2}.prefab",
                                                  dir, appearance.profile, appearance.seed);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                Check(prefab != null, "프리팹이 없다: " + prefabPath);
                if (prefab == null) continue;

                var renderers = prefab.GetComponentsInChildren<SpriteRenderer>(true);
                Check(renderers.Length >= appearance.layers.Length,
                      appearance.name + ": 렌더러가 appearance 레이어보다 적다");
                for (int i = 1; i < renderers.Length; i++)
                {
                    Check(renderers[i - 1].sortingOrder <= renderers[i].sortingOrder,
                          appearance.name + ": sortingOrder 가 오름차순이 아니다");
                }
                Check(prefab.GetComponent<SpriteLibrary>() != null,
                      appearance.name + ": SpriteLibrary 컴포넌트가 없다");
            }

            // 6. 실제 인스턴스에서 스프라이트가 해결되는가 + 방향/프레임 유지
            TestResolution(appearances, manifestPath);
        }

        /// <summary>프리팹의 슬롯 구조를 문자열로. 두 appearance 가 같아야 clip 을 공유한다.</summary>

        // ── Phase 2: AnimationClip / Animator ──────────────────────────────

        static List<CharacterAppearance> AppearancesIn(string dir)
        {
            var list = new List<CharacterAppearance>();
            foreach (string guid in AssetDatabase.FindAssets("t:CharacterAppearance", new[] { dir }))
            {
                var a = AssetDatabase.LoadAssetAtPath<CharacterAppearance>(
                    AssetDatabase.GUIDToAssetPath(guid));
                if (a != null) list.Add(a);
            }
            list.Sort((x, y) => x.seed.CompareTo(y.seed));
            return list;
        }

        static void TestAnimatorPlayback()
        {
            foreach (string manifestPath in FindManifests())
            {
                string dir = Path.GetDirectoryName(manifestPath).Replace('\\', '/') + "/Generated";
                var appearances = AppearancesIn(dir);
                if (appearances.Count == 0) continue;
                string profile = appearances[0].profile;

                // 1. clip 이 실제로 만들어졌고 profile 당 한 벌인가
                var clips = new List<AnimationClip>();
                foreach (string guid in AssetDatabase.FindAssets("t:AnimationClip", new[] { dir }))
                    clips.Add(AssetDatabase.LoadAssetAtPath<AnimationClip>(
                        AssetDatabase.GUIDToAssetPath(guid)));
                Check(clips.Count > 0, profile + ": AnimationClip 이 없다");

                var controller = AssetDatabase.LoadAssetAtPath<UnityEditor.Animations.AnimatorController>(
                    string.Format("{0}/{1}_controller.controller", dir, profile));
                Check(controller != null, profile + ": AnimatorController 가 없다");
                if (controller == null) continue;

                // 2. clip 이 appearance 를 키프레임하지 않는가 (외형 독립)
                foreach (AnimationClip clip in clips)
                {
                    var bindings = AnimationUtility.GetCurveBindings(clip);
                    Check(bindings.Length == 1,
                          profile + ": clip 이 커브를 1개만 가져야 한다 (현재 " + bindings.Length + ")");
                    foreach (var b in bindings)
                    {
                        Check(b.propertyName == "frame",
                              profile + ": clip 이 frame 이 아닌 " + b.propertyName + " 을 키프레임한다");
                        Check(b.path == "",
                              profile + ": clip 이 루트가 아닌 경로를 키프레임한다: " + b.path);
                    }
                    Check(clip.frameRate > 0, profile + ": frameRate 가 0 이다");
                    Check(clip.isLooping, profile + ": clip 이 loop 가 아니다");
                }

                // 3. 프레임 수와 길이가 topology 와 맞는가
                foreach (AnimationClip clip in clips)
                {
                    var bindings = AnimationUtility.GetCurveBindings(clip);
                    if (bindings.Length == 0) continue;
                    AnimationCurve curve = AnimationUtility.GetEditorCurve(clip, bindings[0]);
                    int frames = curve.keys.Length - 1;
                    Check(frames >= 1, clip.name + ": 프레임이 없다");
                    float expected = frames / clip.frameRate;
                    Check(Mathf.Abs(clip.length - expected) < 0.001f,
                          string.Format("{0}: 길이 {1} != frames {2} / rate {3}",
                                        clip.name, clip.length, frames, clip.frameRate));
                    // 첫 키는 frame 0, 마지막 데이터 키는 frames-1
                    Check(Mathf.Approximately(curve.keys[0].value, 0f),
                          clip.name + ": 첫 키가 frame 0 이 아니다");
                    Check(Mathf.Approximately(curve.keys[frames - 1].value, frames - 1),
                          clip.name + ": 마지막 데이터 키가 frame " + (frames - 1) + " 이 아니다");
                }

                // 4. 실제 재생 — Animator 가 시간에 따라 frame 을 진행시키는가
                string prefabPath = string.Format("{0}/{1}_{2}.prefab", dir, profile,
                                                  appearances[0].seed);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                Check(prefab != null, profile + ": 프리팹이 없다");
                if (prefab == null) continue;
                Check(prefab.GetComponent<Animator>() != null,
                      profile + ": 프리팹에 Animator 가 없다");

                GameObject instance = Object.Instantiate(prefab);
                try
                {
                    var animator = instance.GetComponent<Animator>();
                    var view = instance.GetComponent<CharacterView>();
                    animator.runtimeAnimatorController = controller;
                    string direction = FirstDirection(appearances[0]);
                    if (!string.IsNullOrEmpty(direction)) view.SetDirection(direction);

                    animator.Update(0f);
                    string firstAnimation = view.CurrentAnimation;
                    Check(!string.IsNullOrEmpty(firstAnimation),
                          profile + ": state 진입이 animation 이름을 세팅하지 않았다");
                    int startFrame = view.CurrentFrame;

                    // 몇 프레임 진행시킨다. Animator 가 frame 을 쓰고, 그 값이
                    // 실제로 다른 스프라이트로 이어지는지까지 본다.
                    // 첫 렌더러 하나만 보면 안 된다 — 그 슬롯이 이 appearance 가
                    // 안 쓰는 선택 슬롯이면 영영 null 이다 (CC0 의 wing_l 등).
                    // 보이는 레이어 전체의 스프라이트 조합을 본다.
                    var seenFrames = new HashSet<int>();
                    var seenSprites = new HashSet<string>();
                    for (int i = 0; i < 6; i++)
                    {
                        animator.Update(1f / 8f);
                        // 에디터 모드에서는 OnDidApplyAnimationProperties 메시지가
                        // 보장되지 않으므로 여기서 명시적으로 반영한다.
                        // 플레이 모드에서는 그 훅이 같은 일을 한다.
                        view.Apply();
                        seenFrames.Add(view.CurrentFrame);
                        seenSprites.Add(VisibleSpriteSignature(instance));
                    }
                    Check(seenFrames.Count > 1,
                          profile + ": Animator 가 frame 을 진행시키지 않았다 (frame=" + startFrame + " 고정)");
                    Check(view.VisibleLayerCount() > 0,
                          profile + ": 재생 중 보이는 레이어가 없다");
                    Check(seenSprites.Count > 1,
                          profile + ": frame 은 바뀌는데 스프라이트가 그대로다 (" +
                          seenSprites.Count + "종)");

                    // 5. state 전환 — Motion 파라미터로 다른 애니메이션으로
                    if (controller.parameters.Length > 0 && clips.Count > 1)
                    {
                        animator.SetInteger("Motion", 1);
                        for (int i = 0; i < 4; i++) animator.Update(1f / 8f);
                        Check(view.CurrentAnimation != firstAnimation,
                              profile + ": Motion 을 바꿨는데 animation 이 그대로다 (" + view.CurrentAnimation + ")");
                    }

                    // 6. 재생 중 appearance swap — Animator 상태가 유지되는가
                    if (appearances.Count >= 2)
                    {
                        AnimatorStateInfo before = animator.GetCurrentAnimatorStateInfo(0);
                        string beforeAnimation = view.CurrentAnimation;
                        string beforeDirection = view.CurrentDirection;
                        int beforeFrame = view.CurrentFrame;
                        float beforeTime = before.normalizedTime;

                        view.SetAppearance(appearances[1]);

                        AnimatorStateInfo after = animator.GetCurrentAnimatorStateInfo(0);
                        Check(after.fullPathHash == before.fullPathHash,
                              profile + ": swap 후 Animator state 가 바뀌었다");
                        Check(Mathf.Abs(after.normalizedTime - beforeTime) < 0.0001f,
                              string.Format("{0}: swap 후 normalizedTime 이 튀었다 {1} -> {2}",
                                            profile, beforeTime, after.normalizedTime));
                        Check(view.CurrentAnimation == beforeAnimation,
                              profile + ": swap 후 animation 이 바뀌었다");
                        Check(view.CurrentDirection == beforeDirection,
                              profile + ": swap 후 direction 이 바뀌었다");
                        Check(view.CurrentFrame == beforeFrame,
                              profile + ": swap 후 frame 이 바뀌었다");
                        Check(view.Appearance == appearances[1],
                              profile + ": appearance 가 교체되지 않았다");
                        Check(view.VisibleLayerCount() > 0,
                              profile + ": swap 후 보이는 레이어가 없다");

                        // 계속 재생되는가
                        var afterFrames = new HashSet<int>();
                        for (int i = 0; i < 6; i++)
                        {
                            animator.Update(1f / 8f);
                            view.Apply();
                            afterFrames.Add(view.CurrentFrame);
                        }
                        Check(afterFrames.Count > 1,
                              profile + ": swap 후 재생이 멈췄다");
                        Debug.LogFormat("[ANIM] {0}: 재생 중 swap {1} -> {2}, state/direction/frame 유지",
                                        profile, appearances[0].seed, appearances[1].seed);
                    }
                }
                finally
                {
                    Object.DestroyImmediate(instance);
                }
            }
        }

        /// <summary>보이는 모든 레이어의 스프라이트 이름을 하나의 문자열로.</summary>
        static string VisibleSpriteSignature(GameObject instance)
        {
            var parts = new List<string>();
            foreach (SpriteRenderer r in instance.GetComponentsInChildren<SpriteRenderer>(true))
                if (r.enabled && r.sprite != null) parts.Add(r.sprite.name);
            return string.Join("|", parts.ToArray());
        }

        /// <summary>두 appearance 가 같은 파츠 구성을 쓰는가.</summary>
        static bool SameAssets(CharacterAppearance a, CharacterAppearance b)
        {
            var setA = new HashSet<string>();
            foreach (var l in a.layers) setA.Add(l.slot + "=" + l.asset);
            var setB = new HashSet<string>();
            foreach (var l in b.layers) setB.Add(l.slot + "=" + l.asset);
            return setA.SetEquals(setB);
        }

        static string FirstDirection(CharacterAppearance appearance)
        {
            var categories = new List<string>(appearance.library.GetCategoryNames());
            if (categories.Count == 0) return "";
            var labels = new List<string>(appearance.library.GetCategoryLabelNames(categories[0]));
            labels.Sort();
            if (labels.Count == 0) return "";
            string[] bits = labels[0].Split(new[] { CharacterView.LabelSeparator },
                                            System.StringSplitOptions.None);
            return bits.Length == 3 ? bits[1] : "";
        }

        // ── Phase 2: multi-layer / animation subset ────────────────────────

        static void TestMultiLayerAndSubset()
        {
            foreach (string manifestPath in FindManifests())
            {
                string dir = Path.GetDirectoryName(manifestPath).Replace('\\', '/') + "/Generated";
                var appearances = AppearancesIn(dir);
                if (appearances.Count == 0) continue;

                foreach (CharacterAppearance appearance in appearances)
                {
                    // multi-layer: 같은 asset 이 여러 render layer 로 나뉜 경우
                    var byAsset = new Dictionary<string, List<CharacterAppearance.VisualLayer>>();
                    foreach (CharacterAppearance.VisualLayer layer in appearance.layers)
                    {
                        List<CharacterAppearance.VisualLayer> list;
                        if (!byAsset.TryGetValue(layer.asset, out list))
                        {
                            list = new List<CharacterAppearance.VisualLayer>();
                            byAsset[layer.asset] = list;
                        }
                        list.Add(layer);
                    }
                    foreach (var pair in byAsset)
                    {
                        if (pair.Value.Count < 2) continue;
                        // 하나의 logical item 이 만든 여러 layer 는 서로 다른 category 여야 한다
                        var cats = new HashSet<string>();
                        foreach (var l in pair.Value)
                        {
                            Check(cats.Add(l.slot),
                                  appearance.name + ": multi-layer item 의 category 가 겹친다: " + l.slot);
                        }
                        // zPos 가 서로 달라야 앞/뒤가 성립한다
                        var zs = new HashSet<int>();
                        foreach (var l in pair.Value) zs.Add(l.zOrder);
                        Check(zs.Count == pair.Value.Count,
                              appearance.name + ": multi-layer item 의 zOrder 가 겹친다");
                        Debug.LogFormat("[MULTI] {0}: logical item '{1}' -> {2} layers, z={3}",
                                        appearance.name, pair.Key, pair.Value.Count,
                                        string.Join("/", System.Array.ConvertAll(
                                            pair.Value.ToArray(), l => l.zOrder.ToString())));
                    }
                }

                // animation subset 실검증: 지원 -> 미지원 -> 지원 복귀
                CharacterAppearance target = null;
                string supported = null, unsupported = null, subsetCategory = null;
                foreach (CharacterAppearance appearance in appearances)
                {
                    var categories = new List<string>(appearance.library.GetCategoryNames());
                    var animationsBy = new Dictionary<string, HashSet<string>>();
                    foreach (string category in categories)
                    {
                        var set = new HashSet<string>();
                        foreach (string label in appearance.library.GetCategoryLabelNames(category))
                        {
                            string[] bits = label.Split(new[] { CharacterView.LabelSeparator },
                                                        System.StringSplitOptions.None);
                            set.Add(bits[0]);
                        }
                        animationsBy[category] = set;
                    }
                    var all = new HashSet<string>();
                    foreach (var pair in animationsBy) all.UnionWith(pair.Value);
                    foreach (var pair in animationsBy)
                    {
                        if (pair.Value.Count >= all.Count) continue;
                        foreach (string a in all)
                        {
                            if (pair.Value.Contains(a)) supported = supported ?? a;
                            else unsupported = unsupported ?? a;
                        }
                        if (supported != null && unsupported != null)
                        {
                            target = appearance;
                            subsetCategory = pair.Key;
                        }
                        break;
                    }
                    if (target != null) break;
                }

                if (target == null) continue;

                string prefabPath = string.Format("{0}/{1}_{2}.prefab", dir,
                                                  target.profile, target.seed);
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefab == null) continue;
                GameObject instance = Object.Instantiate(prefab);
                try
                {
                    var view = instance.GetComponent<CharacterView>();
                    string direction = FirstDirection(target);

                    view.SetState(supported, direction, 0);
                    int visibleSupported = view.VisibleLayerCount();
                    SpriteRenderer subsetRenderer = FindRenderer(instance, view, subsetCategory);
                    Check(subsetRenderer != null,
                          target.name + ": subset 레이어 렌더러를 못 찾았다: " + subsetCategory);
                    if (subsetRenderer == null) return;

                    Check(subsetRenderer.sprite != null && subsetRenderer.enabled,
                          string.Format("{0}: 지원 애니메이션 '{1}' 인데 {2} 가 안 보인다",
                                        target.name, supported, subsetCategory));

                    view.SetState(unsupported, direction, 0);
                    Check(subsetRenderer.sprite == null && !subsetRenderer.enabled,
                          string.Format("{0}: 미지원 애니메이션 '{1}' 인데 {2} 가 아직 보인다 "
                                        + "(직전 스프라이트 잔존)",
                                        target.name, unsupported, subsetCategory));
                    int visibleUnsupported = view.VisibleLayerCount();
                    Check(visibleUnsupported == visibleSupported - 1,
                          string.Format("{0}: 숨겨진 레이어 수가 1개가 아니다 ({1} -> {2})",
                                        target.name, visibleSupported, visibleUnsupported));
                    Check(visibleUnsupported > 0,
                          target.name + ": 미지원 애니메이션에서 몸통까지 사라졌다");

                    view.SetState(supported, direction, 0);
                    Check(subsetRenderer.sprite != null && subsetRenderer.enabled,
                          target.name + ": 지원 애니메이션으로 돌아왔는데 복원되지 않았다");
                    Check(view.VisibleLayerCount() == visibleSupported,
                          target.name + ": 복귀 후 보이는 레이어 수가 다르다");
                    Debug.LogFormat("[SUBSET] {0}: {1} 는 '{2}' 보임 / '{3}' 숨김 / 복귀 시 복원",
                                    target.name, subsetCategory, supported, unsupported);
                }
                finally
                {
                    Object.DestroyImmediate(instance);
                }
            }
        }

        static SpriteRenderer FindRenderer(GameObject instance, CharacterView view,
                                           string category)
        {
            string[] slots = view.Slots;
            var renderers = instance.GetComponentsInChildren<SpriteRenderer>(true);
            if (slots == null) return null;
            for (int i = 0; i < slots.Length && i < renderers.Length; i++)
                if (slots[i] == category) return renderers[i];
            return null;
        }

        static string PrefabSlotSignature(string dir, CharacterAppearance appearance)
        {
            string prefabPath = string.Format("{0}/{1}_{2}.prefab",
                                              dir, appearance.profile, appearance.seed);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefab == null) return null;
            var parts = new List<string>();
            foreach (SpriteRenderer renderer in prefab.GetComponentsInChildren<SpriteRenderer>(true))
                parts.Add(renderer.gameObject.name + ":" + renderer.sortingOrder);
            return string.Join(",", parts.ToArray());
        }

        static void TestResolution(List<CharacterAppearance> appearances, string manifestPath)
        {
            CharacterAppearance first = appearances[0];
            string dir = Path.GetDirectoryName(manifestPath).Replace('\\', '/') + "/Generated";
            string prefabPath = string.Format("{0}/{1}_{2}.prefab", dir, first.profile, first.seed);
            var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
            if (prefab == null) return;

            GameObject instance = Object.Instantiate(prefab);
            try
            {
                var view = instance.GetComponent<CharacterView>();
                Check(view != null, "CharacterView 가 없다");
                if (view == null) return;

                // 방향이 있는 팩인지 라벨에서 판단한다 (하드코딩하지 않는다)
                var categories = new List<string>(first.library.GetCategoryNames());
                var labels = new List<string>(first.library.GetCategoryLabelNames(categories[0]));
                labels.Sort();
                string sample = labels[0];
                string[] bits = sample.Split(new[] { CharacterView.LabelSeparator },
                                             System.StringSplitOptions.None);
                bool directional = bits.Length == 3;
                string animation = bits[0];
                string direction = directional ? bits[1] : "";

                view.SetState(animation, direction, 0);
                int visible = view.VisibleLayerCount();
                Check(visible > 0,
                      first.name + ": 어떤 레이어도 스프라이트를 해결하지 못했다");
                // 프리팹은 프로파일 전체 슬롯을 갖는다. 이 appearance 가 쓰는 슬롯만 보여야 한다.
                Check(visible == first.layers.Length,
                      string.Format("{0}: appearance 레이어 {1}개인데 {2}개가 보인다 "
                                    + "(프리팹 슬롯 {3}개)",
                                    first.name, first.layers.Length, visible,
                                    view.Slots != null ? view.Slots.Length : -1));

                // 7. 없는 애니메이션 -> 레이어가 숨겨지되 예외가 나지 않는다
                view.SetState("no_such_animation", direction, 0);
                Check(view.VisibleLayerCount() == 0,
                      first.name + ": 없는 애니메이션인데 레이어가 남아 있다");

                // 8. 다시 정상 상태로 돌아오는가 (숨김이 영구적이면 안 된다)
                view.SetState(animation, direction, 0);
                Check(view.VisibleLayerCount() == first.layers.Length,
                      first.name + ": 정상 상태로 복귀하지 못했다");

                // 9. 방향이 실제로 다른 스프라이트를 고르는가
                if (directional)
                {
                    var directions = new HashSet<string>();
                    foreach (string label in labels)
                    {
                        string[] parts = label.Split(
                            new[] { CharacterView.LabelSeparator },
                            System.StringSplitOptions.None);
                        if (parts.Length == 3 && parts[0] == animation) directions.Add(parts[1]);
                    }
                    Check(directions.Count > 1, first.name + ": 방향이 1개뿐이다");

                    var seen = new HashSet<string>();
                    foreach (string d in directions)
                    {
                        view.SetState(animation, d, 0);
                        var renderer = instance.GetComponentInChildren<SpriteRenderer>();
                        if (renderer != null && renderer.sprite != null)
                            seen.Add(renderer.sprite.name);
                    }
                    Check(seen.Count == directions.Count,
                          first.name + ": 방향마다 다른 스프라이트가 나오지 않는다");
                }
            }
            finally
            {
                Object.DestroyImmediate(instance);
            }
        }

        /// <summary>
        /// 이번 POC 의 핵심 질문: appearance 를 바꿔도 애니메이션 상태가 유지되는가.
        /// </summary>
        static void TestAppearanceSwapKeepsAnimatorState()
        {
            var all = new List<CharacterAppearance>();
            foreach (string guid in AssetDatabase.FindAssets("t:CharacterAppearance"))
            {
                var asset = AssetDatabase.LoadAssetAtPath<CharacterAppearance>(
                    AssetDatabase.GUIDToAssetPath(guid));
                if (asset != null) all.Add(asset);
            }
            all.Sort((a, b) => (a.profile + a.seed).CompareTo(b.profile + b.seed));

            var byProfile = new Dictionary<string, List<CharacterAppearance>>();
            foreach (CharacterAppearance a in all)
            {
                List<CharacterAppearance> list;
                if (!byProfile.TryGetValue(a.profile, out list))
                {
                    list = new List<CharacterAppearance>();
                    byProfile[a.profile] = list;
                }
                list.Add(a);
            }

            foreach (KeyValuePair<string, List<CharacterAppearance>> pair in byProfile)
            {
                if (pair.Value.Count < 2) continue;
                CharacterAppearance a = pair.Value[0];
                CharacterAppearance b = pair.Value[1];

                string dir = Path.GetDirectoryName(AssetDatabase.GetAssetPath(a)).Replace('\\', '/');
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(
                    string.Format("{0}/{1}_{2}.prefab", dir, a.profile, a.seed));
                if (prefab == null) continue;

                GameObject instance = Object.Instantiate(prefab);
                try
                {
                    var view = instance.GetComponent<CharacterView>();
                    var categories = new List<string>(a.library.GetCategoryNames());
                    var labels = new List<string>(a.library.GetCategoryLabelNames(categories[0]));
                    labels.Sort();
                    string[] bits = labels[0].Split(
                        new[] { CharacterView.LabelSeparator }, System.StringSplitOptions.None);
                    bool directional = bits.Length == 3;
                    string animation = bits[0];
                    string direction = directional ? bits[1] : "";

                    // 애니메이션 중간 프레임에서 교체한다
                    int midFrame = 1;
                    view.SetState(animation, direction, midFrame);
                    string beforeAnimation = view.CurrentAnimation;
                    string beforeDirection = view.CurrentDirection;
                    int beforeFrame = view.CurrentFrame;

                    // 첫 렌더러가 이 appearance 의 미사용 선택 슬롯일 수 있다.
                    // 보이는 레이어 전체 조합으로 비교한다.
                    string beforeSignature = VisibleSpriteSignature(instance);

                    view.SetAppearance(b);

                    // 상태 3축이 그대로여야 한다 — 이게 유지되지 않으면
                    // 걷다가 외형만 바꿔도 애니메이션이 리셋된다.
                    Check(view.CurrentAnimation == beforeAnimation,
                          pair.Key + ": swap 후 animation 이 바뀌었다");
                    Check(view.CurrentDirection == beforeDirection,
                          pair.Key + ": swap 후 direction 이 바뀌었다");
                    Check(view.CurrentFrame == beforeFrame,
                          pair.Key + ": swap 후 frame 이 바뀌었다");
                    Check(view.Appearance == b, pair.Key + ": appearance 가 교체되지 않았다");
                    Check(view.VisibleLayerCount() > 0,
                          pair.Key + ": swap 후 아무 레이어도 안 보인다");

                    string afterSignature = VisibleSpriteSignature(instance);
                    Check(!string.IsNullOrEmpty(afterSignature),
                          pair.Key + ": swap 후 보이는 스프라이트가 없다");
                    if (!SameAssets(a, b))
                    {
                        Check(beforeSignature != afterSignature,
                              pair.Key + ": 파츠가 다른데 스프라이트 조합이 그대로다");
                    }
                    Debug.LogFormat("[SWAP] {0}: seed {1} -> {2}, state {3}/{4}/{5} 유지",
                                    pair.Key, a.seed, b.seed, view.CurrentAnimation,
                                    view.CurrentDirection, view.CurrentFrame);
                }
                finally
                {
                    Object.DestroyImmediate(instance);
                }
            }
        }
    }
}
