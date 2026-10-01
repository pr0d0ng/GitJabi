import json
from typing import Dict, Any, List, Tuple
import re
import asyncio

# =============================================================================
# Diff 정제 및 청크화 관련 함수들
# =============================================================================

def _clean_diff_content(diff: str) -> str:
    """
    diff 콘텐츠에서 불필요한 노이즈를 제거한다.
    
    제외 대상:
    - .txt 파일 (diff.txt, sample_pr.json 등 데이터 파일)
    - .lock, .yaml (패키지 락 파일)
    - 빈 파일 변경 (diff.txt처럼 내용이 없는 파일)
    
    포함 대상:
    - *.py (Python 코드)
    - *.ts, *.tsx, *.js (TypeScript/JavaScript)
    - *.md (마크다운 - 중요한 문서)
    - requirements.txt, package.json, pyproject.toml (의존성)
    - 기타 코드 파일
    """
    
    # 파일별로 diff 분리
    file_diffs = re.findall(r'diff --git .+\n(?:.*?\n)*?(?=diff --git|$)', diff, re.MULTILINE)
    
    cleaned_diffs = []
    
    # 제외할 파일 패턴들
    exclude_patterns = [
        r'\.txt$',           # difftext 파일
        r'\.lock$',          # lock 파일 (pnpm-lock.yaml, package-lock.json)
        r'pnpm-lock\.yaml',  # 패키지 락
        r'package-lock\.json',
        r'yarn\.lock',
        r'sample_pr\.json',  # 샘플 데이터
        r'/debug/',          # debug 폴더
        r'__pycache__',      # 캐시
        r'\.pyc$',           # 컴파일된 파일
    ]
    
    # 포함해야 할 중요 파일들
    essential_patterns = [
        r'requirements\.txt$',
        r'package\.json$',
        r'pyproject\.toml$',
        r'setup\.py$',
    ]
    
    for file_diff in file_diffs:
        # diff 헤더에서 파일명 추출
        match = re.search(r'diff --git a/(.+?) b/', file_diff)
        if not match:
            continue
            
        filename = match.group(1)
        
        # 필수 파일 우선 포함
        is_essential = any(re.search(pattern, filename) for pattern in essential_patterns)
        if is_essential:
            cleaned_diffs.append(file_diff)
            continue
        
        # 제외 패턴 체크
        should_exclude = any(re.search(pattern, filename) for pattern in exclude_patterns)
        if should_exclude:
            continue
        
        # 파일 확장자 체크 (코드 파일만)
        code_extensions = [
            r'\.py$', r'\.ts$', r'\.tsx$', r'\.js$', r'\.jsx$',
            r'\.java$', r'\.go$', r'\.rs$', r'\.cpp$', r'\.c$',
            r'\.md$', r'\.sh$', r'\.yaml$', r'\.yml$', r'\.json$',
            r'\.sql$', r'\.dockerfile$', r'Dockerfile$'
        ]
        
        is_code_file = any(re.search(ext, filename, re.IGNORECASE) for ext in code_extensions)
        if not is_code_file:
            continue
        
        # 빈 파일 변경 제외 (diff 내용이 거의 없음)
        if len(file_diff.strip()) < 100:
            continue
        
        cleaned_diffs.append(file_diff)
    
    return "\n".join(cleaned_diffs)


