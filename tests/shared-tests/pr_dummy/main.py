import os, argparse
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
from pathlib import Path

from .scenario import generate_pr_scenario
from .webhook_builder import build_pr_webhook_payload
from .utils import get_next_index, OUTPUT_DIR




DEFAULT_COUNT = 1

async def generate_one(index: int, by_risk: bool):
    try:
        scenario = await generate_pr_scenario()
    except Exception as e:
        print(f"{index} 인덱스 작업중 오류 발생: {e}")
        return

    print(f"Index {index} Scenario: {scenario}")
    webhook_payload = build_pr_webhook_payload(scenario)

    data = {
        "scenario_meta": scenario,
        "webhook_event": webhook_payload,
    }

    risk_level = scenario.get("risk_level", "unknown")

    if by_risk:
        output_dir = OUTPUT_DIR / risk_level
    else:
        output_dir = OUTPUT_DIR

    output_dir.mkdir(parents=True, exist_ok=True)

    is_merged = data['scenario_meta']['is_merged']

    file_path = output_dir / f"{index}_{data['scenario_meta']['action']}_{"merged" if is_merged else "unmerged"}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data["webhook_event"], f, indent=2, ensure_ascii=False)

    print(f"Generated: {file_path}")


async def run(count: int, by_risk: bool, concurrency: int):
    OUTPUT_DIR.mkdir(exist_ok=True)

    start_index = get_next_index()

    semaphore = asyncio.Semaphore(concurrency)

    async def sem_task(i):
        async with semaphore:
            await generate_one(start_index + i, by_risk)

    await asyncio.gather(*(sem_task(i) for i in range(count)))

def main():
    parser = argparse.ArgumentParser(description="PR Dummy Generator")
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--by-risk", action="store_true")
    parser.add_argument("--concurrency", type=int, default=5)

    args = parser.parse_args()

    asyncio.run(run(args.count, args.by_risk, args.concurrency))

if __name__ == "__main__":
    main()