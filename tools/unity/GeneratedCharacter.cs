using System;
using UnityEngine;

namespace ArtFactory
{
    /// <summary>
    /// 05_GENERATED 에서 나온 캐릭터 variation 하나. 06_UNITY_EXPORT 의 manifest.json 을
    /// GeneratedCharacterImporter 가 읽어서 이 에셋을 만든다.
    ///
    /// 여기에 게임 로직을 넣지 않는다. 조합 정의 + 스프라이트 참조만 들고 있는 자료구조다.
    /// </summary>
    [CreateAssetMenu(fileName = "GeneratedCharacter", menuName = "2D Art Factory/Generated Character")]
    public class GeneratedCharacter : ScriptableObject
    {
        [Serializable]
        public struct PartSlot
        {
            [Tooltip("규칙 파일의 슬롯 이름 (head, hair, weapon ...)")]
            public string slot;

            [Tooltip("소스 팩의 파츠 이름 (head2, hair3 ...)")]
            public string part;

            [Tooltip("이 슬롯에 적용된 팔레트 ramp id. 비어 있으면 원본 색 유지.")]
            public string ramp;
        }

        [Serializable]
        public struct AnimationClipSheet
        {
            public string animation;
            public int frameRate;

            [Tooltip("시트를 셀 단위로 슬라이스한 결과. 프레임 순서대로.")]
            public Sprite[] frames;
        }

        [Header("정체")]
        public string pack;
        public string profile;
        public string archetype;
        public int seed;

        [Header("조합")]
        public PartSlot[] parts;
        public string paletteName;

        [Header("스프라이트")]
        public Sprite preview;
        public AnimationClipSheet[] sheets;

        /// <summary>해당 애니메이션의 프레임을 찾는다. 없으면 null.</summary>
        public Sprite[] GetFrames(string animation)
        {
            if (sheets == null) return null;
            for (int i = 0; i < sheets.Length; i++)
            {
                if (sheets[i].animation == animation) return sheets[i].frames;
            }
            return null;
        }

        /// <summary>해당 슬롯에 어떤 파츠가 들어갔는지. 없으면 빈 문자열.</summary>
        public string GetPart(string slot)
        {
            if (parts == null) return string.Empty;
            for (int i = 0; i < parts.Length; i++)
            {
                if (parts[i].slot == slot) return parts[i].part;
            }
            return string.Empty;
        }
    }
}
