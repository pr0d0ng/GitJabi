"""
대시보드 CR/컴플라이언스 통제 관련 CRUD 엔드포인트
"""

import logging
import json
from fastapi import Depends, APIRouter, HTTPException
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from asyncpg.pool import Pool
from app.modules.database.psql import aget_db_pool
from app.modules.oauth.authentication import get_current_user, UserSession
from app.models.dashboard import ChangeRequestCreate, CRDecisionCreate
from app.modules.dashboard.utils import format_audit_logs


router = APIRouter(prefix="/api/dashboard/change-request", tags=["Compliance"])

@router.get("/")
async def get_change_requests(
        pool = Depends(aget_db_pool),
        # user = Depends(get_current_user)
    ):
    """CR 목록을 반환"""
    async with pool.acquire() as conn:
            query = """
            SELECT jsonb_build_object(
                'id', cr.cr_id,
                'title', cr.title,
                'description', COALESCE(cr.description, ''),
                'status', cr.status,
                'currentStage', cr.current_stage,
                'IsHotfix', cr.is_hotfix,
                'requester', cr.requester_id,
                'requesterName', COALESCE(u.full_name, u.username) || ' (' || u.position || ')',
                'targetEnv', cr.target_env,
                'priority', cr.priority,
                'createdAt', TO_CHAR(cr.created_at, 'YYYY-MM-DD HH24:MI'),
                'riskScore', (
                    SELECT risk_score
                    FROM vw_cr_risk_analysis 
                    WHERE cr.cr_id = cr_id
                ),
                
                -- 1. Technical (PRs & GitJabi)
                'technical', jsonb_build_object(
                    'pullRequests', (
                        SELECT COALESCE(jsonb_agg(jsonb_build_object(
                            'id', pr.pr_id,
                            'prNum', pr.pr_number,
                            'repo', pr.repo_name,
                            'branch', pr_detail.head_ref,
                            'status', pr.status,
                            'pr_html_url', pr_detail.pr_html_url,
                            'stats', jsonb_build_object(
                                'target', pr_detail.base_ref,
                                'addition', pr_detail.pr_additions,
                                'deletion', pr_detail.pr_deletions,
                                'language', pr_detail.repo_language,
                                'loc', 'null'
                            )
                        )), '[]'::jsonb)
                        FROM public.cr_pr_mapping m
                        JOIN public.pull_requests_master pr 
                        ON m.pr_id = pr.pr_id
                        JOIN public.github_pr_events pr_detail
                        ON pr.event_root_id = pr_detail.id
                        WHERE m.cr_id = cr.cr_id
                    ),
                    'gitjabiScan', (
                            SELECT 
                                jsonb_agg(filtered_scan)
                            FROM (
                                SELECT 
                                    jsonb_build_object(
                                        'run_id', s.run_id,
                                        'pr_id', s.pr_id,
                                        'pr_number', s.pr_number,
                                        'event_id', s.event_id,
                                        'title', s.title,
                                        'executed_at', TO_CHAR(s.executed_at, 'YYYY-MM-DD HH24:MI'),
                                        -- compliance_violations 배열에서 COMPLIANT가 아닌 것만 추출
                                        'violations', (
                                            SELECT COALESCE(jsonb_agg(v), '[]'::jsonb)
                                            FROM jsonb_array_elements(s.compliance_violations) AS v
                                            WHERE v->'output'->>'judgment_result' <> 'COMPLIANT'
                                        )
                                    ) AS filtered_scan
                                FROM public.pr_scan_compliance_runs_history s
                                JOIN public.cr_pr_mapping m ON s.pr_id = m.pr_id
                                WHERE m.cr_id = cr.cr_id
                                ORDER BY s.executed_at DESC
                            ) sub
                        )
                ),
                -- 2. Rulebase Scan Result
                'rulebaseScan', (
                    SELECT jsonb_agg(rule_item)
                    FROM (
                        SELECT jsonb_build_object(
                            'run_id', s.run_id,
                            'severity', s.rulebase_violations->>'severity',
                            'pass', (s.rulebase_violations->>'pass')::boolean,
                            'violations', s.rulebase_violations->'violations',
                            'warnings', s.rulebase_violations->'warnings',
                            'executed_at', TO_CHAR(s.executed_at, 'YYYY-MM-DD HH24:MI')
                        ) AS rule_item
                        FROM public.pr_scan_compliance_runs_history s
                        JOIN public.cr_pr_mapping m ON s.pr_id = m.pr_id
                        WHERE m.cr_id = cr.cr_id
                        ORDER BY 
                            -- 위험도(Severity) 순서 정렬 (CRITICAL > HIGH > MEDIUM > LOW)
                            CASE s.rulebase_violations->>'severity'
                                WHEN 'CRITICAL' THEN 1
                                WHEN 'HIGH'     THEN 2
                                WHEN 'MEDIUM'   THEN 3
                                WHEN 'LOW'      THEN 4
                                ELSE 5
                            END ASC,
                            s.executed_at DESC
                        LIMIT 5 -- 상위 5개만 추출
                    ) sub
                ),

                -- 3. Risk Factors and Scores
                'riskFactors',
                COALESCE(
                    (
                        SELECT jsonb_agg(elem)
                        FROM vw_cr_risk_analysis rva,
                            jsonb_array_elements(rva.risk_factors) elem
                        WHERE rva.cr_id = cr.cr_id
                        AND elem IS NOT NULL
                    ),
                    '[]'::jsonb
                ),

                'riskMetric',
                COALESCE(
                    (
                        SELECT jsonb_build_object(
                            'riskScore', rva.risk_score
                        )
                        FROM vw_cr_risk_analysis rva
                        WHERE rva.cr_id = cr.cr_id
                    ),
                    jsonb_build_object('riskScore', 0)
                ),

                -- 4. Decision
                'decision', (
                    SELECT COALESCE(jsonb_agg(d.*), '[]'::jsonb)
                    FROM (
                        SELECT approver_role as role, approver_name as name, status, comment
                        FROM public.cr_decisions
                        WHERE cr_id = cr.cr_id
                    ) d
                ),

                -- 5. Audit Logs
                'auditLogs', (
                    SELECT COALESCE(jsonb_agg(l.*), '[]'::jsonb)
                    FROM (
                        SELECT TO_CHAR(action_time, 'MM-DD HH24:MI') as time, 
                            action_alias as action, 
                            actor_id as user
                        FROM public.cr_audit_logs
                        WHERE cr_id = cr.cr_id
                        ORDER BY action_time ASC
                    ) l
                )
            )
            FROM public.change_requests_master cr
            LEFT JOIN public.users u ON cr.requester_id = u.username
            ORDER BY cr.created_at DESC;
            """
            
            final_data = []
            results = await conn.fetch(query)
            for r in results:
                cr_item = json.loads(r[0]) # jsonb_build_object 결과물
                
                # auditLogs 섹션 가공
                if "auditLogs" in cr_item:
                    cr_item["auditLogs"] = format_audit_logs(cr_item["auditLogs"])
                
                final_data.append(cr_item)
            
            return final_data


