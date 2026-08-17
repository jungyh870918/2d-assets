using System;
using UnityEngine;

namespace ArtFactory
{
    /// <summary>
    /// 한 profile 의 런타임 진입점. **소비자가 아는 유일한 에셋이다.**
    ///
    /// 이게 없으면 게임 코드가 prefab / appearance 를 찾으려고 에셋 경로나
    /// 파일 이름 규칙을 알아야 한다. 그건 Factory 내부가 소비자로 새는 것이다.
    /// 여기에 참조를 모아 두면 게임은 이 에셋 하나만 들고 있으면 된다.
    ///
    /// SpriteLibraryBuilder 가 만든다. 사람이 손으로 채우지 않는다.
    /// </summary>
    [CreateAssetMenu(fileName = "CharacterProfile",
                     menuName = "2D Art Factory/Character Profile")]
    public class CharacterProfile : ScriptableObject
    {
        [Header("정체")]
        public string profile;
        public string pack;

        [Header("런타임 진입점")]
        [Tooltip("profile 전체 슬롯 topology 를 가진 프리팹. appearance 마다 다르지 않다.")]
        public GameObject prefab;

        [Tooltip("이 profile 이 제공하는 외형들. 순서는 결정적이다 (seed 정렬).")]
        public CharacterAppearance[] appearances;

        [Serializable]
        public struct MotionEntry
        {
            [Tooltip("애니메이션 이름. Sprite Library 라벨의 앞부분과 같다.")]
            public string animation;

            [Tooltip("이 애니메이션에 해당하는 Animator motion 파라미터 값.")]
            public int value;
        }

        [Header("애니메이션 topology")]
        public string[] animations;

        [Header("Animator 계약")]
        [Tooltip("Animator 의 motion 파라미터 이름. **게임 코드는 이 문자열을 몰라도 된다** — " +
                 "SetMotion() 을 쓰면 된다.")]
        public string motionParameterName = "Motion";

        [Tooltip("animation 이름 -> motion 값. 배열 순서에 기대지 않는 명시적 매핑이다. " +
                 "AnimatorController state 를 만들 때 같은 자리에서 생성된다.")]
        public MotionEntry[] motions;

        [Tooltip("이 profile 이 쓰는 방향. 방향 축이 없는 팩은 빈 배열이다.")]
        public string[] directions;

        [Header("stale 추적")]
        [Tooltip("이전 export 에 있었지만 지금 export 에는 없는 외형 에셋 경로. " +
                 "빌더가 지우지 않고 여기에 남긴다 — 게임이 아직 참조 중일 수 있으므로 " +
                 "발견 가능해야 하고, 자동 대체는 하지 않는다.")]
        public string[] staleAppearances;

        [Header("출처 추적")]
        [Tooltip("Factory 의 runtime manifest 경로. 소비자 런타임에는 필요 없고 추적용이다.")]
        public string sourceManifest;

        public int AppearanceCount { get { return appearances != null ? appearances.Length : 0; } }

        /// <summary>
        /// 애니메이션 이름으로 Animator 를 전환한다. **게임 코드의 유일한 진입점이다.**
        ///
        /// 게임은 파라미터 이름("Motion")도, state 순서도 알 필요가 없다.
        /// 없는 애니메이션이면 조용히 엉뚱한 state 로 보내지 않고 false 를 돌려주며
        /// 경고를 남긴다. fallback 애니메이션 시스템은 만들지 않는다.
        /// </summary>
        public bool SetMotion(Animator animator, string animation)
        {
            if (animator == null)
            {
                Debug.LogWarning("[ArtFactory] SetMotion: animator 가 null 이다");
                return false;
            }
            int value;
            if (!TryGetMotion(animation, out value))
            {
                Debug.LogWarningFormat(
                    "[ArtFactory] profile '{0}' 에 animation '{1}' 이 없다. "
                    + "가능한 값: {2}", profile, animation,
                    string.Join(", ", animations ?? new string[0]));
                return false;
            }
            animator.SetInteger(motionParameterName, value);
            return true;
        }

        /// <summary>animation 이름 -> motion 값. 없으면 false.</summary>
        public bool TryGetMotion(string animation, out int value)
        {
            value = 0;
            if (motions == null || string.IsNullOrEmpty(animation)) return false;
            for (int i = 0; i < motions.Length; i++)
            {
                if (motions[i].animation == animation)
                {
                    value = motions[i].value;
                    return true;
                }
            }
            return false;
        }

        public bool HasAnimation(string animation)
        {
            int ignored;
            return TryGetMotion(animation, out ignored);
        }

        /// <summary>
        /// 이 외형이 **지금 export 에도 여전히 들어 있는가.**
        ///
        /// 게임이 특정 외형을 직접 직렬화해 들고 있을 때, 재-export 로 그 외형이
        /// 빠졌는지 확인하는 유일한 방법이다. false 여도 다른 외형으로 바꿔 주지
        /// 않는다 — 무엇을 쓸지는 게임이 정한다.
        /// </summary>
        public bool Contains(CharacterAppearance appearance)
        {
            if (appearance == null || appearances == null) return false;
            for (int i = 0; i < appearances.Length; i++)
                if (appearances[i] == appearance) return true;
            return false;
        }

        /// <summary>이전 export 의 잔재가 남아 있는가. 있으면 사람이 정리해야 한다.</summary>
        public int StaleAppearanceCount
        {
            get { return staleAppearances != null ? staleAppearances.Length : 0; }
        }

        /// <summary>index 로 외형을 고른다. 범위를 벗어나면 순환한다.</summary>
        public CharacterAppearance AppearanceAt(int index)
        {
            if (appearances == null || appearances.Length == 0) return null;
            int i = index % appearances.Length;
            if (i < 0) i += appearances.Length;
            return appearances[i];
        }

        /// <summary>방향 축이 있는 profile 인가.</summary>
        public bool IsDirectional
        {
            get { return directions != null && directions.Length > 0; }
        }
    }
}
