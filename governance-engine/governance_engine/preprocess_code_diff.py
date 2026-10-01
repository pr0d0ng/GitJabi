import os
import json
from typing import Dict, Any, List
from openai import AsyncAzureOpenAI

from governance_engine.modules.llm_code_summary import (
    prompt_analyze_diff_chunked_async,
    convert_json_to_text_prompt
)


class CodeDiffSummarizerLLM:
    """
    사용자 요청의 모든 항목을 포함한 깊이 있는 diff 분석:

    파일 단위 요약: 각 파일의 변경 목적과 영향도
    변경된 핵심 함수: 함수/메서드명, 변경 유형, 영향도 분석
    보안/검증 변경: 입력값 검증, 보안 설정, 민감 정보 처리 변화
    외부 API 통신 변화: 새 API, 기존 API 수정, 인증 방식 변경
    잠재적 리스크: Breaking Change, 데이터 손실, 성능, 호환성 등
    핵심 메트릭: 라인 수, 복잡도, 의존성 추가 여부
    """

    def __init__(self):
        # Azure OpenAI
        self.async_aoai_client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
        )

    async def async_diff_summarize(self, diff_text):
        result = await prompt_analyze_diff_chunked_async(
            async_aoai_client=self.async_aoai_client,
            deployment_name="deployment",
            pr_context={
                "title": "주요 리팩토링",
                "body": "대규모 아키텍처 변경",
                "diff": diff_text 
            },
            max_chunk_size=4000,  
            clean_first=True 
        )
        if __debug__:
            with open('./debug/1_CODE_DIFF_LLM_요약_test.json', 'w', encoding='utf-8') as j:
                j.write(json.dumps(result, indent=4, ensure_ascii=False))

        return result

    def convert_json_to_text(self, result):
        return convert_json_to_text_prompt(result, format_type='structured')