@router.post("/publish")
async def publish_change_request(
    cr_form: ChangeRequestCreate,
    pool: "Pool" = Depends(aget_db_pool),
    current_user: UserSession = Depends(get_current_user) 
):
    """[POST] CR 발행"""
    async with pool.acquire() as conn:

        username = current_user.username

        query = """
            INSERT INTO public.change_requests_master (
                title, description, target_env, priority, 
                authority_group, is_hotfix ,requester_id
            ) VALUES (
                $1, $2, $3, $4, 
                $5, $6, $7
            ) RETURNING cr_id
        """
        
        try:
            async with conn.transaction():
                # 행위자 사용자 이름 명시 (DB에 전달)
                await conn.execute("SELECT set_config('app.current_user', $1, true)", str(username))

                # 메인 쿼리
                new_id = await conn.fetchval(
                    query,
                    cr_form.title,
                    cr_form.body,
                    cr_form.targetEnv,
                    cr_form.priority,
                    cr_form.authorityGroup,
                    cr_form.isHotfix,
                    username
                )
                return {"message": "CR created successfully", "cr_id": new_id}
            
        except Exception as e:
            logging.error(f"CR creation failed: {e}")
            raise HTTPException(status_code=500, detail="CR 등록 중 오류가 발생했습니다.")