def _chunk_diff(diff: str, max_chunk_size: int = 3000) -> List[Tuple[str, List[str]]]:
    """
    diff를 파일 단위로 청크화한다.
    각 청크는 (청크_콘텐츠, 관련_파일명_리스트) 형태로 반환된다.
    
    Parameters:
    - diff: 정제된 diff 문자열
    - max_chunk_size: 한 청크의 최대 크기 (기본 3000자)
    
    Returns:
    - List[Tuple[str, List[str]]]: (청크 내용, 파일명 리스트) 튜플의 리스트
    """
    
    # 파일별로 diff 분리
    file_diffs = re.findall(r'diff --git .+\n(?:.*?\n)*?(?=diff --git|$)', diff, re.MULTILINE)
    
    chunks: List[Tuple[str, List[str]]] = []
    current_chunk = ""
    current_files = []
    
    for file_diff in file_diffs:
        # 파일명 추출
        match = re.search(r'diff --git a/(.+?) b/', file_diff)
        if not match:
            continue
            
        filename = match.group(1)
        file_size = len(file_diff)
        
        # 현재 청크에 파일을 추가했을 때의 크기
        new_chunk_size = len(current_chunk) + file_size
        
        # 새로운 청크로 시작해야 하는 경우
        if current_chunk and new_chunk_size > max_chunk_size:
            chunks.append((current_chunk, current_files))
            current_chunk = ""
            current_files = []
        
        # 현재 청크에 파일 추가
        current_chunk += file_diff + "\n"
        current_files.append(filename)
    
    # 마지막 청크 추가
    if current_chunk:
        chunks.append((current_chunk, current_files))
    
    return chunks


async def prompt_analyze_diff_chunked_async(
        async_aoai_client,
        deployment_name: str,
        pr_context: Dict[str, Any],
        max_chunk_size: int = 3000,
        clean_first: bool = True
    ) -> Dict[str, Any]:
    """
    비동기 방식으로 diff를 정제, 청크화하고 각 청크별 LLM 분석을 병렬로 수행한다.
    
    Parameters:
    - async_aoai_client: Azure OpenAI 클라이언트 (동기 방식)
    - deployment_name: LLM 배포명
    - pr_context: PR 컨텍스트 (title, body, diff 포함)
    - max_chunk_size: 청크 최대 크기
    - clean_first: diff 정제 여부 (기본 True)
    
    Returns:
    - 통합 분석 결과 (전체 요약, 청크별 분석, 메타 정보)
    """
    
    title = pr_context.get("title", "")
    body = pr_context.get("body", "")
    diff = pr_context.get("diff", "")
    
    # diff 정제
    if clean_first:
        diff = _clean_diff_content(diff)
    
    # diff 청크화
    chunks = _chunk_diff(diff, max_chunk_size=max_chunk_size)
    
    if not chunks:
        return {
            "title": title,
            "status": "no_content",
            "message": "정제 후 분석할 코드 diff가 없습니다",
            "chunks_processed": 0
        }
    
    # 각 청크별 분석 태스크 생성
    tasks = [
        _analyze_chunk_async(async_aoai_client, deployment_name, title, body, idx, chunk_content, filenames, len(chunks))
        for idx, (chunk_content, filenames) in enumerate(chunks)
    ]
    
    # 모든 청크 분석을 병렬로 실행
    chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 예외 처리: Exception 객체가 반환된 경우 에러로 변환
    processed_results = []
    for idx, result in enumerate(chunk_results):
        if isinstance(result, Exception):
            processed_results.append({
                "chunk_number": idx + 1,
                "error": str(result),
                "files_in_chunk": []
            })
        else:
            processed_results.append(result)
    
    integrated_result = _integrate_chunk_results(processed_results, title)
    
    return integrated_result


