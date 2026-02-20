import random
import uuid
from datetime import datetime, timezone, timedelta

def random_merged_at(max_days_back: int = 14) -> str:
    """
    현재 UTC 기준으로
    max_days_back 일 이내의 랜덤 과거 시각 반환
    ISO 8601 (Z) 형식
    """
    now = datetime.now(timezone.utc)

    delta_seconds = random.randint(0, max_days_back * 24 * 60 * 60)

    merged_time = now - timedelta(seconds=delta_seconds)

    return merged_time.replace(microsecond=0).isoformat().replace("+00:00", "Z")

def build_pr_webhook_payload(scenario):
    _rand_repo = random.choice(["backend", "api", "program", "solution", "frontend", "dashboard"]) + "-random-repo"
    language = scenario.get("language")
    repo_name = scenario.get("repo_name", _rand_repo)
    pr_number = random.randint(1, 10000)
    now = datetime.now(timezone.utc).isoformat() + "Z"
    sha = uuid.uuid4().hex[:40]
    diff = scenario.get("diff")

    is_merged = bool(scenario.get("is_merged"))
    merged_at = random_merged_at()
    action = scenario.get("action", "closed" if is_merged else "opened")
    
    merged_by = None

    if is_merged:
        merged_by = {
            "login": f"maintainer_{random.randint(1,20)}",
            "id": random.randint(1000, 9999),
            "type": "User",
            "site_admin": False
        }

    payload = {
        "action": action,
        "number": pr_number,
        "pull_request": {
            "id": random.randint(1000000000, 9999999999),
            "number": pr_number,
            "state": action,
            "title": scenario["title"],
            "body": scenario["body"],
            "created_at": now,
            "updated_at": now,
            "merged_at": merged_at if is_merged else None,
            "merged": is_merged,
            "merged_by": merged_by,
            "draft": False,
            "mergeable_state": "clean" if is_merged else "unknown",
            "commits": 1,
            "additions": scenario["additions"],
            "deletions": scenario["deletions"],
            "changed_files": scenario["changed_files"],
            "user": {
                "login": f"user_{random.randint(1,100)}",
                "id": random.randint(10000, 99999),
                "type": "User",
                "site_admin": False
            },
            "head": {
                "ref": "dev",
                "sha": sha
            },
            "base": {
                "ref": "main",
                "sha": uuid.uuid4().hex[:40]
            }
        },
        "repository": {
            "name": f"{repo_name}",
            "full_name": f"my-organization/{repo_name}",
            "private": False,
            "language": language,
            "default_branch": "main"
        },
        "additional_custom_data": {
            "diff": f"{diff}"
        }
    }

    return payload
