import glob
import json
from parse_meeting import convert_meeting

def build_jsonl(input_glob, output_path):
    all_data = []

    for path in glob.glob(input_glob):
        meeting_data = convert_meeting(path)
        all_data.extend(meeting_data)

    with open(output_path, "w", encoding="utf-8") as f:
        for item in all_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

if __name__ == "__main__":
    build_jsonl(
        input_glob="data/translated/ami/*.json",
        output_path="data/processed/train.jsonl"
    )
