using UnityEngine;

namespace ArtFactory
{
    /// <summary>
    /// AnimatorController 의 state 하나가 "어떤 동작인지"를 CharacterView 에 알려준다.
    ///
    /// AnimationClip 은 문자열을 키프레임할 수 없어서 애니메이션 **이름**은 clip 이 아니라
    /// state 가 들고 있다. clip 은 frame 정수만 진행시킨다.
    ///
    ///     state(Walk)  -> view.SetAnimation("walk")     이름
    ///     clip(walk)   -> view.frame = 0,1,2,...        진행
    ///     게임 로직     -> view.SetDirection("south")     방향
    ///
    /// 셋이 분리되어 있어서 appearance 를 바꿔도 Animator 는 영향을 받지 않는다.
    /// </summary>
    public class CharacterAnimationState : StateMachineBehaviour
    {
        [Tooltip("이 state 가 재생하는 애니메이션 이름. Sprite Library 라벨의 앞부분이 된다.")]
        public string animationName;

        public override void OnStateEnter(Animator animator, AnimatorStateInfo stateInfo,
                                          int layerIndex)
        {
            if (string.IsNullOrEmpty(animationName)) return;
            var view = animator.GetComponent<CharacterView>();
            if (view != null) view.SetAnimation(animationName);
        }
    }
}
