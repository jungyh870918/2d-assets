using UnityEngine;
using UnityEngine.U2D.Animation;

namespace ArtFactory
{
    /// <summary>
    /// appearance 와 animation state 를 잇는 런타임 컴포넌트.
    ///
    /// 핵심은 <see cref="SetAppearance"/> 다. 외형을 바꿀 때 **SpriteLibraryAsset 만
    /// 교체**하고 Animator 는 건드리지 않는다. category / label 이름이 appearance 마다
    /// 동일하므로 같은 AnimationClip 이 그대로 계속 재생되고, 현재 재생 위치도 유지된다.
    ///
    /// 라벨 규약 (파이프라인의 runtime_export.py 와 동일):
    ///     "&lt;animation&gt;__&lt;direction&gt;__&lt;frame:00&gt;"   방향이 있는 팩
    ///     "&lt;animation&gt;__&lt;frame:00&gt;"                       방향이 없는 팩
    ///
    /// 어떤 파츠가 특정 애니메이션을 지원하지 않으면 그 라벨이 라이브러리에 없다.
    /// 그때 Resolver 는 null 을 돌려주고 이 컴포넌트는 그 레이어의 렌더러만 끈다.
    /// 몸통 애니메이션은 계속 돈다 — missing_animation_policy = hide_layer.
    /// </summary>
    [DisallowMultipleComponent]
    public class CharacterView : MonoBehaviour
    {
        public const string LabelSeparator = "__";

        [SerializeField] CharacterAppearance appearance;
        [SerializeField] SpriteLibrary spriteLibrary;
        [Tooltip("프로파일 전체 슬롯. appearance 가 안 쓰는 슬롯도 여기 있다 — " +
                 "프리팹 구조가 appearance 마다 같아야 AnimationClip 을 공유할 수 있다.")]
        [SerializeField] string[] slots;
        [SerializeField] SpriteResolver[] resolvers;
        [SerializeField] SpriteRenderer[] renderers;

        [Header("현재 상태 (Animator 가 정한다)")]
        [SerializeField] string animation = "idle";
        [SerializeField] string direction = "";
        [SerializeField] int frame;

        public CharacterAppearance Appearance { get { return appearance; } }
        public string CurrentAnimation { get { return animation; } }
        public string CurrentDirection { get { return direction; } }
        public int CurrentFrame { get { return frame; } }

        /// <summary>
        /// 켜질 때 한 번은 반드시 반영한다.
        ///
        /// SetAnimation / SetDirection 은 값이 같으면 조기 반환하는데, 직렬화된 초기값과
        /// 첫 상태가 우연히 같으면 Apply 가 한 번도 안 걸려 스프라이트가 비어 있게 된다.
        /// 실제로 방향이 없는 팩(CC0)에서 이 문제로 아무것도 안 그려졌다.
        /// </summary>
        void OnEnable()
        {
            Apply();
        }

        /// <summary>에디터 툴이 프리팹을 만들 때 채워 넣는다.</summary>
        public void Bind(CharacterAppearance value, SpriteLibrary library,
                         string[] slotNames, SpriteResolver[] slotResolvers,
                         SpriteRenderer[] slotRenderers)
        {
            appearance = value;
            spriteLibrary = library;
            slots = slotNames;
            resolvers = slotResolvers;
            renderers = slotRenderers;
        }

        public string[] Slots { get { return slots; } }

        /// <summary>
        /// 외형만 교체한다. **Animator 상태를 건드리지 않는다.**
        /// 이게 Sprite Library 를 쓰는 핵심 이유다.
        /// </summary>
        public void SetAppearance(CharacterAppearance value)
        {
            if (value == null) return;
            appearance = value;
            if (spriteLibrary != null)
            {
                spriteLibrary.spriteLibraryAsset = value.library;
            }
            Apply();
        }

        /// <summary>Animator 나 게임 코드가 현재 상태를 알려준다.</summary>
        public void SetState(string newAnimation, string newDirection, int newFrame)
        {
            animation = newAnimation;
            direction = newDirection;
            frame = newFrame;
            Apply();
        }

