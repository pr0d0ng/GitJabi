import logging
from fastapi import APIRouter, Depends
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions
from langchain_core.prompts import ChatPromptTemplate

from app.modules.openai.azure_ai import get_azure_open_ai_instance
from app.models.knowledge import SearchReq
from app.modules.oauth.authentication import get_current_user, UserSession
from app.modules.database.psql import aget_db_pool

from app.settings import api_settings

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Cloud"])


# 2. API 엔드포인트: 통계 정보 (상단 KPI 카드용)
@router.get("/stats")
async def get_stats(
        pool = Depends(aget_db_pool)
):
    async with pool.acquire() as conn:
        try:
            # 실제 DB에서 ACTIVE와 PROPOSED 상태인 정책 수를 가져옵니다.
            fetched = await conn.fetch("SELECT status, count(*) FROM compliance_policies GROUP BY status")
            counts = dict(fetched)
            
            total_nodes = sum(counts.values())
            active_count = counts.get('ACTIVE', 0)
            active_ratio = (active_count / total_nodes * 100) if total_nodes > 0 else 0
            
            return {
                "total_nodes": str(total_nodes),
                "graph_density": "0.89",
                "ai_accuracy": f"{active_ratio:.1f}%"
            }
        except Exception as e:
            logging.error(f"Stats 에러: {e}")
            return {"total_nodes": "0", "graph_density": "0", "ai_accuracy": "0%"}


@router.post("/search")
async def search_rag(
        req: SearchReq,
        openai=Depends(get_azure_open_ai_instance),
        user: UserSession=Depends(get_current_user),

): # Depends(get_current_user) # 전체 백엔드 코드와 통합 시 추가
    if not check_prompt_safety(req.query):
        return {
            "answer": "⚠️ 보안 가이드라인에 따라 유해하거나 부적절한 질문(폭력, 혐오 등)에는 답변을 제공할 수 없습니다.",
            "related_ids": []
        }
    try:
        user_group = user.claims.get("group_id")
        user_role = user.role

        # RBAC
        # 관리자(admin)는 필터 없이 모든 문서 조회, 일반 사용자는 자신의 그룹과 공용 그룹(1)만 조회
        if user_role == "admin":
            search_filter = None
        else:
            search_filter = f"authority_group eq 1 or authority_group eq {user_group}"

        search_client = SearchClient(
            api_settings.AI_SEARCH_ENDPOINT, 
            api_settings.AI_INDEX_NAME, 
            AzureKeyCredential(
                api_settings.AI_SEARCH_KEY
            )
        )
        results = search_client.search(search_text=req.query, top=3, filter=search_filter)

        related_ids = []
        context = ""
        for doc in results:
            p_human_id = doc.get('policy_id', 'Unknown-ID')
            p_system_id = doc.get('node_id', 'Unknown-Node')

            source = doc.get('source_annotation', '알 수 없는 출처')
            title = doc.get('title', '제목 없음')
            content = doc.get('content', '')

            context += f"[{p_human_id} / 시스템ID: {p_system_id}] {title}\n내용: {content}\n\n"
            related_ids.append(p_system_id)
        
        if not context:
            return {"answer": "죄송합니다. 관련 정책을 지식 베이스에서 찾을 수 없습니다."}

        prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 IT 보안 및 컴플라이언스 전문가입니다. 
            반드시 제공된 [맥락]의 내용만을 근거로 답변하세요. 
            시스템 ID(KC-DOC-xxx)는 답변 텍스트에 노출하지 마세요.
            답변은 반드시 다음 형식을 지키세요:
            
            1. 관련 정책 Top 3: 정책의 [P-SEC-xxx] 형태의 ID와 제목을 적으세요.
            2. 상세 안내: (질문에 대한 구체적인 설명) ### 상세 안내 라는 헤더를 사용하여 구분하세요.
            3. 권장 조치: (사용자가 취해야 할 행동 요령)
            4. 중요 키워드나 정책 ID는 **별표 두 개**로 감싸서 강조하세요. (초록색 볼드가 됩니다)
            5. 권장 조치는 반드시 * 기호를 사용한 글머리 기호 목록으로 작성하세요.
            6. 섹션 제목(관련 정책, 상세 안내 등) 앞에 '1.', '2.'와 같은 숫자를 절대 붙이지 마세요. 또한 답변 중 불필요한 제어 문자나 특수 공백을 사용하지 마세요.
            7. 답변 시 SQL 명령어, 변수명($, #), 파일명, 또는 강조하고 싶은 기술 용어는 반드시 `백틱(`)`으로 감싸서 표현하세요. 문장 끝에는 불필요한 특수 기호나 제어 문자를 포함하지 마세요."""),
            ("user", f"[맥락]\n{context}\n\n[질문]\n{req.query}")
        ])
        
        chain = prompt | openai
        try:
            ai_msg = chain.invoke({}) 
            return {"answer": ai_msg.content, "related_ids": related_ids}
        except Exception as e:
            # Azure OpenAI 자체 필터(content_filter)에 걸렸을 때의 처리
            error_str = str(e)
            if "content_filter" in error_str or "ResponsibleAIPolicyViolation" in error_str:
                 return {
                    "answer": "⚠️ 보안 정책에 따라 답변을 제공할 수 없습니다. 질문에 부적절하거나 위험한 내용(탈옥 시도 등)이 포함되어 있는지 확인해 주세요.",
                    "related_ids": []
                }
            raise e
        
    except Exception as e:
        logging.error(f"RAG 검색 실패: {e}")
        return {"answer": f"서버 내부 오류가 발생했습니다: {str(e)}", "related_ids": []}


