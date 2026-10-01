from fastapi import FastAPI, Request, HTTPException, Depends, Body
import os, json, logging
from typing import TYPE_CHECKING, Optional
from traceback import format_exc
from dotenv import load_dotenv
from governance_engine.engine import GovernanceEngine
from governance_engine.modules.psql import get_db_pool_singleton
from models import CheckRunRequest
from governance_engine.preprocess_code_diff import CodeDiffSummarizerLLM
import uvicorn

if TYPE_CHECKING:
    from governance_engine.modules.psql import DatabasePool
    # from psycopg2.extensions import connection

load_dotenv()

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()] 
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)

@app.post("/api/engine/check-run")
async def check_run(
    request: CheckRunRequest,
    event_id: Optional[str]=None,
    db_pool: "DatabasePool"=Depends(get_db_pool_singleton)
):
    """거버넌스 검사를 수행한다. """
    minium_len_to_analyze = 100
    code_diff_raw = request.code_diff
    code_diff_summarized_text = None
    
    try:
        # ==========================================
        # 데이터 전처리: Code Diff 요약 
        # ==========================================
        if len(code_diff_raw.strip()) > minium_len_to_analyze:
            logging.info(f"[{event_id}] PR({request.pr_event.get('pull_request', {}).get('id')})의 Code Diff 내용 요약중...")
            summarizer_diff = CodeDiffSummarizerLLM()
            code_diff_summarized_structured = await summarizer_diff.async_diff_summarize(code_diff_raw)
            code_diff_summarized_text = summarizer_diff.convert_json_to_text(code_diff_summarized_structured)
    except Exception as e:
        logging.error(f"{e}")
        raise HTTPException(status_code=500, detail=f"Code Diff Parsing Error: {e}")
    
    try:
        with db_pool.get_connection() as conn:
            engine = GovernanceEngine(conn)
            try:
                result = engine.run(
                    payload=request.pr_event,
                    diff_text=code_diff_summarized_text or "",
                    event_id=event_id
                )
                return result
            except Exception as e:
                logging.error(f"[ERROR] {e} \n {format_exc()}")
                raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
    except Exception as e:
        logging.error(f"[DB ERROR] {e}")
        raise HTTPException(status_code=500, detail=f"Database connection failed: {e}")


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=3000)


###############################################

# =========================
# Webhook Endpoint
# =========================
# @app.post("/webhook")
# async def webhook(request: Request):

#     payload = await request.json()

#     pr = payload.get("pull_request")
#     if not pr:
#         raise HTTPException(status_code=400, detail="pull_request missing")

#     pr_id = pr.get("id")
#     pr_title = pr.get("title", "")
#     pr_body = pr.get("body", "")
#     pr_diff = payload.get("code_diff", "")

#     try:
#         result = engine.run(
#             pr_title=pr_title,
#             pr_body=pr_body,
#             pr_diff=pr_diff
#         )
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     # =========================
#     # 1️⃣ Rule Engine 결과 DB 저장
#     # =========================
#     rule_result = result.get("rule_engine_result")
#     if rule_result:
#         save_rule_result(pr_id, rule_result)

#     # =========================
#     # 2️⃣ LLM 기반 Compliance 결과 반환
#     # =========================
#     return {
#         "status": "processed",
#         "pr_id": pr_id,
#         "tags": result.get("tags"),
#         "violations": result.get("llm_violations"),
#         "policies_checked": result.get("policies_checked")
#     }