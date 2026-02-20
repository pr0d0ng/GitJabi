from pathlib import Path
import re

OUTPUT_DIR = Path("output")

NUMBER_PREFIX_PATTERN = re.compile(r"^(\d+)")

def get_next_index():
    if not OUTPUT_DIR.exists():
        return 1

    max_index = 0

    for file in OUTPUT_DIR.glob("*.json"):
        match = NUMBER_PREFIX_PATTERN.match(file.stem)
        if match:
            number = int(match.group(1))
            max_index = max(max_index, number)

    return max_index + 1