# 4. API 엔드포인트: 최근 업데이트된 정책 목록 (최근 업데이트 카드용)
@router.get("/recent-updates")
async def get_recent_updates(
        pool = Depends(aget_db_pool)
):
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch("""
                SELECT policy_id, title, created_at, status 
                FROM compliance_policies 
                ORDER BY created_at DESC LIMIT 5
            """)
            
            result = []
            for row in rows:
                p_id = row[0]
                s_type = "DOCUMENT" if "DOC" in p_id.upper() else "TEAMS_MEETING"
                
                result.append({
                    "source_type": s_type,
                    "policy_id": p_id,
                    "title": row[1], 
                    "created_at": row[2].isoformat() if row[2] else None,
                    "status": row[3]
                })
            return result
        except Exception as e:
            logging.error(f"Recent Updates 조회 실패: {e}")
            return []


# 5. API 엔드포인트: 지식 그래프 데이터 (지식 그래프 시각화용)
@router.get("/graph")
async def get_graph_data(
        pool = Depends(aget_db_pool)
):
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch(
                "SELECT policy_id, node_id, title, tag, content FROM compliance_policies"
            )
            
            nodes = []
            
            # 1. 노드 생성
            for row in rows:
                nodes.append({"id": row[1], "policy_id": row[0], "title": row[2], "tags": row[3] if row[3] else [], "content": row[4]})
                
            # 2. 링크 생성 (동일 태그 공유 시 연결)
            links = []

            for i in range(len(nodes)):
                link_count = 0
                for j in range(i + 1, len(nodes)):
                    if link_count > 2:  # 각 노드당 최대 3개의 링크만 생성
                        break
                    # 두 노드가 공통 태그를 하나라도 가지고 있다면 연결
                    common_tags = set(nodes[i]["tags"]) & set(nodes[j]["tags"])
                    if len(common_tags) >= 2:
                        links.append({
                            "source": nodes[i]["id"],
                            "target": nodes[j]["id"],
                            "label": list(common_tags)[0]
                        })
                        link_count += 1
                        
            return {"nodes": nodes, "links": links}
        except Exception as e:
            logging.error(f"Graph 에러: {e}")
            return {"nodes": [], "links": []}


# 6. 유해한 프롬프트 검사 (AI 답변 생성 전에 호출)
def check_prompt_safety(
        query: str
    ):
    """유저의 질문에 유해한 내용이나 탈옥(Jailbreak) 시도가 있는지 검사합니다."""
    client = ContentSafetyClient(
        api_settings.CONTENT_SAFETY_ENDPOINT, 
        AzureKeyCredential(
            api_settings.CONTENT_SAFETY_KEY)
    )
    
    # 텍스트 분석 옵션 설정 (Hate, SelfHarm, Sexual, Violence 검사)
    request = AnalyzeTextOptions(text=query)
    
    try:
        response = client.analyze_text(request)
        
        # 각 카테고리별 위험 점수(0~7) 확인. 4점 이상이면 위험으로 간주.
        for category in response.categories_analysis:
            if category.severity and category.severity >= 4:
                logging.error(f"⚠️ 보안 위협 감지: {category.category} (점수: {category.severity})")
                return False
        
        return True
    except Exception as e:
        logging.error(f"Content Safety 호출 실패: {e}")
        return True 
    