from pydantic import BaseModel


# 3. API 엔드포인트: RAG 검색 (중간 검색창용)
class SearchReq(BaseModel):
    query: str
    test_group_id: int | None = 1  # 테스트용 기본값
    test_role: str | None = "user"

