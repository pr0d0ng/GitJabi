import re
from copy import deepcopy

def filter_relevant_compliance(
        compliance_list, 
        pr_event, 
        diff_text
    ):
    """
    PR 이벤트와 컴플라이언스 목록 간의 연관성을 분석하여 필터링합니다.
    """
    data = deepcopy(compliance_list)
    final_inspection_list = []
    
    changed_files = pr_event.get("files", [])
    changed_extensions = {f.split('.')[-1].lower() for f in changed_files if '.' in f}

    for policy in data:
        score = 0
        policy_content = policy.get("content", "").lower()
        policy_tags = [t.lower() for t in policy.get("tag", [])]
        
        # --- A. 파일 확장자 기반 필터링 (기초 점수) ---
        for ext in changed_extensions:
            if ext in policy_tags or ext in policy.get("domain", "").lower():
                score += 30  # 강력한 연관성 가점
        
        # --- B. 키워드 매칭 (함수명, 보안 키워드) ---
        keywords = re.findall(r"(\w+)\(\)", policy_content)
        keywords.extend(policy_tags)
        
        match_count = 0
        for kw in set(keywords):
            if kw in diff_text:
                match_count += 1
        
        if match_count > 0:
            score += (match_count * 20) 
            
        # --- C. 검색 엔진 기반 유사도 가중치 ---
        score += (policy.get("similarity", 0) * 50)

        policy["_relevance_score"] = round(score, 2)
        final_inspection_list.append(policy)

    return sorted(final_inspection_list, key=lambda x: x["_relevance_score"], reverse=True)
