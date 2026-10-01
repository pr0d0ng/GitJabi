from typing import Dict, Any, List


class PRParser:
    """
    GitHub webhook payload를
    내부 표준 PR Context 구조로 변환한다.

    이 모듈은 오직 '정규화(normalization)'만 담당한다.
    특정 Stage나 rule_engine에 종속되지 않는다.
    """

    @staticmethod
    def parse(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        payload: GitHub webhook JSON
        diff: 외부에서 수집한 PR diff 문자열 (없으면 빈 문자열)
        """

        pr = payload.get("pull_request", {})

        # 라벨 이름만 추출
        labels: List[str] = [
            label.get("name")
            for label in pr.get("labels", [])
            if isinstance(label, dict)
        ]

        # 리뷰어 login만 추출
        reviewers: List[str] = [
            reviewer.get("login")
            for reviewer in pr.get("requested_reviewers", [])
            if isinstance(reviewer, dict)
        ]

        return {
            # 기본 식별
            "id": pr.get("id"),
            "number": pr.get("number"),

            # 핵심 내용
            "title": pr.get("title", "") or "",
            "body": pr.get("body", "") or "",

            # 메타 정보
            "labels": labels,
            "reviewers": reviewers,
            "author": pr.get("user", {}).get("login"),

            # 브랜치 정보
            "base_branch": pr.get("base", {}).get("ref"),
            "head_branch": pr.get("head", {}).get("ref"),

            # 변경 통계
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "changed_files": pr.get("changed_files", 0),
            "commits": pr.get("commits", 0),

            # 상태
            "state": pr.get("state"),
            "draft": pr.get("draft", False),
            "merged": pr.get("merged", False),
        }
    

def build_dict_pr_data_for_prompt(
        pr_context,
        pr_llm_summary
):
    """프롬프트에 적합한 형태로 데이터 구조 변경"""
    allowed_cols = (
        "id", "number", "title", "body", "diff", "labels",
        "reviewers", "author", "base_branch", "head_branch",
        "additions", "deletions", "changed_files", "commits",
        "state", "draft"
    )

    data = {}
    for k, v in pr_context.items():
        if k not in allowed_cols:
            continue
        data[k] = v

    for p, m in pr_llm_summary.items():
        if p in ('title', 'formatted'):
            continue
        data[p] = m
    return data
