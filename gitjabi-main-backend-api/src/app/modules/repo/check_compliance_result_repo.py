import json
from typing import Any
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from asyncpg.connection import Connection

import json
from datetime import datetime
from typing import Any


async def insert_governance_scan_result(conn, scan_data: dict[str, Any], pr_number=None):
    run_id = scan_data.get("run_id") 
    event_id = scan_data.get("event_id")
    executed_at_str = datetime.fromisoformat(scan_data.get("executed_at", ""))
    
    violations = scan_data.get("compliance_violations", [])
    pr_id = None
    pr_title = None
    if violations:
        pr_id = violations[0].get("related_pr_id")
        pr_title = violations[0].get("related_pr_title")

    # 3. JSONB 데이터 준비
    rulebase_json = json.dumps(scan_data.get("rulebase_violations", {}))
    compliance_json = json.dumps(violations)

    query = """
    INSERT INTO pr_scan_compliance_runs_history (
        run_id, event_id, pr_id, pr_number, 
        title, compliance_violations, rulebase_violations, executed_at
    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
    ON CONFLICT (pr_id) DO UPDATE SET
        compliance_violations = EXCLUDED.compliance_violations,
        rulebase_violations = EXCLUDED.rulebase_violations;
    """

    await conn.execute(
        query,
        run_id,       
        event_id,     
        pr_id,         
        pr_number,        
        pr_title,      
        compliance_json, 
        rulebase_json,   
        executed_at_str  
    )


