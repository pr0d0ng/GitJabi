import logging
from fastapi import FastAPI, Request, HTTPException, APIRouter, Depends, BackgroundTasks
from app.modules.github_app.authenticator import (
    get_github_app_authenticator_singleton, 
    GithubAppAuthenticator
)
from app.modules.oauth.authentication import get_current_user, UserSession
from app.modules.github_restapi.organization import GithubOrgDataDispatcher


router = APIRouter(prefix="/api/github-organization", tags=["Github Organization"])

@router.get("/repos/{org_name}")
async def get_dashboard_repos(
        org_name: str,
        user: UserSession=Depends(get_current_user),
        github_app_auth: GithubAppAuthenticator=Depends(get_github_app_authenticator_singleton)
):
    filter_columns = (
        "id", "node_id", "name", "full_name", "owner", "private", "html_url", "description", "url", "created_at",
        "language", "license", "default_branch"
    )
    dispatcher = GithubOrgDataDispatcher(
        github_app_auth,
        org_name
    )
    repos = await dispatcher.get_org_repos()
    if not repos:
        return []
    
    filtered = []
    for rep in repos:
        _row = {}
        for k, v in rep.items():
            if k not in filter_columns:
                continue
            if k == 'owner':
                _row[k] = {m: n for m, n in v.items()
                            if m in ("login", "id", "node_id", "html_url", "type", "avatar_url")}
            else:
                _row[k] = v
        filtered.append(_row)
    return filtered