        /// <summary>어떤 동작인지. AnimatorController 의 state 가 진입할 때 알려준다.</summary>
        public void SetAnimation(string newAnimation)
        {
            if (animation == newAnimation) return;
            animation = newAnimation;
            Apply();
        }

        /// <summary>어느 쪽을 보는지. 게임 로직(입력/AI)이 정한다.</summary>
        public void SetDirection(string newDirection)
        {
            if (direction == newDirection) return;
            direction = newDirection;
            Apply();
        }

        /// <summary>
        /// Animator 가 <c>frame</c> 을 쓴 직후 Unity 가 불러준다.
        ///
        /// AnimationClip 은 **frame 정수 하나만** 키프레임한다. 외형(어떤 파츠인지)은
        /// clip 에 들어가지 않으므로, 같은 clip 을 모든 appearance 가 공유한다.
        /// 여기서 현재 (animation, direction, frame) 을 라벨로 바꿔 Resolver 에 넘긴다.
        /// </summary>
        void OnDidApplyAnimationProperties()
        {
#if UNITY_EDITOR
            _didApplyAnimationCallbacks++;
#endif
            Apply();
        }

#if UNITY_EDITOR
        // ── 테스트 계측 ────────────────────────────────────────────────
        // UNITY_EDITOR 안에만 있어서 빌드된 게임에는 들어가지 않는다.
        // Play Mode 에서 "Animator 가 frame 을 바꾸면 콜백이 자동으로 오는가" 를
        // 실측하기 위한 카운터일 뿐, 런타임 동작에는 관여하지 않는다.
        int _didApplyAnimationCallbacks;
        int _applyCalls;

        public int DidApplyAnimationCallbackCount { get { return _didApplyAnimationCallbacks; } }
        public int ApplyCallCount { get { return _applyCalls; } }

        public void ResetInstrumentation()
        {
            _didApplyAnimationCallbacks = 0;
            _applyCalls = 0;
        }
#endif

        public static string BuildLabel(string animation, string direction, int frame)
        {
            if (string.IsNullOrEmpty(direction))
            {
                return string.Format("{0}{1}{2:D2}", animation, LabelSeparator, frame);
            }
            return string.Format("{0}{1}{2}{1}{3:D2}",
                                 animation, LabelSeparator, direction, frame);
        }

        /// <summary>현재 상태를 모든 레이어의 Resolver 에 반영한다.</summary>
        public void Apply()
        {
#if UNITY_EDITOR
            _applyCalls++;
#endif
            if (resolvers == null || slots == null) return;
            string label = BuildLabel(animation, direction, frame);

            for (int i = 0; i < resolvers.Length && i < slots.Length; i++)
            {
                SpriteResolver resolver = resolvers[i];
                if (resolver == null) continue;
                string category = slots[i];

                // 라이브러리에 그 (category, label) 이 실제로 있는지 먼저 본다.
                // 없으면 Resolver 는 직전 스프라이트를 그대로 두므로, 숨김 정책을
                // Unity 내부 동작에 맡기지 않고 여기서 명시적으로 처리한다.
                //   - 이 appearance 가 안 쓰는 슬롯       -> category 자체가 없다
                //   - 이 파츠가 지원하지 않는 애니메이션   -> label 이 없다
                // 둘 다 "그 레이어만 숨기고 나머지는 계속 재생" 으로 같게 다룬다.
                Sprite resolved = spriteLibrary != null
                    ? spriteLibrary.GetSprite(category, label)
                    : null;

                if (resolved != null)
                {
                    resolver.SetCategoryAndLabel(category, label);
                    resolver.ResolveSpriteToSpriteRenderer();
                }

                if (renderers != null && i < renderers.Length && renderers[i] != null)
                {
                    renderers[i].sprite = resolved;
                    renderers[i].enabled = resolved != null;
                }
            }
        }

        /// <summary>현재 상태에서 실제로 보이는 레이어 수. 테스트/디버그용.</summary>
        public int VisibleLayerCount()
        {
            int count = 0;
            if (renderers == null) return 0;
            for (int i = 0; i < renderers.Length; i++)
            {
                if (renderers[i] != null && renderers[i].enabled &&
                    renderers[i].sprite != null) count++;
            }
            return count;
        }
    }
}
