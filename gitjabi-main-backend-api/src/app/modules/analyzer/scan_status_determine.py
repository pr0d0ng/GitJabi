
def _classify_compliance_status(compliance_item: dict) -> dict:
    """
    개별 컴플라이언스 항목의 상태를 분석하여 분류합니다.
    """
    output = compliance_item.get("output", {})
    result = output.get("judgment_result", "UNKNOWN")
    severity = output.get("severity", "LOW")
    confidence = output.get("violation_confidence", 0.0)

    if result == "VIOLATION":
        status = "CRITICAL_VIOLATION" if severity == "CRITICAL" else "VIOLATION"
        label = "🚨 위반"
    
    elif result == "ADVISORY_WARNING":
        status = "WARNING"
        label = "⚠️ 경고"
    
    elif result == "INSUFFICIENT_CONTEXT":
        status = "INSUFFICIENT"
        label = "❓ 판단보류 (정보부족)"
    
    elif result == "COMPLIANT":
        status = "COMPLIANT"
        label = "✅ 준수"
    
    else:
        status = "UNKNOWN"
        label = "⚪ 미분류"

    return {
        "policy_id": compliance_item.get("related_policy_id"),
        "status": status,
        "label": label,
        "severity": severity,
        "confidence": confidence,
        "reason": output.get("reason", "사유 없음")
    }

def get_final_scan_summary_advanced(scan_data: dict):
    """
    전체 스캔 결과에서 최종 승인 여부를 결정합니다.
    """
    items = scan_data.get("compliance_violations", [])
    results = [_classify_compliance_status(item) for item in items]
    
    # 우선순위 기반 최종 상태 결정 (위반 > 경고 > 판단보류 > 준수)
    status_priority = ["CRITICAL_VIOLATION", "VIOLATION", "WARNING", "INSUFFICIENT", "COMPLIANT"]
    current_best_idx = len(status_priority) - 1
    final_status = "COMPLIANT"

    for res in results:
        try:
            idx = status_priority.index(res["status"])
            if idx < current_best_idx:
                current_best_idx = idx
                final_status = res["status"]
        except ValueError:
            continue

    return {
        "final_status": final_status,
        "detailed_results": results,
        "has_violation": any(r["status"] in ["VIOLATION", "CRITICAL_VIOLATION"] for r in results),
        "needs_manual_review": any(r["status"] == "INSUFFICIENT" for r in results)
    }
