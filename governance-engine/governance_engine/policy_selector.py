import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

from governance_engine.modules.policy_vector_query import prompt_process_pr_for_compliance, format_compliance_context


load_dotenv()


class PolicySelector:
    """
    Stage1:
    PR Context 기반으로 점검해야 할 compliance tag를 LLM으로 추천하고,
    Azure AI Search에서 해당 tag 기반 정책을 검색하는 모듈
    """

    def __init__(self):

        # Azure OpenAI
        self.aoai_client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        )

        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT")

        # Azure AI Search
        self.search_client = SearchClient(
            endpoint=os.getenv("AZURE_SEARCH_ENDPOINT"),
            index_name=os.getenv("AZURE_SEARCH_INDEX"),
            credential=AzureKeyCredential(os.getenv("AZURE_SEARCH_API_KEY"))
        )

    # -----------------------------
    # 외부 호출 메인 함수
    # -----------------------------
    def evaluate(self, pr_context: Dict[str, Any], code_diff: str) -> Dict[str, Any]:
        # recommended_tags = self._recommend_tags(pr_context)
        results = prompt_process_pr_for_compliance(
            self.aoai_client,
            self.deployment_name,
            pr_context,
            code_diff=code_diff
        )
        results["formatted"] = format_compliance_context(results)

        # policies = self._search_by_tags(results["tags"])
        return results

    # -----------------------------
    # LLM 기반 tag 추천
#     # -----------------------------
#     def _recommend_tags(self, pr_context: Dict[str, Any]) -> List[str]:

#         title = pr_context.get("title", "")
#         body = pr_context.get("body", "")
#         diff = pr_context.get("diff", "")

#         prompt = f"""
# You are a compliance tag classifier.

# Given the PR information and code diff,
# select the most relevant compliance tags (max 5).

# Return ONLY JSON:

# {{
#   "tags": ["tag1", "tag2", ...]
# }}

# PR Title:
# {title}

# PR Description:
# {body}

# Code Diff:
# {diff[:2000]}
# """

#         response = self.aoai_client.chat.completions.create(
#             model=self.deployment_name,
#             messages=[
#                 {"role": "system", "content": "You classify PRs into compliance tags."},
#                 {"role": "user", "content": prompt}
#             ],
#             temperature=0.1
#         )

#         content = response.choices[0].message.content

#         try:
#             parsed = json.loads(content)
#             return parsed.get("tags", [])
#         except Exception:
#             return []

    # # -----------------------------
    # # Azure AI Search에서 tag 필터 검색
    # # -----------------------------
    # def _search_by_tags(self, tags: List[str], top_n: int = 5) -> List[Dict[str, Any]]:

    #     if not tags:
    #         return []

    #     tag_filters = " or ".join([f"tag/any(t: t eq '{tag}')" for tag in tags])

    #     results = self.search_client.search(
    #         search_text="*",
    #         filter=tag_filters,
    #         top=top_n
    #     )

    #     policies = []

    #     for doc in results:
    #         policies.append({
    #             "node_id": doc["node_id"],
    #             "title": doc["title"],
    #             "content": doc["content"],
    #             "risk_level": doc["risk_level"],
    #             "tag": doc["tag"]
    #         })

    #     return policies
