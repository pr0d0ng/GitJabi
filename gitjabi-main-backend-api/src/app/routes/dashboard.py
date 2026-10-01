"""
대시보드 관련 CRUD 엔드포인트
"""

import logging
from fastapi import Depends, APIRouter, HTTPException
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from asyncpg.pool import Pool
from app.modules.database.psql import aget_db_pool
from app.modules.oauth.authentication import get_current_user, UserSession
from app.models.dashboard import PolicyCreate


router = APIRouter(prefix="/api/dashboard", tags=["Policy"])

@router.get("/policy")
async def get_policies(
        pool = Depends(aget_db_pool),
        user = Depends(get_current_user)
    ):
    """정책 목록을 반환"""
    async with pool.acquire() as conn:
        # 1. 실제 데이터 조회 쿼리
        query = """
            SELECT c.*, g.id as authority_group_pk, g.group_name, g.description as group_description 
            FROM public.compliance_policies c
            left join "groups" g 
            on c.authority_group = g.id 
            ORDER BY c.created_at DESC
        """
        rows = await conn.fetch(query)
        
        # 2. 전체 개수 조회 (페이지네이션 계산용)
        count_query = "SELECT COUNT(*) FROM public.compliance_policies"
        total = await conn.fetchval(count_query)
        
        return {
            "items": [dict(row) for row in rows],
            "total": total
        }


@router.post("/policy")
async def create_policy(
    policy: PolicyCreate,
    pool: "Pool" = Depends(aget_db_pool),
    current_user: UserSession = Depends(get_current_user) 
):
    async with pool.acquire() as conn:
        # 3. DB Insert 쿼리

        query = """
            INSERT INTO public.compliance_policies (
                title, content, type, domain, 
                risk_level, tag, status, authority_group
            ) VALUES (
                $1, $2, $3, $4, 
                $5, $6, $7, $8
            ) RETURNING id
        """
        
        try:
            new_id = await conn.fetchval(
                query,
                policy.title,
                policy.content,
                policy.type,
                policy.domain,
                policy.risk_level,
                policy.tag,
                policy.status,
                policy.authority_group           # 세션의 권한 레벨 적용
            )
            return {"message": "Policy created successfully", "id": new_id}
            
        except Exception as e:
            logging.error(f"Policy creation failed: {e}")
            raise HTTPException(status_code=500, detail="정책 등록 중 오류가 발생했습니다.")



