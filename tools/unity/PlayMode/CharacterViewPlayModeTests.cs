using System.Collections;
using System.Collections.Generic;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.TestTools;
using UnityEngine.U2D.Animation;
#if UNITY_EDITOR
using UnityEditor;
#endif

namespace ArtFactory.PlayModeTests
{
    /// <summary>
    /// **이 파일이 검증하는 것은 딱 하나다:**
    /// 실제 Play Mode 에서 Animator 가 `CharacterView.frame` 을 진행시키면
    /// `OnDidApplyAnimationProperties()` 가 자동으로 불려 스프라이트가 갱신되는가.
    ///
    /// EditMode batchmode 테스트에서는 그 메시지가 보장되지 않아
    /// `view.Apply()` 를 명시 호출해야 했다. 여기서는 **절대 호출하지 않는다.**
    /// 재생 중 Apply 를 부르면 검증 자체가 무의미해진다.
    ///
    /// 실행:
    ///   Unity -runTests -testPlatform PlayMode -projectPath &lt;proj&gt; \
    ///         -testResults results.xml -batchmode
    /// </summary>
    public class CharacterViewPlayModeTests
    {
        const float FrameRate = 8f;

        class Observation
        {
            public HashSet<int> frames;
            public HashSet<string> labels;
            public HashSet<string> sprites;
            public int callbacks;
            public int applyCalls;
            public string direction;
            public string animation;
        }

