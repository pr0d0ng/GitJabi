import os
from typing import Optional, List, Dict
from sentence_transformers import CrossEncoder


class KoreanTechReranker:

    def __init__(
        self,
        model_name: str,
        max_length: int = 512
    ):
        self.model = CrossEncoder(
            model_name, 
            max_length=max_length
        )

    # -----------------------------------
    # 1. PR 텍스트 구성 (기술 특화)
    # -----------------------------------
    def _build_pr_text(self, pr_data: Dict) -> str:
        return f"""
        [PR 제목]
        {pr_data.get("title")}

        [도메인]
        {pr_data.get("domain")}

        [위험도]
        {pr_data.get("risk_level")}

        [핵심 태그]
        {", ".join(pr_data.get("tags", []))}

        [요약]
        {pr_data.get("summary")}
        """

    # -----------------------------------
    # 2. Knowledge Node 텍스트 구성
    # -----------------------------------
    def build_node_text(self, node: Dict) -> str:
        return f"""
        [지식노드 제목]
        {node.get("title")}

        [위험도]
        {node.get("risk_level")}

        [관련 태그]
        {", ".join(node.get("tag", []))}

        [내용]
        {node.get("content")}
        """

    # -----------------------------------
    # 3. 메타 가중치 적용
    # -----------------------------------
    def _apply_meta_weight(
        self,
        pr_data: Dict,
        node: Dict,
        score: float
    ) -> float:

        weight = 1.0

        # Risk match bonus
        if pr_data.get("risk_level") == node.get("risk_level"):
            weight += 0.15

        # Tag overlap bonus
        pr_tags = set(pr_data.get("tags", []))
        node_tags = set(node.get("tag", []))
        overlap = len(pr_tags & node_tags)

        weight += 0.07 * overlap

        return score * weight

    # -----------------------------------
    # 4. Rerank 실행
    # -----------------------------------
    def rerank(
        self,
        pr_data: Dict,
        candidate_nodes: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:

        pr_text = self._build_pr_text(pr_data)

        pairs = [
            (pr_text, self.build_node_text(node))
            for node in candidate_nodes
        ]

        scores = self.model.predict(pairs)

        results = []

        for i, (node, score) in enumerate(zip(candidate_nodes, scores)):
            final_score = self._apply_meta_weight(pr_data, node, score)

            results.append({
                "no": i,
                "node": node,
                "base_score": float(score),
                "final_score": float(final_score),
                "risk_level": node.get("risk_level")
            })

        results.sort(key=lambda x: x["final_score"], reverse=True)

        return results[:top_k]