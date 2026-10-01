import logging
import asyncio
import httpx
from datetime import datetime
from app.modules.github_app.check_run import (
    GithubCheckRunDispatcher,
    GithubCheckRunConclusionEnum
)
from app.modules.repo.check_compliance_result_repo import insert_governance_scan_result
from app.modules.analyzer.report import build_scan_report_text
from app.modules.analyzer.scan_status_determine import get_final_scan_summary_advanced
from app.settings import api_settings

MAX_TIMEOUT = 120
GOVERNANCE_CHECK_SCAN_ENDPOINT = f'{api_settings.GOVERNANCE_ENGINE_API_ENDPOINT.rstrip('/')}/api/engine/check-run'


async def _get_code_diff(
        token, event_data
    ):
    pr_number = event_data.get('number')
    repository_full_name = event_data.get('repository').get('full_name')
    # diff_url = event_data.get('pull_request').get('diff_url')
    headers = {
        "Authorization": f"Bearer {token}", 
        "Accept": "application/vnd.github.v3.diff"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repository_full_name}/pulls/{pr_number}",
                headers=headers
            )
            response.raise_for_status()
            data = response.text
            return data
    except Exception as e:
        return ""
    
async def _call_engine_api(event_data, code_diff_content, event_id):
    try:
        async with httpx.AsyncClient() as client:
            logging.info(f"[{event_id}] 거버넌스 분석 시작...")
            response = await client.post(
                GOVERNANCE_CHECK_SCAN_ENDPOINT,
                json={
                    "pr_event": event_data,
                    "code_diff": code_diff_content
                },
                params={'event_id': event_id},
                timeout=MAX_TIMEOUT
            )
            scan_result = response.json()
            logging.info(f"[{event_id}] 거버넌스 분석 완료.")
            return scan_result  
    except Exception as e:
        logging.error(e)
        return None

async def analyze_code_with_governance(
        pool,
        dispatcher: GithubCheckRunDispatcher, 
        check_run_id: int, 
        event_data
):
    is_successful = False
    scan_report_text = None
    logging.info(f"[{check_run_id}] 분석 시작: {str(event_data)[:50]}...")
    
    # DIFF CODE 가져오기
    code_diff_content = await _get_code_diff(dispatcher._token, event_data)
    logging.info(f"[CODE DIFF]: {code_diff_content[:50]}")

    # 거버넌스 엔진 API 호출
    scan_result = await _call_engine_api(
        event_data, 
        code_diff_content, 
        check_run_id
    )
    if not scan_result:
        is_successful = False
    else:
        # SQL 저장
        if scan_result:
            try:
                async with pool.acquire() as conn:
                    await insert_governance_scan_result(conn, scan_result, event_data.get('number'))
            except Exception as e:
                logging.error(e)
        
        # 스캔 요약 정보 추출
        scan_summary = get_final_scan_summary_advanced(scan_result)
        try:
            scan_report_text = build_scan_report_text(scan_result)
        except Exception as e:
            scan_report_text = 'Internal Server Error'

        logging.info(f"Scan Summary: {scan_summary}")
        is_successful = not(scan_summary['has_violation'])
    
    #-------------------------
    #   Github 으로 결과 전송
    #-------------------------
    if is_successful:
        await dispatcher.end_of_check_run(
            check_run_id,
            conclusion=GithubCheckRunConclusionEnum.SUCCESS,
            title="컴플라이언스 준수 확인 결과",
            summary="정상적인 PR로 판단되었습니다. 세부 내용은 시스템 로그를 참고하세요.",
            text=scan_report_text or 'Internal Server Error (Scan Failure)'
        )
    else:
        await dispatcher.end_of_check_run(
            check_run_id,
            conclusion=GithubCheckRunConclusionEnum.FAILURE,
            title="컴플라이언스 준수 확인 결과 - 검토 필요",
            summary="PR에 대한 비정상적인 내용이 존재함을 판단했습니다. 세부 내용은 시스템 로그를 참고하세요.",
            text=scan_report_text or 'Internal Server Error (Scan Failure)'
        )