        static GameObject LoadPrefab(string profileHint)
        {
#if UNITY_EDITOR
            foreach (string guid in AssetDatabase.FindAssets("t:Prefab"))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (!path.Contains(profileHint)) continue;
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab != null && prefab.GetComponent<CharacterView>() != null &&
                    prefab.GetComponent<Animator>() != null)
                {
                    return prefab;
                }
            }
#endif
            return null;
        }

        /// <summary>현재 보이는 모든 레이어의 스프라이트 이름. 슬롯 순서 유지.</summary>
        static List<string> SpriteNames(GameObject instance)
        {
            var names = new List<string>();
            foreach (SpriteRenderer r in instance.GetComponentsInChildren<SpriteRenderer>(true))
                if (r.enabled && r.sprite != null) names.Add(r.sprite.name);
            return names;
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

        /// <summary>
        /// 일정 시간 재생하며 관찰만 한다. **Apply() 를 부르지 않는다.**
        /// </summary>
        static IEnumerator Observe(GameObject instance, float seconds, Observation result)
        {
            var view = instance.GetComponent<CharacterView>();

            result.frames = new HashSet<int>();
            result.labels = new HashSet<string>();
            result.sprites = new HashSet<string>();

            float elapsed = 0f;
            while (elapsed < seconds)
            {
                // 관찰만 한다. 여기서 Apply() 를 부르면 검증이 무의미해진다.
                result.frames.Add(view.CurrentFrame);
                result.labels.Add(CharacterView.BuildLabel(
                    view.CurrentAnimation, view.CurrentDirection, view.CurrentFrame));
                // 첫 렌더러 하나만 보면 그 슬롯이 미사용 선택 슬롯일 때 영영 null 이다.
                // 보이는 레이어 전체 조합을 본다.
                string signature = string.Join("|", SpriteNames(instance).ToArray());
                if (!string.IsNullOrEmpty(signature)) result.sprites.Add(signature);

                elapsed += Time.deltaTime;
                yield return null;
            }

            result.animation = view.CurrentAnimation;
            result.direction = view.CurrentDirection;
#if UNITY_EDITOR
            result.callbacks = view.DidApplyAnimationCallbackCount;
            result.applyCalls = view.ApplyCallCount;
#endif
        }

        IEnumerator RunProfile(string profileHint, bool expectDirection)
        {
            GameObject prefab = LoadPrefab(profileHint);
            Assert.IsNotNull(prefab, profileHint + ": Animator 가 붙은 프리팹을 찾지 못했다");

            GameObject instance = Object.Instantiate(prefab);
            try
            {
                var view = instance.GetComponent<CharacterView>();
                var animator = instance.GetComponent<Animator>();
                Assert.IsNotNull(animator.runtimeAnimatorController,
                                 profileHint + ": AnimatorController 가 없다");

                // ── setup (재생 전) ──────────────────────────────────────
                string direction = FirstDirection(view.Appearance);
                if (!string.IsNullOrEmpty(direction)) view.SetDirection(direction);
                Assert.AreEqual(expectDirection, !string.IsNullOrEmpty(direction),
                                profileHint + ": 방향 축 유무가 예상과 다르다");

                // 한 프레임 돌려 Animator 를 초기화한 뒤 계측을 0 으로
                yield return null;
#if UNITY_EDITOR
                view.ResetInstrumentation();
#endif
                int startFrame = view.CurrentFrame;

                // ── 재생 (Apply 호출 없음) ───────────────────────────────
                var observed = new Observation();
                yield return Observe(instance, 1.5f, observed);

                // 1. frame 이 실제로 진행했는가
                Assert.Greater(observed.frames.Count, 1,
                    string.Format("{0}: frame 이 진행하지 않았다 (start={1}, 관찰={2})",
                                  profileHint, startFrame,
                                  string.Join(",", new List<int>(observed.frames).ConvertAll(x => x.ToString()).ToArray())));

                // 2. 라벨도 frame 을 따라 바뀌었는가
                Assert.Greater(observed.labels.Count, 1,
                               profileHint + ": 라벨이 바뀌지 않았다");

                // 3. **실제 스프라이트**가 바뀌었는가 — 이게 핵심이다.
                //    Apply() 를 부르지 않았는데 스프라이트가 바뀌었다면
                //    OnDidApplyAnimationProperties 가 자동으로 불린 것이다.
                Assert.Greater(observed.sprites.Count, 1,
                    string.Format("{0}: frame 은 바뀌는데 스프라이트가 그대로다 " +
                                  "(수동 Apply 없이 갱신되지 않음). sprites={1}",
                                  profileHint, observed.sprites.Count));

#if UNITY_EDITOR
                // 4. 콜백이 실제로 발생했는가
                Assert.Greater(observed.callbacks, 0,
                               profileHint + ": OnDidApplyAnimationProperties 가 한 번도 안 불렸다");
                Assert.AreEqual(observed.callbacks, observed.applyCalls,
                    string.Format("{0}: Apply 호출({1})이 콜백({2})보다 많다 — " +
                                  "재생 중 누군가 Apply 를 따로 불렀다",
                                  profileHint, observed.applyCalls, observed.callbacks));
                Debug.LogFormat("[PLAYMODE] {0}: frames={1} labels={2} sprites={3} " +
                                "callbacks={4} applyCalls={5} animation={6} direction='{7}'",
                                profileHint, observed.frames.Count, observed.labels.Count,
                                observed.sprites.Count, observed.callbacks,
                                observed.applyCalls, observed.animation, observed.direction);
#endif

                // 5. direction 이 유지되는가
                if (expectDirection)
                {
                    Assert.AreEqual(direction, observed.direction,
                                    profileHint + ": 재생 중 direction 이 바뀌었다");
                    foreach (string label in observed.labels)
                    {
                        StringAssert.Contains(CharacterView.LabelSeparator + direction +
                                              CharacterView.LabelSeparator, label,
                                              profileHint + ": 라벨에서 방향이 빠졌다: " + label);
                    }
                }

                Assert.Greater(view.VisibleLayerCount(), 0,
                               profileHint + ": 재생 중 보이는 레이어가 없다");
            }
            finally
            {
                Object.Destroy(instance);
            }
        }

        [UnityTest]
        public IEnumerator Cc0_AutoAppliesAnimatedFrames()
        {
            yield return RunProfile("cc0_test_population", false);
        }

        [UnityTest]
        public IEnumerator Lpc_AutoAppliesAnimatedFrames_AndKeepsDirection()
        {
            yield return RunProfile("lpc_phase2_showcase", true);
        }

        [UnityTest]
        public IEnumerator AppearanceSwapDuringPlayback_KeepsStateAndKeepsAnimating()
        {
            GameObject prefab = LoadPrefab("lpc_phase2_showcase");
            Assert.IsNotNull(prefab, "프리팹을 찾지 못했다");

            CharacterAppearance other = null;
#if UNITY_EDITOR
            var all = new List<CharacterAppearance>();
            foreach (string guid in AssetDatabase.FindAssets("t:CharacterAppearance"))
            {
                var a = AssetDatabase.LoadAssetAtPath<CharacterAppearance>(
                    AssetDatabase.GUIDToAssetPath(guid));
                if (a != null && a.profile == "lpc_phase2_showcase") all.Add(a);
            }
            all.Sort((x, y) => x.seed.CompareTo(y.seed));
            if (all.Count >= 2) other = all[1];
#endif
            Assert.IsNotNull(other, "swap 대상 appearance 가 없다");

            GameObject instance = Object.Instantiate(prefab);
            try
            {
                var view = instance.GetComponent<CharacterView>();
                var animator = instance.GetComponent<Animator>();
                var renderer = instance.GetComponentInChildren<SpriteRenderer>();
                string direction = FirstDirection(view.Appearance);
                if (!string.IsNullOrEmpty(direction)) view.SetDirection(direction);

                // 잠깐 재생해서 애니메이션 중간 지점으로
                float t = 0f;
                while (t < 0.5f) { t += Time.deltaTime; yield return null; }

                AnimatorStateInfo before = animator.GetCurrentAnimatorStateInfo(0);
                string beforeAnimation = view.CurrentAnimation;
                string beforeDirection = view.CurrentDirection;
                float beforeTime = before.normalizedTime;
                // 첫 렌더러 하나만 보면 안 된다 — 두 appearance 가 그 슬롯에서
                // 같은 파츠를 쓸 수 있다 (여기서는 둘 다 hair_braid).
                // 전체 렌더러의 스프라이트 조합을 본다.
                List<string> beforeSprites = SpriteNames(instance);

                view.SetAppearance(other);   // setup 성격의 명시 호출 — 재생 갱신과 다르다

                AnimatorStateInfo after = animator.GetCurrentAnimatorStateInfo(0);
                Assert.AreEqual(before.fullPathHash, after.fullPathHash,
                                "swap 후 Animator state 가 바뀌었다");
                Assert.AreEqual(beforeTime, after.normalizedTime, 0.0001f,
                                "swap 후 normalizedTime 이 리셋됐다");
                Assert.AreEqual(beforeAnimation, view.CurrentAnimation,
                                "swap 후 animation 이 바뀌었다");
                Assert.AreEqual(beforeDirection, view.CurrentDirection,
                                "swap 후 direction 이 바뀌었다");
                Assert.AreEqual(other, view.Appearance, "appearance 가 교체되지 않았다");

                // swap 이후에도 **자동으로** 계속 진행되는가 (Apply 호출 없음)
#if UNITY_EDITOR
                view.ResetInstrumentation();
#endif
                var observed = new Observation();
                yield return Observe(instance, 1.0f, observed);

                Assert.Greater(observed.frames.Count, 1, "swap 후 frame 이 멈췄다");
                Assert.Greater(observed.sprites.Count, 1,
                               "swap 후 스프라이트가 자동 갱신되지 않는다");
                Assert.AreEqual(beforeDirection, observed.direction,
                                "swap 후 direction 이 바뀌었다");
#if UNITY_EDITOR
                Assert.Greater(observed.callbacks, 0,
                               "swap 후 콜백이 오지 않는다");
                Debug.LogFormat("[PLAYMODE-SWAP] frames={0} sprites={1} callbacks={2} " +
                                "applyCalls={3} normalizedTime {4:F4} -> {5:F4}",
                                observed.frames.Count, observed.sprites.Count,
                                observed.callbacks, observed.applyCalls,
                                beforeTime, after.normalizedTime);
#endif
                // 두 appearance 가 실제로 다른 파츠를 쓰는 슬롯이 있으면
                // 스프라이트 조합도 달라져야 한다.
                bool partsDiffer = false;
                var beforeAssets = new HashSet<string>();
                foreach (var l in view.Appearance.layers) beforeAssets.Add(l.slot + "=" + l.asset);
                var otherAssets = new HashSet<string>();
                foreach (var l in other.layers) otherAssets.Add(l.slot + "=" + l.asset);
                partsDiffer = !beforeAssets.SetEquals(otherAssets);

                List<string> afterSprites = SpriteNames(instance);
                Assert.Greater(afterSprites.Count, 0, "swap 후 스프라이트가 하나도 없다");
                if (partsDiffer)
                {
                    CollectionAssert.AreNotEqual(beforeSprites, afterSprites,
                        "파츠 구성이 다른데 스프라이트 조합이 그대로다");
                }
            }
            finally
            {
                Object.Destroy(instance);
            }
        }
    }
}
