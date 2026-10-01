from pydantic import BaseModel, Field
from typing import List, Optional

class PolicyCreate(BaseModel):
    title: str
    content: str
    type: str  # security, governance, standard
    domain: str # backend, frontend, others
    risk_level: str # LOW, MEDIUM, HIGH, CRITICAL
    tag: List[str] = []
    status: str = "PROPOSED" # 기본값 설정
    authority_group: int = 1



class ChangeRequestCreate(BaseModel):
    """변경 요청 폼"""
    title: str
    body: str
    targetEnv: str
    priority: str
    authorityGroup: int
    isHotfix: bool


class CRDecisionCreate(BaseModel):
    """CR 결정 (승인/거부) 요청"""
    approver_role: str
    approver_name: str
    status: str  # APPROVED, REJECTED, PENDING, etc.
    comment: Optional[str] = None

