
def build_scan_report_text(scan_data: dict) -> str:
    # 1. 메타 데이터 추출
    run_id = scan_data.get("run_id", "Unknown")
    executed_at = scan_data.get("executed_at", "")
    rulebase = scan_data.get("rulebase_violations", {})
    compliance_list = scan_data.get("compliance_violations", [])
    
    total_checks = len(compliance_list)
    violations = [c for c in compliance_list if c["output"]["judgment_result"] == "VIOLATION"]
    warnings = [c for c in compliance_list if c["output"]["judgment_result"] == "ADVISORY_WARNING"]
    insufficient = [c for c in compliance_list if c["output"]["judgment_result"] == "INSUFFICIENT_CONTEXT"]
    
    lines = []
    lines.append(f"## Governance Scan Report")
    lines.append(f"> **Run ID:** `{run_id}`  ")
    lines.append(f"> **Scan Time:** {executed_at}  ")
    lines.append(f"> **Summary:** 총 {total_checks}건 검사 (위반 {len(violations)} | 경고 {len(warnings)} | 판단보류 {len(insufficient)})")
    lines.append("\n---\n")

    if rulebase.get("warnings"):
        lines.append("### Code Health (Rulebase)")
        for w in rulebase["warnings"]:
            lines.append(f"- **[{w['rule']}]** {w['message']}")
        lines.append("")

    if compliance_list:
        lines.append("### Policy Compliance Details")
        severity_map = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_compliance = sorted(compliance_list, key=lambda x: severity_map.get(x["output"]["severity"], 9))

        for item in sorted_compliance:
            output = item["output"]
            res = output["judgment_result"]
            
            icon = "❌" if res == "VIOLATION" else "⚠️" if res == "ADVISORY_WARNING" else "❓" if res == "INSUFFICIENT_CONTEXT" else "✅"
            
            lines.append(f"{icon} **{item['related_policy']}** (ID: `{item['related_policy_id']}`)")
            lines.append(f"  - **Severity:** `{output['severity']}` | **Result:** `{res}`")
            lines.append(f"  - **Reason:** {output['reason']}")
            
            if res in ["VIOLATION", "INSUFFICIENT_CONTEXT"]:
                lines.append(f"  - **Analysis:** {output['analysis']['step_1_context']}")
            
            lines.append("")

    lines.append("\n---\n")
    lines.append("*본 리포트는 **Gitjabi Governance Analysis Engine**에 의해 자동 생성되었습니다. 상세 내용은 관리 도구에서 확인하세요.*")

    return "\n".join(lines)

