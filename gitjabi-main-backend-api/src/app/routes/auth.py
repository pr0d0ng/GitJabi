import logging
from fastapi import Depends, APIRouter, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from app.modules.oauth.authentication import (
    create_user_access_token, create_refresh_token,
    authenticate_user, fetch_user_data, 
    decode_token
)
from app.settings import api_settings
from app.modules.database.psql import aget_db_pool
from app.models.auth import UserCreate
from app.modules.oauth.hash import hash_password

HTTP_SECURE = api_settings.HTTP_SECURE

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/token")
async def login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        pool = Depends(aget_db_pool)
    ):
    user = await authenticate_user(pool, form_data.username, form_data.password)

    access_token = create_user_access_token(
        user["username"],
        user["role"],
        extra_claims={
            "position": user["position"],
            "group_id": user["group_id"],
            "group_name": user["group_name"],
            "group_organization_id": user["group_organization_id"]
        }
    )
    refresh_token = create_refresh_token(
        data={"sub": user["username"], "role": user["role"]}
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,  
        secure=HTTP_SECURE,   
        samesite="none",  
        max_age=60 * 60 * 24 * 7 # 7일
    )

    return {
        "access_token": access_token, 
        "user": {
            "username": user["username"],
            "role": user["role"],
            "position": user["position"],
            "group_id": user["group_id"],
            "group_name": user["group_name"]
        }, 
        "token_type": "bearer"
    }

@router.post("/token/refresh")
async def refresh_access_token(
    request: Request, 
    pool = Depends(aget_db_pool)
):
    # 1. 쿠키에서 refresh_token 추출
    refresh_token = request.cookies.get("refresh_token")

    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    # 2. 토큰 디코딩 및 검증
    decoded_payload = decode_token(refresh_token)
    username: str = decoded_payload.get("sub")
        
    if username is None or decoded_payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
    user = await fetch_user_data(pool, username) 

    new_access_token = create_user_access_token(
        user["username"],
        user["role"],
        extra_claims={
            "position": user["position"],
            "group_id": user["group_id"],
            "group_name": user["group_name"],
            "group_organization_id": user["group_organization_id"]
        }
    )

    return {
        "access_token": new_access_token, 
        "user": {
            "username": user["username"],
            "role": user["role"],
            "position": user["position"],
            "group_id": user["group_id"],
            "group_name": user["group_name"]
        }, 
        "token_type": "bearer"
    }



@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        httponly=True,
        samesite="none",
        secure=HTTP_SECURE 
    )
    return {"detail": "Successfully logged out"}


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, pool=Depends(aget_db_pool)):
    # 1. 중복 사용자 확인 (username 또는 email)
    async with pool.acquire() as conn:
        existing_user = await conn.fetchrow(
            "SELECT id FROM public.users WHERE username = $1 OR email = $2",
            user_in.username, user_in.email
        )
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="이미 존재하는 사용자명 또는 이메일입니다."
            )

        hashed_password = hash_password(user_in.password)

        try:
            new_user = await conn.fetchrow(
                """
                INSERT INTO public.users 
                (username, password, email, position, group_id, is_active)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, username, email
                """,
                user_in.username,
                hashed_password,
                user_in.email,
                user_in.position,
                1,
                True 
            )
            return {"message": "회원가입 성공", "user": new_user}
            
        except Exception as e:
            logging.error(e)
            raise HTTPException(status_code=500, detail=f"회원가입 중 오류 발생")

