import os
from typing import Any, Dict, List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import (
    VectorizableTextQuery,
)
from governance_engine.modules.nlp_keyword_extract import NLPKeywordExtractDispatcher

class KnowledgeNodeSearcher:
    """
    Stage2:
    Azure AI Search에서 정책(Policy) 문서를 검색해서
    Stage1에서 추천된 tags에 해당하는 정책 후보들을 반환한다.
    """

    def __init__(self):
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT", "").strip()
        api_key = os.getenv("AZURE_SEARCH_API_KEY", "").strip()
        index_name = os.getenv("AZURE_SEARCH_INDEX", "").strip()

        if not endpoint or not api_key or not index_name:
            raise ValueError(
                "Azure AI Search env missing. "
                "AZURE_SEARCH_ENDPOINT / AZURE_SEARCH_API_KEY / AZURE_SEARCH_INDEX 설정해라."
            )

        self.top_k = int(os.getenv("AZURE_SEARCH_TOP_K", "20"))
        self.query_type = os.getenv("AZURE_SEARCH_QUERY_TYPE", "simple").strip().lower()
        self.semantic_config = os.getenv("AZURE_SEARCH_SEMANTIC_CONFIG", "").strip() or None

        self.client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=AzureKeyCredential(api_key),
        )

    # -------------------------------------------------
    # Stage2 메인 함수
    # -------------------------------------------------
    def search_nodes(
        self,
        policy_id: str,
        policy_title: str,
        policy_keywords: List[str],
        policy_tags: List[str],
        pr_diff: Optional[str]=None,
        # pr_context: Dict[str, Any],
        top_k: Optional[int] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        select_fields = ["node_id", "title", "content", "risk_level", "tag"]

        top_k = top_k or self.top_k

        # PR 기반 검색 텍스트 생성
        # title = pr_context.get("title", "")
        # body = pr_context.get("body", "")
        # diff = pr_context.get("diff", "")

        search_text = f"정책 제목: {policy_title} \n주요 키워드: {policy_keywords}"

        # tag 기반 필터 생성
        tag_filter = self._tags_to_filter(policy_tags)

        # B. 하이브리드 검색을 위한 벡터 쿼리 설정
        vector_query = VectorizableTextQuery(
            text=search_text, 
            k_nearest_neighbors=5, 
            fields="content_vector", # 인덱스의 벡터 필드명
            exhaustive=True
        )
        # C. 메타데이터 필터 구성 (OData 구문)
        # 도메인이 일치하고 위험도가 동일한 노드 위주로 필터링
        # filter_query = f"domain eq '{policy['domain']}' and risk_level eq '{policy['risk_level']}'"

        try:
            if self.query_type == "semantic":
                knowledge_nodes = self.client.search(
                    search_text=search_text,
                    filter=tag_filter,
                    top=top_k,
                    query_type="semantic",
                    semantic_configuration_name=self.semantic_config,
                    select=select_fields,
                )
            else:
                knowledge_nodes = self.client.search(
                    search_text=search_text, 
                    vector_queries=[vector_query], 
                    filter=tag_filter,
                    select=select_fields, 
                    top=top_k
                    # query_type="semantic", # 시맨틱 랭커 사용 시 (선택 사항)
                    # semantic_configuration_name="my-semantic-config", # 인덱스에 설정된 이름
                    # query_answer=QueryAnswerType.EXTRACTIVE,    # AI가 답변 추출
                    # query_caption=QueryCaptionType.EXTRACTIVE,
                )
        except Exception as e:
            raise RuntimeError(f"Azure AI Search 호출 실패: {str(e)}")

        nodes: List[Dict[str, Any]] = []

        for i, doc in enumerate(knowledge_nodes, start=0):
            score = doc.get('@search.score', 0.0)
            rerank = doc.get("@search.reranker_score", None)     # 시맨틱 재정렬 점수
            semantic_summ = doc.get("@search.captions", None)
            semantic_highligts = doc.get("@search.highlights", None)
            
            if rerank is not None:
                try:
                    score = float(rerank)
                except ValueError as e:
                    print(e)
            if score < min_score:
                continue

            nodes.append({
                "idx": i,
                "node_id": doc.get("node_id"),
                "title": doc.get("title"),
                "content": doc.get("content"),
                "risk_level": doc.get("risk_level"),
                "tag": doc.get("tag"),
                "formatted": (f"node_id: {doc.get("node_id")} \n"
                              f"title: {doc.get("title")} \n"
                              f"content: {doc.get("content")} \n"
                              f"tag: {doc.get("tag")} \n"
                              f"risk_level: {doc.get("risk_level")}"),
                "_related_policy_id": policy_id,
                "_score": score,
                "_semantic_summary": semantic_summ, 
                "_semantic_highlights": semantic_highligts
            })
        nodes.sort(
            key=lambda x: x.get("_score", 0.0), 
            reverse=False
        )
        return nodes
    
    def rerank_nodes(self, pr_data, node_data, top_k: int=5):
        dispatcher = NLPKeywordExtractDispatcher()
        result = dispatcher.rerank(pr_data, node_data, top_k)
        ranked_items = result['results']
        return [{
                    **e['node'],
                    'base_score': e['base_score'],
                    'final_score': e['final_score']
                } 
                for e in ranked_items]

    # -------------------------------------------------
    # 내부 유틸
    # -------------------------------------------------
    def _tags_to_filter(self, tags: List[str]) -> Optional[str]:
        if not tags:
            return None
 
        cleaned = [t.strip() for t in tags if t]
        if not cleaned:
            return None

        # 'eq' 대신 'any(t: t eq 'value')' 형식을 사용합니다.
        # tag/any(t: t eq 'val1') or tag/any(t: t eq 'val2')
        ors = [f"tag/any(t: t eq '{self._escape_odata(t)}')" for t in cleaned]
        return "(" + " or ".join(ors) + ")"
    # def _tags_to_filter(self, tags: List[str]) -> Optional[str]:
    #     if not tags:
    #         return None

    #     cleaned = [t.strip() for t in tags if t]
    #     if not cleaned:
    #         return None

    #     ors = [f"tag eq '{self._escape_odata(t)}'" for t in cleaned]
    #     return "(" + " or ".join(ors) + ")"

    def _escape_odata(self, s: str) -> str:
        return s.replace("'", "''")


# def get_advanced_knowledge_search_parameters():
#     """지식 노드 검색을 위한 벡터 서치 파라미터를 반환"""
#     search_payload = {
#         "query": "취약한 API 사용 방지 및 대체 함수 사용 strcpy sprintf gets_s", # 하이브리드 쿼리
#         "select": ["node_id", "title", "content"],
#         "filter": "domain eq 'backend' and risk_level eq 'HIGH'",
#         "vector_queries": [
#             {
#                 "value": policy_content_vector, # 정책 content를 임베딩한 값
#                 "fields": "content_vector",
#                 "k": 5
#             }
#         ],
#         "top": 3 # 가장 연관성 높은 지식 노드 3개 추출
#     }



