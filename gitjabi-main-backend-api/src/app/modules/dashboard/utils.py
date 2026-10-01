def format_audit_logs(logs):
    action_map = {
        "change_requests_master_INSERT": "CR 최초 등록",
        "change_requests_master_UPDATE": "CR 정보 수정",
        "change_requests_master_DELETE": "CR 삭제",
        "cr_decisions_INSERT": "결재 라인 할당",
        "cr_decisions_UPDATE": "의사결정 변경(승인/반려)",
        "cr_decisions_DELETE": "결재 취소",
        "cr_scan_results_INSERT": "기술 스캔 완료",
        "cr_risk_factors_INSERT": "리스크 분석 완료"
    }

    formatted_logs = []
    for log in logs:
        raw_action = log.get('action', '')
        
        human_action = action_map.get(raw_action, raw_action)

        formatted_logs.append({
            **log,
            "action": human_action
        })
    
    return formatted_logs