@router.post("/{cr_id}/link-pr")
async def link_pr_to_cr(
    cr_id: str, 
    pr_id: int, 
    user: UserSession = Depends(get_current_user),
    pool = Depends(aget_db_pool)
):
    """PR과 CR을 연결시킨다."""
    async with pool.acquire() as conn:
        async with conn.transaction():
            # 1. 감사 로그를 위한 유저 세팅
            await conn.execute("SELECT set_config('app.current_user', $1, true)", user.username)
            
            # 2. 매핑 테이블 삽입
            await conn.execute(
                "INSERT INTO public.cr_pr_mapping (cr_id, pr_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                cr_id, pr_id
            )
            
    return {"status": "success", "message": f"PR #{pr_id} linked to {cr_id}"}

@router.get("/unlinked-prs")
async def get_unlinked_pull_requests(
    pool = Depends(aget_db_pool),
    user = Depends(get_current_user)
):
    """어떤 CR에도 연결되지 않은 Pull Request 목록만 조회"""
    async with pool.acquire() as conn:
        query = """
            SELECT 
                p.pr_id,
                p.pr_number,
                p.repo_name,
                p.status,
                p.ai_analysis_result,
                TO_CHAR(p.created_at, 'YYYY-MM-DD HH24:MI') as created_at,
                p.is_mandatory
            FROM public.pull_requests_master p
            -- cr_pr_mapping 테이블에 pr_id가 존재하지 않는 경우만 필터링
            WHERE NOT EXISTS (
                SELECT 1 
                FROM public.cr_pr_mapping m 
                WHERE m.pr_id = p.pr_id
            )
            ORDER BY p.created_at DESC
            LIMIT 50;
        """
        
        rows = await conn.fetch(query)
        return [dict(row) for row in rows]


@router.post("/{cr_id}/decision")
async def create_cr_decision(
    cr_id: str,
    decision_form: CRDecisionCreate,
    pool = Depends(aget_db_pool),
    user: UserSession = Depends(get_current_user)
):
    """[POST] CR 결정(승인/거부) 저장"""
    async with pool.acquire() as conn:
        try:
            async with conn.transaction():
                await conn.execute("SELECT set_config('app.current_user', $1, true)", user.username)

                update_decision_query = """
                    UPDATE public.cr_decisions
                    SET status = $3::decision_status,
                        comment = $4,
                        decided_at = CURRENT_TIMESTAMP
                    WHERE cr_id = $1 
                    AND approver_name = $2
                    AND status = 'PENDING'
                    RETURNING cr_id, approver_role, approver_name, status, comment
                """
                
                result = await conn.fetchrow(
                    update_decision_query,
                    cr_id,
                    decision_form.approver_name,
                    decision_form.status,
                    decision_form.comment
                )

                if not result:
                    raise HTTPException(
                        status_code=403, 
                        detail=f"'{decision_form.approver_name}'님은 이 CR의 의사결정 그룹에 배당되지 않았거나, 이미 처리가 완료되었습니다."
                    )

                # 4. 메인 마스터 테이블 상태 업데이트
                update_master_query = """
                    UPDATE public.change_requests_master
                    SET status = CASE 
                            WHEN (SELECT COUNT(*) FROM public.cr_decisions WHERE cr_id = $1 AND status != 'APPROVED') = 0 
                            THEN 'APPROVED'::change_request_status
                            ELSE 'IN_PROGRESS'::change_request_status
                        END,
                    current_stage = CASE 
                            WHEN (SELECT COUNT(*) FROM public.cr_decisions WHERE cr_id = $1 AND status != 'APPROVED') = 0 
                            THEN 9 
                            ELSE 5 
                        END,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE cr_id = $1
                """
                await conn.execute(update_master_query, cr_id)

                return {
                    "message": "CR 결정이 성공적으로 업데이트되었습니다.",
                    "data": dict(result)
                }

        except HTTPException as he:
            raise he
        except Exception as e:
            logging.error(f"CR decision update failed: {e}")
            raise HTTPException(status_code=500, detail="의사결정 처리 중 서버 오류가 발생했습니다.")
        
        