async def _analyze_chunk_async(
        aoai_client,
        deployment_name: str,
        title: str,
        body: str,
        idx: int,
        chunk_content: str,
        filenames: List[str],
        total_chunks: int
    ) -> Dict[str, Any]:
    """
    단일 청크를 비동기로 분석한다.
    
    Parameters:
    - aoai_client: Azure OpenAI 클라이언트
    - deployment_name: LLM 배포명
    - title: PR 제목
    - body: PR 설명
    - idx: 청크 인덱스
    - chunk_content: 청크 내용
    - filenames: 청크에 포함된 파일명 리스트
    - total_chunks: 전체 청크 수
    
    Returns:
    - 청크 분석 결과
    """
    
    chunk_prompt = f"""
당신은 코드 리뷰 전문가입니다. PR의 일부 diff를 분석하고 있습니다.

이 분석 청크는 총 {total_chunks}개 중 #{idx + 1}번째입니다.

[분석 대상 파일들]
{', '.join(filenames)}

다음 항목들을 분석하세요:
1. 파일별 변경 요약 (각 파일 1-2문장)
2. 추가된 함수/클래스명 및 역할
3. 수정된 함수/클래스명 및 변경 내용
4. 보안 관련 변경사항 (있으면)
5. API 호출 변화 (있으면)
6. 라이브러리 의존성 추가/제거 (requirements.txt 변경 시)
7. 위험도 평가 (LOW / MEDIUM / HIGH / CRITICAL)
8. 주요 관찰사항

Return ONLY JSON:
{{
  "chunk_number": {idx + 1},
  "total_chunks": {total_chunks},
  "files_in_chunk": {filenames},
  "file_summaries": [
    {{
      "filename": "파일명",
      "status": "added|modified|deleted",
      "summary": "변경 요약"
    }}
  ],
  "added_functions": [
    {{
      "name": "함수명",
      "file": "파일명",
      "description": "역할"
    }}
  ],
  "modified_functions": [
    {{
      "name": "함수명",
      "file": "파일명",
      "change": "변경 내용"
    }}
  ],
  "security_changes": ["보안 관련 변경사항"],
  "api_changes": ["API 변화"],
  "dependency_changes": {{
    "added": ["새로운 라이브러리"],
    "removed": ["제거된 라이브러리"]
  }},
  "risk_level": "MEDIUM",
  "key_observations": ["주요 관찰사항"]
}}

[PR TITLE]
{title}

[PR DESCRIPTION]
{body}

[CODE DIFF CHUNK]
{chunk_content}
"""
    try:
        response = await aoai_client.chat.completions.create(
            model=deployment_name,
            messages=[{"role": "user", "content": chunk_prompt}],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        chunk_result = json.loads(response.choices[0].message.content)
        return chunk_result
    except Exception as e:
        return {
            "chunk_number": idx + 1,
            "error": str(e),
            "files_in_chunk": filenames
        }


def _integrate_chunk_results(chunk_results: List[Dict[str, Any]], pr_title: str) -> Dict[str, Any]:
    """
    여러 청크의 분석 결과를 통합한다.
    
    Parameters:
    - chunk_results: 각 청크별 LLM 분석 결과
    - pr_title: PR 제목
    
    Returns:
    - 통합된 최종 분석 결과
    """
    
    all_files = []
    all_added_functions = []
    all_modified_functions = []
    all_security_changes = []
    all_api_changes = []
    all_dependencies_added = []
    all_dependencies_removed = []
    max_risk_level = "LOW"
    all_observations = []
    
    # 위험도 순서
    risk_order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    
    for chunk in chunk_results:
        if "error" in chunk:
            continue
        
        # 파일 요약 병합
        for file_summary in chunk.get("file_summaries", []):
            all_files.append(file_summary)
        
        # 추가된 함수 병합
        for func in chunk.get("added_functions", []):
            all_added_functions.append(func)
        
        # 수정된 함수 병합
        for func in chunk.get("modified_functions", []):
            all_modified_functions.append(func)
        
        # 보안 변경사항 병합
        all_security_changes.extend(chunk.get("security_changes", []))
        
        # API 변화 병합
        all_api_changes.extend(chunk.get("api_changes", []))
        
        # 의존성 변경 병합
        dependencies = chunk.get("dependency_changes", {})
        all_dependencies_added.extend(dependencies.get("added", []))
        all_dependencies_removed.extend(dependencies.get("removed", []))
        
        # 위험도 업데이트 (최고 수준 유지)
        chunk_risk = chunk.get("risk_level", "LOW")
        if risk_order.get(chunk_risk, 0) > risk_order.get(max_risk_level, 0):
            max_risk_level = chunk_risk
        
        # 관찰사항 병합
        all_observations.extend(chunk.get("key_observations", []))
    
    # 중복 제거
    all_security_changes = list(set(all_security_changes))
    all_api_changes = list(set(all_api_changes))
    all_dependencies_added = list(set(all_dependencies_added))
    all_dependencies_removed = list(set(all_dependencies_removed))
    all_observations = list(set(all_observations))
    
    # 최종 결과 조합
    final_result = {
        "title": pr_title,
        "analysis_type": "chunked_diff_analysis",
        "chunks_processed": len([c for c in chunk_results if "error" not in c]),
        "total_chunks": len(chunk_results),
        
        "file_summaries": all_files,
        
        "added_functions": all_added_functions,
        
        "modified_functions": all_modified_functions,
        
        "security_changes": all_security_changes if all_security_changes else [],
        
        "api_changes": all_api_changes if all_api_changes else [],
        
        "dependency_changes": {
            "added": list(set(all_dependencies_added)),
            "removed": list(set(all_dependencies_removed))
        },
        
        "overall_risk_level": max_risk_level,
        
        "key_observations": all_observations,
        
        "chunk_details": chunk_results  # 상세 부록
    }
    
    return final_result


# =============================================================================
# 결과 포맷팅 함수들 (JSON → 텍스트/마크다운)
# =============================================================================

def format_analysis_to_compact_text(analysis_result: Dict[str, Any]) -> str:
    """
    분석 결과를 콤팩트한 텍스트로 변환 (토큰 최소화)
    
    특징:
    - 불필요한 필드 제거
    - 줄 바꿈 최소화
    - 구조화된 마크다운 사용
    - 다른 LLM이 쉽게 파싱 가능
    
    Returns:
    - 콤팩트한 텍스트 문자열
    """
    
    lines = []
    
    # 제목 및 기본 정보
    title = analysis_result.get("title", "")
    if title:
        lines.append(f"PR: {title}")
    
    risk = analysis_result.get("overall_risk_level", "UNKNOWN")
    lines.append(f"Risk: {risk}")
    
    chunks = analysis_result.get("chunks_processed", 0)
    if chunks > 0:
        lines.append(f"Chunks: {chunks}")
    
    lines.append("")  # 빈 줄
    
    # 파일 변경 요약
    files = analysis_result.get("file_summaries", [])
    if files:
        lines.append("FILES:")
        for f in files:
            filename = f.get("filename", "")
            status = f.get("status", "").upper()
            summary = f.get("summary", "")
            # 한 줄로 압축
            lines.append(f"  [{status}] {filename}: {summary[:60]}...")
        lines.append("")
    
    # 추가된 함수
    added_funcs = analysis_result.get("added_functions", [])
    if added_funcs:
        lines.append("ADDED FUNCTIONS:")
        for func in added_funcs[:5]:  # 최대 5개만
            name = func.get("name", "")
            file = func.get("file", "")
            lines.append(f"  + {name} ({file})")
        if len(added_funcs) > 5:
            lines.append(f"  + ... and {len(added_funcs) - 5} more")
        lines.append("")
    
    # 수정된 함수
    modified_funcs = analysis_result.get("modified_functions", [])
    if modified_funcs:
        lines.append("MODIFIED FUNCTIONS:")
        for func in modified_funcs[:5]:  # 최대 5개만
            name = func.get("name", "")
            file = func.get("file", "")
            change = func.get("change", "")
            lines.append(f"  ~ {name} ({file}): {change[:40]}...")
        if len(modified_funcs) > 5:
            lines.append(f"  ~ ... and {len(modified_funcs) - 5} more")
        lines.append("")
    
    # 보안 변경사항
    security = analysis_result.get("security_changes", [])
    if security:
        lines.append("SECURITY CHANGES:")
        for s in security[:3]:  # 최대 3개만
            lines.append(f"  ⚠ {s}")
        if len(security) > 3:
            lines.append(f"  ⚠ ... and {len(security) - 3} more")
        lines.append("")
    
    # API 변화
    api_changes = analysis_result.get("api_changes", [])
    if api_changes:
        lines.append("API CHANGES:")
        for api in api_changes[:3]:  # 최대 3개만
            lines.append(f"  {api}")
        if len(api_changes) > 3:
            lines.append(f"  ... and {len(api_changes) - 3} more")
        lines.append("")
    
    # 의존성 변경
    deps = analysis_result.get("dependency_changes", {})
    added_deps = deps.get("added", [])
    removed_deps = deps.get("removed", [])
    
    if added_deps or removed_deps:
        lines.append("DEPENDENCIES:")
        if added_deps:
            lines.append(f"  + {', '.join(added_deps[:5])}")
            if len(added_deps) > 5:
                lines.append(f"    ... +{len(added_deps) - 5} more")
        if removed_deps:
            lines.append(f"  - {', '.join(removed_deps[:5])}")
            if len(removed_deps) > 5:
                lines.append(f"    ... -{len(removed_deps) - 5} more")
        lines.append("")
    
    # 주요 관찰사항
    observations = analysis_result.get("key_observations", [])
    if observations:
        lines.append("KEY OBSERVATIONS:")
        for obs in observations[:3]:  # 최대 3개만
            lines.append(f"  • {obs}")
        if len(observations) > 3:
            lines.append(f"  • ... {len(observations) - 3} more items")
    
    return "\n".join(lines)


def format_analysis_to_markdown(analysis_result: Dict[str, Any]) -> str:
    """
    분석 결과를 마크다운 형식으로 변환
    
    특징:
    - 가독성 우수
    - 마크다운 헤더 사용
    - 테이블 형식 지원
    - 이모지 활용
    
    Returns:
    - 마크다운 형식의 텍스트 문자열
    """
    
    lines = []
    
    # 제목
    title = analysis_result.get("title", "")
    lines.append(f"# PR Analysis: {title}\n")
    
    # 기본 정보
    risk = analysis_result.get("overall_risk_level", "UNKNOWN")
    risk_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(risk, "⚪")
    chunks = analysis_result.get("chunks_processed", 0)
    
    lines.append(f"## Summary")
    lines.append(f"- **Risk Level**: {risk_emoji} `{risk}`")
    lines.append(f"- **Chunks Processed**: {chunks}")
    lines.append("")
    
    # 파일 변경 요약
    files = analysis_result.get("file_summaries", [])
    if files:
        lines.append("## Changed Files")
        lines.append("| File | Status | Summary |")
        lines.append("|------|--------|---------|")
        for f in files:
            filename = f.get("filename", "")
            status = f.get("status", "").upper()
            summary = f.get("summary", "")[:50]
            lines.append(f"| `{filename}` | {status} | {summary}... |")
        lines.append("")
    
    # 함수 변경
    added_funcs = analysis_result.get("added_functions", [])
    modified_funcs = analysis_result.get("modified_functions", [])
    
    if added_funcs:
        lines.append("## Added Functions ✨")
        for func in added_funcs[:10]:
            name = func.get("name", "")
            file = func.get("file", "")
            desc = func.get("description", "")
            lines.append(f"- **{name}** ({file})")
            if desc:
                lines.append(f"  - {desc}")
        if len(added_funcs) > 10:
            lines.append(f"- ... and {len(added_funcs) - 10} more")
        lines.append("")
    
    if modified_funcs:
        lines.append("## Modified Functions 🔧")
        for func in modified_funcs[:10]:
            name = func.get("name", "")
            file = func.get("file", "")
            change = func.get("change", "")
            lines.append(f"- **{name}** ({file})")
            if change:
                lines.append(f"  - {change}")
        if len(modified_funcs) > 10:
            lines.append(f"- ... and {len(modified_funcs) - 10} more")
        lines.append("")
    
    # 보안 체크
    security = analysis_result.get("security_changes", [])
    if security:
        lines.append("## Security Changes ⚠️")
        for s in security:
            lines.append(f"- {s}")
        lines.append("")
    
    # API 변화
    api_changes = analysis_result.get("api_changes", [])
    if api_changes:
        lines.append("## API Changes 🔌")
        for api in api_changes:
            lines.append(f"- {api}")
        lines.append("")
    
    # 의존성
    deps = analysis_result.get("dependency_changes", {})
    added_deps = deps.get("added", [])
    removed_deps = deps.get("removed", [])
    
    if added_deps or removed_deps:
        lines.append("## Dependencies 📦")
        if added_deps:
            lines.append(f"**Added**: `{', '.join(added_deps)}`")
        if removed_deps:
            lines.append(f"**Removed**: `{', '.join(removed_deps)}`")
        lines.append("")
    
    # 관찰사항
    observations = analysis_result.get("key_observations", [])
    if observations:
        lines.append("## Key Observations 📋")
        for obs in observations:
            lines.append(f"- {obs}")
        lines.append("")
    
    return "\n".join(lines)


def format_analysis_to_structured_text(analysis_result: Dict[str, Any], include_chunk_details: bool = False) -> str:
    """
    분석 결과를 구조화된 텍스트로 변환
    
    다른 LLM이 쉽게 파싱할 수 있는 구조화된 형식:
    - 섹션 구분자 명확
    - 각 항목에 인덱스 번호
    - 일관된 포맷
    
    Parameters:
    - analysis_result: 분석 결과 JSON
    - include_chunk_details: 청크 상세 정보 포함 여부
    
    Returns:
    - 구조화된 텍스트 문자열
    """
    
    lines = []
    
    # 헤더
    title = analysis_result.get("title", "")
    lines.append("=" * 80)
    lines.append(f"DIFF ANALYSIS REPORT: {title}")
    lines.append("=" * 80)
    lines.append("")
    
    # 메타정보
    lines.append("METADATA")
    lines.append("-" * 40)
    lines.append(f"Risk Level: {analysis_result.get('overall_risk_level', 'UNKNOWN')}")
    lines.append(f"Analysis Type: {analysis_result.get('analysis_type', 'unknown')}")
    lines.append(f"Chunks Processed: {analysis_result.get('chunks_processed', 0)}/{analysis_result.get('total_chunks', 0)}")
    lines.append("")
    
    # 파일 변경 상세
    files = analysis_result.get("file_summaries", [])
    if files:
        lines.append("FILES CHANGED")
        lines.append("-" * 40)
        for idx, f in enumerate(files, 1):
            lines.append(f"[{idx}] {f.get('status', 'unknown').upper()}: {f.get('filename', '')}")
            lines.append(f"    Summary: {f.get('summary', '')}")
        lines.append("")
    
    # 함수 추가
    added_funcs = analysis_result.get("added_functions", [])
    if added_funcs:
        lines.append("FUNCTIONS ADDED")
        lines.append("-" * 40)
        for idx, func in enumerate(added_funcs, 1):
            lines.append(f"[{idx}] {func.get('name', '')} in {func.get('file', '')}")
            lines.append(f"    Description: {func.get('description', '')}")
        lines.append("")
    
    # 함수 수정
    modified_funcs = analysis_result.get("modified_functions", [])
    if modified_funcs:
        lines.append("FUNCTIONS MODIFIED")
        lines.append("-" * 40)
        for idx, func in enumerate(modified_funcs, 1):
            lines.append(f"[{idx}] {func.get('name', '')} in {func.get('file', '')}")
            lines.append(f"    Change: {func.get('change', '')}")
        lines.append("")
    
    # 보안 항목
    security = analysis_result.get("security_changes", [])
    if security:
        lines.append("SECURITY CONSIDERATIONS")
        lines.append("-" * 40)
        for idx, item in enumerate(security, 1):
            lines.append(f"[{idx}] {item}")
        lines.append("")
    
    # API 변화
    api_changes = analysis_result.get("api_changes", [])
    if api_changes:
        lines.append("API CHANGES")
        lines.append("-" * 40)
        for idx, api in enumerate(api_changes, 1):
            lines.append(f"[{idx}] {api}")
        lines.append("")
    
    # 의존성 변경
    deps = analysis_result.get("dependency_changes", {})
    if deps.get("added") or deps.get("removed"):
        lines.append("DEPENDENCIES")
        lines.append("-" * 40)
        if deps.get("added"):
            lines.append("ADDED:")
            for idx, dep in enumerate(deps["added"], 1):
                lines.append(f"  [{idx}] {dep}")
        if deps.get("removed"):
            lines.append("REMOVED:")
            for idx, dep in enumerate(deps["removed"], 1):
                lines.append(f"  [{idx}] {dep}")
        lines.append("")
    
    # 관찰사항
    observations = analysis_result.get("key_observations", [])
    if observations:
        lines.append("KEY OBSERVATIONS")
        lines.append("-" * 40)
        for idx, obs in enumerate(observations, 1):
            lines.append(f"[{idx}] {obs}")
        lines.append("")
    
    # 청크 상세정보 (선택)
    if include_chunk_details:
        chunk_details = analysis_result.get("chunk_details", [])
        if chunk_details:
            lines.append("CHUNK DETAILS")
            lines.append("-" * 40)
            for chunk_idx, chunk in enumerate(chunk_details, 1):
                if "error" in chunk:
                    lines.append(f"Chunk {chunk_idx}: ERROR - {chunk['error']}")
                else:
                    files_in_chunk = chunk.get("files_in_chunk", [])
                    risk = chunk.get("risk_level", "UNKNOWN")
                    lines.append(f"Chunk {chunk_idx}: {len(files_in_chunk)} files, Risk={risk}")
                    lines.append(f"  Files: {', '.join(files_in_chunk)}")
            lines.append("")
    
    lines.append("=" * 80)
    
    return "\n".join(lines)


def convert_json_to_text_prompt(analysis_result: Dict[str, Any], format_type: str = "compact") -> str:
    """
    분석 결과를 다른 LLM에 전달하기 위한 텍스트 프롬프트로 변환
    
    Parameters:
    - analysis_result: 분석 결과 JSON
    - format_type: "compact", "markdown", "structured" 중 선택
    
    Returns:
    - 텍스트 형식의 프롬프트 문자열
    """
    
    if format_type == "markdown":
        return format_analysis_to_markdown(analysis_result)
    elif format_type == "structured":
        return format_analysis_to_structured_text(analysis_result)
    else:  # compact (기본)
        return format_analysis_to_compact_text(analysis_result)


def get_token_usage_estimate(analysis_result: Dict[str, Any]) -> Dict[str, int]:
    """
    JSON vs 텍스트 포맷별 토큰 사용량 추정
    
    대략적인 추정치:
    - JSON: 비효율적, 대괄호/쉼표 포함
    - 텍스트: 효율적
    
    Returns:
    - {"json": 토큰수, "text": 토큰수, "savings": 절약율}
    """
    
    json_str = json.dumps(analysis_result, ensure_ascii=False)
    text_str = format_analysis_to_compact_text(analysis_result)
    
    # 대략적 토큰 추정: 1 token ≈ 4자
    json_tokens = len(json_str) // 4
    text_tokens = len(text_str) // 4
    
    savings_percent = ((json_tokens - text_tokens) / json_tokens * 100) if json_tokens > 0 else 0
    
    return {
        "json_tokens": json_tokens,
        "text_tokens": text_tokens,
        "savings_percent": round(savings_percent, 1),
        "json_length_bytes": len(json_str.encode('utf-8')),
        "text_length_bytes": len(text_str.encode('utf-8'))
    }

