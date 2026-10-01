import json
from typing import Dict, Any

def prompt_process_pr_for_compliance(
        aoai_client,
        deployment_name: str,
        pr_context: Dict[str, Any],
        code_diff: str,
        diff_trunacate_len:int = 4000
    ) -> Dict[str, Any]:
    """
    컴플라이언스 검색을 위한 PR 요약 가공
    """
    title = pr_context.get("title", "")
    body = pr_context.get("body", "")

    prompt = f"""
당신은 RAG와 컴플라이언스를 잘 이해하고 있는 데이터 추출 요약 전문가입니다.
제공된 PR(Pull Request)의 내용을 분석하여, 나중에 '컴플라이언스 정책'과 매칭하기 가장 좋은 형태로 가공하세요.

[분석 가이드라인]
1. 요약(content): 코드의 변경점이 보안이나 규정에 어떤 영향을 미치는지 중심으로 가능한 3~6문장 이내 요약.
2. 키워드(keywords): 요약(content) 내에서 의미 맥락적으로 가장 중요한 키워드 10가지 내외 선별하되, 언어(National Language)는 그대로 따라주세요. 필요시 N-Gram으로 확장해도 됩니다. (추후 벡터 검색에 용이하기 위함).
3. 태그(tags): 관련 보안 규정 검색을 위한 키워드(도메인, 기술 스택, 분야, 핵심 키워드, 라이브러리 등)를 영어로 작성. (예: Java, Security, Authentication, Sensitive Data, Cookie, XQuery, Secure Coding, Pandas 등)
4. 위험도(risk_level): CRITICAL, HIGH, MEDIUM, LOW 중 선택.
5. 도메인(domain): 해당되는 도메인 선택 (infra, backend, frontend, cloud, others).
6. 프로그래밍 언어(tech_stack): 사용된 프로그래밍 언어 영어로 1개 작성. (예: Python) 
7. 코드 분석(diff_metric): diff 내용을 분석. 변경 파일 목록(files), 핵심 함수/클래스명(functions), 핵심 변수명(variables), 사용 라이브러리(libraries). 

Return ONLY JSON (below is example):
{{
  "summary": "검색에 최적화된 요약 내용",
  "keywords": "API, C언어, 함수",
  "tags": ["태그1", "태그2"],
  "risk_level": "MEDIUM",
  "domain": "infra",
  "tech_stack": "Python",
  "diff_metric": {{
    "files": ["src/main.py"],
    "functions": ["observe()", "evaluate(param)", "class AbstractEngine"],
    "variables": ["API_KEY", "compliance_lists"],
    "libraries": ["pandas", "numpy", "fitz"]
  }}
}}

PR Title: {title}

PR Description: {body}

Code Diff:

{code_diff[:diff_trunacate_len]}
"""

    response = aoai_client.chat.completions.create(
        model=deployment_name,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={ "type": "json_object" } # JSON 모드 강제
    )
    result = json.loads(response.choices[0].message.content)
    result['title'] = title
    return result


def format_compliance_context(analysis: Dict[str, Any]) -> str:
    """
    LLM 분석 결과와 원본 제목을 조합하여 임베딩에 최적화된 텍스트를 생성합니다.
    """
    title = analysis.get("title", "")
    summary = analysis.get("summary", "")
    tags = ", ".join(analysis.get("tags", []))
    risk = analysis.get("risk_level", "LOW").upper()
    domain = analysis.get("domain", "GENERAL").lower()

    # 구조화된 포맷팅: 모델이 각 섹션의 의미를 명확히 파악할 수 있게 함
    formatted_text = (
        f"TITLE: {title}\n"
        f"DOMAIN: {domain}\n"
        f"RISK: {risk}\n"
        f"KEYWORDS: {tags}\n"
        f"SUMMARY: {summary}"
    )
    return formatted_text

