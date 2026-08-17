using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace ArtFactory.EditorTools
{
    /// <summary>
    /// runtime manifest 의 animation topology 로 AnimationClip 과 AnimatorController 를
    /// 자동 생성한다. 사람이 Animation 창에서 손으로 만들지 않는다.
    ///
    /// ## clip 이 담는 것
    ///
    /// **`CharacterView.frame` 정수 하나뿐이다.** 외형(hair_03 같은 asset)은 clip 에
    /// 들어가지 않는다. 그래서 같은 profile 의 모든 appearance 가 **같은 clip 을 공유**하고,
    /// 외형 교체는 SpriteLibraryAsset 만 갈아끼우면 된다.
    ///
    /// ## direction 을 clip 에 넣지 않는 이유
    ///
    /// 방향별 clip 을 만들면 LPC 기준 3 animation x 4 direction = 12 clip 이 되고,
    /// 방향이 1개인 애니메이션(hurt/climb)이 섞이면 조합이 더 늘어난다.
    /// frame 만 키프레임하면 clip 은 animation 당 1개(3개)면 충분하고, 방향은
    /// `CharacterView.SetDirection()` 이 라벨을 만들 때 합친다.
    /// **더 작은 쪽을 골랐다.** 방향 정보는 라벨과 manifest 에 그대로 남는다.
    /// </summary>
    public static class AnimationClipBuilder
    {
        /// <summary>Animator 의 motion 파라미터 이름. **여기가 단일 출처다.**
        /// 게임 코드는 이 문자열을 알 필요가 없다 — CharacterProfile 이 들고 간다.</summary>
        public const string MotionParameter = "Motion";

        /// <summary>animation 이름 -> (frameCount, frameRate).</summary>
        public struct ClipSpec
        {
            public string animation;
            public int frameCount;
            public int frameRate;
        }

        /// <summary>clip 들을 만들고 (animation -> clip) 으로 돌려준다.</summary>
        public static Dictionary<string, AnimationClip> BuildClips(
            string outDir, string profile, IEnumerable<ClipSpec> specs)
        {
            var clips = new Dictionary<string, AnimationClip>();
            foreach (ClipSpec spec in specs)
            {
                string path = string.Format("{0}/{1}_{2}.anim", outDir, profile, spec.animation);
                // **지우고 다시 만들지 않는다.** 삭제하면 .meta 가 사라져 GUID 가 바뀌고,
                // 이미 이 clip 을 참조하던 controller / 게임 에셋의 참조가 끊긴다.
                // 기존 에셋이 있으면 내용만 갈아끼운다 (in-place update).
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
                bool isNew = clip == null;
                if (isNew) clip = new AnimationClip();
                FillClip(clip, spec);
                if (isNew) AssetDatabase.CreateAsset(clip, path);
                else EditorUtility.SetDirty(clip);
                clips[spec.animation] = clip;
            }
            return clips;
        }

        static void FillClip(AnimationClip clip, ClipSpec spec)
        {
            int rate = spec.frameRate > 0 ? spec.frameRate : 12;
            clip.ClearCurves();
            clip.frameRate = rate;

            // frame 은 정수라 보간하면 안 된다. 계단(step) 커브로 만든다 —
            // 탄젠트를 무한대로 두면 다음 키까지 값이 유지된다.
            var keys = new Keyframe[spec.frameCount + 1];
            for (int i = 0; i < spec.frameCount; i++)
            {
                keys[i] = new Keyframe(i / (float)rate, i,
                                       float.PositiveInfinity, float.PositiveInfinity);
            }
            // 마지막 키는 길이를 확정하기 위한 것이다 (loop 지점).
            keys[spec.frameCount] = new Keyframe(spec.frameCount / (float)rate,
                                                 spec.frameCount - 1,
                                                 float.PositiveInfinity,
                                                 float.PositiveInfinity);
            var curve = new AnimationCurve(keys);

            // 경로는 빈 문자열 = CharacterView 가 붙은 루트 오브젝트.
            clip.SetCurve("", typeof(CharacterView), "frame", curve);

            AnimationClipSettings settings = AnimationUtility.GetAnimationClipSettings(clip);
            settings.loopTime = true;
            AnimationUtility.SetAnimationClipSettings(clip, settings);
        }

        /// <summary>
        /// 최소 AnimatorController. state 마다 CharacterAnimationState 를 붙여
        /// 애니메이션 **이름**을 CharacterView 에 알려준다.
        ///
        /// parameter 는 `Motion`(int) 하나뿐이다. 게임용 이동 컨트롤러는 만들지 않는다.
        /// </summary>
        public static AnimatorController BuildController(
            string outDir, string profile, Dictionary<string, AnimationClip> clips,
            IList<string> order, Dictionary<string, int> motionMapping = null)
        {
            string path = string.Format("{0}/{1}_controller.controller", outDir, profile);
            // clip 과 같은 이유로 in-place 갱신한다. controller 를 지우면
            // 프리팹의 Animator 참조가 끊긴다.
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(path);
            if (controller == null)
            {
                controller = AnimatorController.CreateAnimatorControllerAtPath(path);
            }
            else
            {
                ClearController(controller);
            }
            controller.AddParameter(MotionParameter, AnimatorControllerParameterType.Int);
            AnimatorStateMachine machine = controller.layers[0].stateMachine;

            var states = new List<AnimatorState>();
            for (int i = 0; i < order.Count; i++)
            {
                string animation = order[i];
                AnimationClip clip;
                if (!clips.TryGetValue(animation, out clip)) continue;

                AnimatorState state = machine.AddState(animation);
                state.motion = clip;
                var behaviour = state.AddStateMachineBehaviour<CharacterAnimationState>();
                behaviour.animationName = animation;
                // **명시적 매핑을 여기서 만든다.** 배열 순서가 우연히 맞기를 기대하지 않는다.
                // controller state 와 CharacterProfile 의 매핑이 같은 자리에서 나온다.
                if (motionMapping != null) motionMapping[animation] = states.Count;
                states.Add(state);
                if (states.Count == 1) machine.defaultState = state;
            }

            // Motion 값으로 어느 state 든 서로 오갈 수 있게 한다. 최소 구성이다.
            for (int i = 0; i < states.Count; i++)
            {
                for (int j = 0; j < states.Count; j++)
                {
                    if (i == j) continue;
                    AnimatorStateTransition transition = states[i].AddTransition(states[j]);
                    transition.AddCondition(AnimatorConditionMode.Equals, j, MotionParameter);
                    transition.hasExitTime = false;
                    transition.duration = 0f;
                }
            }
            EditorUtility.SetDirty(controller);
            return controller;
        }

        /// <summary>
        /// controller 의 내용만 비운다. **에셋 자체는 지우지 않는다** — 지우면 GUID 가
        /// 바뀌고 프리팹의 Animator 참조가 끊긴다.
        ///
        /// state 를 지우면 그 state 로 들어오고 나가는 transition 과 붙어 있던
        /// StateMachineBehaviour 도 함께 사라진다.
        /// </summary>
        static void ClearController(AnimatorController controller)
        {
            AnimatorStateMachine machine = controller.layers[0].stateMachine;
            foreach (ChildAnimatorState child in new List<ChildAnimatorState>(machine.states))
            {
                machine.RemoveState(child.state);
            }
            for (int i = controller.parameters.Length - 1; i >= 0; i--)
            {
                controller.RemoveParameter(i);
            }
        }
    }
}
