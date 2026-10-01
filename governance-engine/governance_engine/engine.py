import json, uuid
from datetime import timezone, datetime
from typing import Dict, Any, List, TYPE_CHECKING, Optional

from governance_engine.policy_selector import PolicySelector
from governance_engine.rag_node_searcher import KnowledgeNodeSearcher
from governance_engine.final_judge_evaluator import PolicyComplianceEvaluator
from governance_engine.rule_engine import RuleEngine
from governance_engine.pr_parser import PRParser
from governance_engine.modules.repository import PolicyRepository
from governance_engine.modules.filter_relevant_compliance import filter_relevant_compliance
from governance_engine.modules.nlp_keyword_extract import extract_keywords_in_policies_list
if TYPE_CHECKING:
    from psycopg2.extensions import connection

class GovernanceEngine:

    def __init__(self, db_connection: "connection"):
        self.selector = PolicySelector()          # Stage1
        self.node_searcher = KnowledgeNodeSearcher()          # Stage2
        self.evaluator = PolicyComplianceEvaluator()  # Stage3
        self.rule_engine = RuleEngine()

        self.db_connection = db_connection

    def run(
            self, 
            payload: Dict[str, Any],
            diff_text='',
            event_id=None
        ) -> Dict[str, Any]:

        time_now = datetime.now(timezone.utc)
        unique_suffix = str(uuid.uuid4())[:8] 
        run_id = f"RUN_{time_now.strftime('%Y%m%d_%H%M%S')}_{unique_suffix}"

        # ==========================================
        # 1 : 표준 PR Context 생성
        # ==========================================
        pr_context_raw = PRParser.parse(payload)
        print('Stage 1 : 데이터 전처리')

        if __debug__:
            with open('./debug/1_PR_전처리_test.json', 'w', encoding='utf-8') as j:
                j.write(json.dumps(pr_context_raw, indent=4, ensure_ascii=False))

        # ==========================================
        # 2 : Rule Engine (정적 검사)
        # ==========================================
        rule_results = self.rule_engine.check(pr_context_raw)
        print('Stage 2 : 룰베이스 검사 체크 완료.')

        # ==========================================
        # Stage 3-1 . 소형 LLM 기반 PR에 대한 요약 추출
        # ==========================================
        pr_llm_summary = self.selector.evaluate(pr_context_raw, code_diff=diff_text)
        tags: List[str] = pr_llm_summary.get("tags", [])
        print('Stage 3-1 : PR 이벤트 내용 추출(LLM) 완료.')

        if __debug__:
            with open('./debug/3_PR_LLM_요약_결과_test.json', 'w', encoding='utf-8') as j:
                j.write(json.dumps(pr_llm_summary, indent=4, ensure_ascii=False))

        # ==========================================
        # Stage 3-2 . 추상적 컴플라이언스 쿼리 
        # ==========================================
        policy_repo = PolicyRepository(
            self.db_connection
        )
        _vector_results = policy_repo.vector_search(
            pr_llm_summary["formatted"]
        )
        print(f'Stage 3-2 : 추상적 컴플라이언스 PSQL로 부터 벡터 검색 ({len(_vector_results)} 건) - 끝.')

        # =====================================================
        #  Stage 3-3: 컴플라이언스 - PR 연관성 필터 및 키워드 추출
        # =====================================================
        filtered_policies = filter_relevant_compliance(
            _vector_results,
            pr_context_raw,
            diff_text,
            # code_diff_summarized_text,
        )
        filtered_policies = extract_keywords_in_policies_list(
            filtered_policies
        )

        if __debug__:
            with open('./debug/3-3_검색된_정책목록_test_(필터).json', 'w', encoding='utf-8') as j:
                j.write(json.dumps(filtered_policies, indent=4, ensure_ascii=False))

        print('Stage 3-3 : 쿼리된 컴플라이언스와 PR 상관관계 분석 후 필터/스코어링 - 끝.')

        # ==========================================
        # Stage 4: RAG 기반 지식 노드 검색
        # ==========================================
        # 검색된 정책 별로 반복문 Loop (MVP 이므로 비동기 생략)
        _contains_node_ids = set()
        searched_all_k_nodes = []
        for i, pl in enumerate(filtered_policies, start=1):
            k_nodes = self.node_searcher.search_nodes(
                policy_id=pl["policy_id"],
                policy_title=pl["title"],
                policy_keywords=pl['keywords_ext'],
                policy_tags=pl["tag"],
                top_k=3
            )
            for n in k_nodes:
                if n['node_id'] in _contains_node_ids:
                    continue
                searched_all_k_nodes.append(n)
                _contains_node_ids.add(n['node_id'])
            print(f'     {i} 번째 정책으로 지식 노드 검색 결과 ({len(k_nodes)} 건):', str(k_nodes)[:50], '...')

        searched_all_k_nodes.sort(key=lambda x: x['_score'], reverse=True)
        print('Stage 4 : 지식 노드 검색 (RAG) 완료.')

        if __debug__:
            with open(f'./debug/4_지식노드_검색_결과_종합_test.json', 'w', encoding='utf-8') as j:
                j.write(json.dumps(searched_all_k_nodes, indent=4, ensure_ascii=False))

        # ==========================================
        # Stage 4-2 : 검색 된 지식문서 종합 필터링
        # ==========================================
        _pr_temp_data = pr_context_raw
        _pr_temp_data["summary"] = pr_llm_summary['summary']
        reranked_k_nodes = self.node_searcher.rerank_nodes(
            _pr_temp_data,
            searched_all_k_nodes,
            top_k=10
        )
        print('Stage 4-2 : 검색된 지식 노드에 대한 CrossEncoder 기반 Rerank 정렬 완료')
        
        # ==========================================
        # Stage 5: 정책 위반 여부 LLM 판단
        # ==========================================
        print('Stage 5 : 정책 위반 여부 LLM 판단 시작...')
        violations = self.evaluator.evaluate(
            pr_context_raw, 
            pr_llm_summary,
            filtered_policies,
            knowledge_nodes=reranked_k_nodes,
            code_diff_text=diff_text
        )

        print('모든 스테이지 완료.')
        # ==========================================
        # 최종 결과 조합
        # ==========================================
        final_result = {
            "run_id": run_id,
            "executed_at": str(time_now),
            "event_id": event_id,
            "rulebase_violations": rule_results,
            "compliance_violations": violations
        }
        return final_result
