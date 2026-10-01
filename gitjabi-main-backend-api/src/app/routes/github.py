import logging
from app.modules.github_app.authenticator import (
    get_github_app_authenticator_singleton, 
    GithubAppAuthenticator
)
from app.modules.github_app.check_run import (
    GithubCheckRunDispatcher,
)
from app.modules.database.psql import aget_db_pool
from app.modules.analyzer.compliance import analyze_code_with_governance
from fastapi import FastAPI, Request, HTTPException, APIRouter, Depends, BackgroundTasks

router = APIRouter(prefix="/api/github", tags=["Github"])


GITHUB_CHECK_RUN_PR_TRIGGER = [
    "opened", 
    "synchronize", 
    "ready_for_review"
]

GITHUB_CHECK_RUN_TITLE_CORE: str = "GitJabi Analysis Engine - Checks compliances"


@router.post("/webhook")
async def github_webhook(
        request: Request, 
        background_tasks: BackgroundTasks,
        github_app_auth: GithubAppAuthenticator=Depends(get_github_app_authenticator_singleton),
        pool = Depends(aget_db_pool)
):

    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    event = request.headers.get("X-GitHub-Event")

    if not signature:
        logging.debug("Signature is not found from github:", signature)
        raise HTTPException(403, "Signature not found")

    github_app_auth.verify_signature(body, signature)

    payload = await request.json()

    if event != "pull_request":
        logging.info(f"This event is not a pull request: {event}. Ignoring it.")
    elif event == "pull_request" and \
            payload.get("pull_request") and payload['pull_request'].get("draft", False):
        logging.info("This event is a draft pull request. Ignoring it.")
    else:
        ###########################
        #     IF PULL-REQUEST
        ###########################
        action = payload.get("action")
        if action in GITHUB_CHECK_RUN_PR_TRIGGER:
            # Is opened? or ready_for_review?

            installation_id = payload["installation"]["id"]
            repo_full_name = payload["repository"]["full_name"]
            repo_name = payload["repository"]["name"]
            repo_owner = payload["repository"]["owner"]["login"]
            pr = payload["pull_request"]
            sha = pr["head"]["sha"]
            
            logging.info("This event is a pull request (open)")

            token = await github_app_auth.async_get_access_token(installation_id)
            if not token:
                logging.error(f"[Internal Error] An invalid access token: {str(token)[:10]}...")
                raise HTTPException(500, "Internal Error : Cannot load access token")
            #------------------------
            #  Github Check Run 생성 
            #       (아웃바운드)
            #------------------------
            dispatcher = GithubCheckRunDispatcher(
                token,
                repo_owner,
                repo_name,
                sha
            )
            check_run_id = await dispatcher.start_check_run(
                GITHUB_CHECK_RUN_TITLE_CORE
            )
            #-------------------------
            #      엔진 분석 시작
            #-------------------------
            background_tasks.add_task(
                analyze_code_with_governance, pool, dispatcher, check_run_id, payload
            )

            return {"message": "Check run created, analysis started."}
  
    return {"message": "Event ignored"}




