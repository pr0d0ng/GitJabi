import json
from typing import List, Dict

LABEL_MAP = {
    "OTHER": 0,
    "KEY": 1,
    "ACTION": 2
}

def load_translated_meeting(path: str) -> List[Dict]:
    """
    한국어 번역된 회의 발화 로드
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # data: List[utterance]
    return data

def assign_label(utterance: Dict) -> int:
    """
    ❗ 여기서 라벨링 규칙을 나중에 계속 바꿈
    지금은 placeholder
    """

    text = utterance["text"]

    # 예시 rule (임시)
    if any(k in text for k in ["해야", "하겠습니다", "합시다"]):
        return LABEL_MAP["ACTION"]

    return LABEL_MAP["OTHER"]

def convert_meeting(translated_path: str) -> List[Dict]:
    utterances = load_translated_meeting(translated_path)
    results = []

    for utt in utterances:
        label = assign_label(utt)

        results.append({
            "utt_id": utt.get("id"),
            "speaker": utt.get("speaker"),
            "text": utt["text"],
            "label": label,
            "meta": {
                "meeting_id": utt.get("meeting_id"),
                "start_time": float(utt.get("starttime", 0)),
                "end_time": float(utt.get("endtime", 0))
            }
        })

    return results
