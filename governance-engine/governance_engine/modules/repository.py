from typing import List, Optional, TYPE_CHECKING
from psycopg2.extras import RealDictCursor
if TYPE_CHECKING:
    # from psycopg2.pool import AbstractConnectionPool
    from psycopg2.extensions import connection

class PolicyRepository:
    """정책 접근 레포지터리"""
    def __init__(self, db_connection: "connection"):
        self.conn = db_connection

    def vector_search(self, user_query: str):
        """벡터 검색"""
        sql = """
WITH search_param AS (
    SELECT public.get_search_embedding(%s) AS v
)
SELECT 
    c.id, c.policy_id, 
    c.type, c.domain, 
    c.risk_level, c.authority_group, 
    c.title, c.content, 
    c.tag, c.status, 
    to_char(c.created_at, 'YYYY-MM-DD"T"HH24:MI:SS') AS created_at, 
    c.node_id,
    1 - (embedding <=> (SELECT v FROM search_param)) AS similarity
FROM public.compliance_policies c
WHERE embedding IS NOT NULL
ORDER BY embedding <=> (SELECT v FROM search_param)
LIMIT 5;
"""
        with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(sql, (user_query,))
            results = cursor.fetchall()
        return results

    def get_policies_by_tags(self, tags: List[str]):
        """태그로 정책을 검색."""
        cleaned_tags = [t.strip() for t in (tags or []) if t and t.strip()]
        
        if not cleaned_tags:
            return [] 

        query = """
            SELECT id, name, tags 
            FROM compliance_policies 
            WHERE tags && %s::text[];
        """

        # 3. 쿼리 실행
        with self.conn.cursor() as cursor:
            cursor.execute(query, (cleaned_tags,))
            results = cursor.fetchall()
            
        return results

    def get_all_unique_tags(self) -> set:
        """
        DB의 모든 정책에서 중복 없는 태그 집합을 가져옵니다.
        """
        query = """
            SELECT DISTINCT unnest(tags) 
            FROM public.compliance_policies 
            WHERE tags IS NOT NULL;
        """
        
        unique_tags = set()
        
        with self.conn.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            unique_tags = {row[0] for row in rows}
                
        return unique_tags

