using System;
using UnityEngine;
using UnityEngine.U2D.Animation;

namespace ArtFactory
{
    /// <summary>
    /// 한 캐릭터의 **외형**. 애니메이션 상태는 담지 않는다.
    ///
    /// 책임 분리:
    ///   CharacterAppearance : 어떤 파츠를 입었는가 (appearance)
    ///   Animator            : 지금 어떤 animation / direction / frame 인가 (state)
    ///   SpriteResolver      : 그 둘을 합쳐 현재 스프라이트를 고른다
    ///
    /// 그래서 이 에셋에는 frame 이 없다. frame 을 여기 저장하면 appearance 를 바꿀 때마다
    /// 애니메이션이 리셋되고, 그게 정확히 Sprite Library 로 피하려는 문제다.
    ///
    /// source of truth 는 파이프라인의 character.json 이다. 이 에셋은 그 변환물이며
    /// seed 로 원본을 되짚을 수 있다.
    /// </summary>
    [CreateAssetMenu(fileName = "CharacterAppearance",
                     menuName = "2D Art Factory/Character Appearance")]
    public class CharacterAppearance : ScriptableObject
    {
        [Serializable]
        public struct VisualLayer
        {
            [Tooltip("정규 슬롯 이름. Sprite Library 의 category 와 같다.")]
            public string slot;

            [Tooltip("이 슬롯에 들어간 소스 asset 이름 (추적용).")]
            public string asset;

            [Tooltip("렌더 순서. 소스가 zPos 를 선언하면 그 값, 아니면 layer_order 순번.")]
            public int zOrder;
        }

        [Header("정체")]
        public string profile;
        public string pack;
        public int seed;
        public string archetype;

        [Header("외형")]
        [Tooltip("렌더 순서(zOrder) 오름차순. 한 logical item 이 여러 layer 를 가질 수 있으므로 " +
                 "slot 이 중복될 수 있다 — 배열이지 사전이 아니다.")]
        public VisualLayer[] layers;

        [Tooltip("이 appearance 의 스프라이트를 담은 라이브러리. 교체하면 외형이 바뀐다.")]
        public SpriteLibraryAsset library;

        [Header("원점")]
        public string originPolicy;
        public float pixelsPerUnit = 100f;

        [Header("출처 / 표기 의무")]
        public bool attributionRequired;
        public bool shareAlikePresent;
        public string[] authors;
        public string[] licenses;

        public int LayerCount { get { return layers != null ? layers.Length : 0; } }
    }
}
