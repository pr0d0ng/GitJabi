import os
import json, uuid
import logging
from datetime import datetime, timezone
from traceback import format_exc
from typing import Any, Dict, List
from collections import defaultdict
from openai import AzureOpenAI
from governance_engine.modules.prompt_utils import dict_to_prompt_yaml
from governance_engine.pr_parser import build_dict_pr_data_for_prompt
from governance_engine.data.eval_prompt_1 import EVAL_PROMPRT_V1

PR_WORD_CHANGE_MAPPING = {
    "diff": "diff(Code Changes)", 
    "base_branch": "base_branch(Merge destination)",
    "head_branch": "head_branch(Merge origin)",
    "additions": "additions(LoC)",
    "delitions": "delitions(removed LoC)",
    "changed_files": "changed_files(Changed files count)",
    "commits": "commits(Commits count)" 
}

class PolicyComplianceEvaluator:
    """
    Stage3:
    PR Context + 정책 문서를 기반으로
    실제 정책 위반 여부를 LLM으로 판단한다.
    고성능 LLM 전용 Azure OpenAI 리소스를 사용한다.
    """

    def __init__(self):

        # -----------------------------------------
        # Stage3 전용 Azure OpenAI 설정
        # -----------------------------------------
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT_STAGE3", "").strip()
        api_key = os.getenv("AZURE_OPENAI_API_KEY_STAGE3", "").strip()
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_STAGE3", "").strip()
        api_version = os.getenv("AZURE_OPENAI_API_VERSION_STAGE3", "").strip()

        if not endpoint or not api_key or not deployment or not api_version:
            raise ValueError(
                "Stage3 Azure OpenAI env missing.\n"
                "AZURE_OPENAI_ENDPOINT_STAGE3\n"
                "AZURE_OPENAI_API_KEY_STAGE3\n"
                "AZURE_OPENAI_DEPLOYMENT_STAGE3\n"
                "AZURE_OPENAI_API_VERSION_STAGE3\n"
                "모두 설정해라."
            )

        self.client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=endpoint,
        )

        self.deployment = deployment

    # -------------------------------------------------
    # Stage3 메인 함수
    # -------------------------------------------------
    def evaluate(
        self,
        pr_context_raw: Dict[str, Any],
        pr_llm_summary: Dict[str, Any],
        policies: List[Dict[str, Any]],
        knowledge_nodes: List[Dict[str, Any]],
        code_diff_text: str
    ) -> List[Dict[str, Any]]:
        if not knowledge_nodes:
            return []
        
        # 통합 PR 데이터
        pr_data_tuned = build_dict_pr_data_for_prompt(pr_context_raw, pr_llm_summary)
        if __debug__:
            # test
            with open(f'./debug/6_PR_데이터_통합본.json', 'w', encoding='utf-8') as j:
                j.write(json.dumps(pr_data_tuned, indent=4, ensure_ascii=False))

        # 컬럼명 LLM 친화적으로 변경
        pr_data_tuned = {PR_WORD_CHANGE_MAPPING.get(k, str(k)): v 
                         for k, v in pr_data_tuned.items()}
        
        # # PR Diff
        # diff_snippet = pr_context_raw['diff'][:max_code_diff_length]
        
        # 지식 노드 리스트를 grouping
        grouped_knodes = group_by(knowledge_nodes, '_related_policy_id')

        results = []
    
        for i, policy in enumerate(policies, start=1):
            if policy['policy_id'] not in grouped_knodes:
                logging.info(f"     {i} 번째 정책({policy['policy_id']})에 해당하는 지식 노드 없으므로 건너 뜀.")
                continue
            response = self._evaluate_single_policy(
                pr_data=pr_data_tuned,
                pr_diff=code_diff_text,
                policy=policy,
                knowledge_nodes=grouped_knodes[policy['policy_id']],
                index=i
            )
            if not response:
                logging.error(f"정책({policy['policy_id']})을 기반으로 LLM 최종 판단 평가 중 오류 발생.")
                continue
            results.append(response)

            # Test
            if __debug__:
                with open(f'./debug/6_최종_LLM_판단_결과_{i}.txt', 'w', encoding='utf-8') as fn:
                    fn.write(json.dumps(response, indent=4, ensure_ascii=False))

        return results

    # -------------------------------------------------
    # 개별 정책 판단
    # -------------------------------------------------
    def _evaluate_single_policy(
        self,
        pr_data: Dict[str, Any],
        pr_diff: str,
        policy: Dict[str, Any],
        knowledge_nodes: List[Dict[str, Any]],
        index=0
    ):
        t = datetime.now(timezone.utc)
        unique_suffix = str(uuid.uuid4())[:8] 
        scan_id = f"SCAN_{t.strftime('%Y%m%d_%H%M%S')}_{unique_suffix}"
        result = {
            'idx': index,
            'scan_id': scan_id,
            'related_pr_id': pr_data['id'],
            'related_pr_title': pr_data['title'],
            'related_policy_id': policy['policy_id'],
            'related_policy': policy['title'],
            'related_knowledge_nodes': [e['node_id'] for e in knowledge_nodes]
        }

        pr_data_for_prompt_text = dict_to_prompt_yaml(
            pr_data, ignored_cols=['diff', 'id']
        )
        policy_data_for_prompt_text = dict_to_prompt_yaml(
            policy, ignored_cols=['id', 'status', 'created_at', 'node_id', 'similarity', '_relevance_score']
        )

        knowledge_cards_text = "\n--------------------\n".join(
            [n["formatted"] for n in knowledge_nodes]
        )
        
        prompt = EVAL_PROMPRT_V1.format(
            policy_data_for_prompt_text=policy_data_for_prompt_text,
            pr_data_for_prompt_text=pr_data_for_prompt_text,
            pr_diff=pr_diff,
            knowledge_cards_text=knowledge_cards_text
        )

        # Test
        if __debug__:
            with open(f'./debug/6_최종_LLM_판단_프롬프트_test_{index}.txt', 'w', encoding='utf-8') as fn:
                fn.write(prompt)

        raw_output = None
        try:
            completion = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an enterprise-grade security compliance expert."
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                response_format={ "type": "json_object" }
            )

            raw_output = completion.choices[0].message.content.strip()
            _parsed = self._safe_json_parse(raw_output)
            result['output'] = _parsed
            return result
        except Exception as e:
            logging.error(f"{e} \nLLM Output: {raw_output} \n {format_exc()}")
        return None

    # -------------------------------------------------
    # JSON 안전 파싱
    # -------------------------------------------------
    def _safe_json_parse(self, text: str):
        try:
            return json.loads(text)
        except Exception:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end != -1:
                return json.loads(text[start:end])

def group_by(nodes: list[dict], key: str) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    
    for node in nodes:
        k = node.get(key, 'unclassified')
        grouped[k].append(node)
    return dict(grouped)
