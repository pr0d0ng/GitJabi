from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt, ExpiredSignatureError
from typing import TypedDict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.modules.oauth.hash import verify_password, DUMMY_HASH
from app.settings import api_settings


SECRET_KEY = api_settings.SECRET_KEY
DEFAULT_ALGORITHM = api_settings.TOKEN_DEFAULT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = api_settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = api_settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

class UserWithGroupScheme(TypedDict):
    id: int
    username: str
    password: str
    role: str
    position: str
    group_id: int
    email: str
    is_active: bool
    group_name: str | None
    group_description: str | None
    group_organization_id: int | None

class AuthJwtSchemeTDict(TypedDict):
    sub: str
    role: str
    exp: datetime

@dataclass(frozen=True)
class UserSession:
    username: str
    role: str
    expire_at: datetime
    claims: dict

def create_user_access_token(sub: str, role: str, extra_claims: dict):
    expire = datetime.now(timezone.utc) + timedelta(minutes=float(ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {
        "sub": sub,
        "role": role,
        "exp": expire,
        "extra_claims": extra_claims,
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=DEFAULT_ALGORITHM)

def decode_token(token, secret_key=None, algorithms=None) -> AuthJwtSchemeTDict:
    try:
        alg = algorithms or [DEFAULT_ALGORITHM]
        sec_key = secret_key or SECRET_KEY
        return jwt.decode(token, sec_key, algorithms=alg) # type: ignore
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="token expired")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

def create_refresh_token(data: dict):
    """
    리프레시 토큰 생성
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"}) 
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=DEFAULT_ALGORITHM)
    return encoded_jwt

#
#
def get_current_user(token: str = Depends(oauth2_scheme)):
    """유저 정보 가져오기 (로그인 필요하게 하는 함수)"""
    try:
        payload: AuthJwtSchemeTDict = decode_token(token)
        sub = payload.get("sub")
        role = payload.get("role")
        exp = payload.get("exp")
        claims = payload.get("extra_claims")

        if sub is None or role is None or exp is None or claims is None:
            raise HTTPException(status_code=401)
        return UserSession(sub, role, exp, claims)
    except JWTError as e:
        raise HTTPException(status_code=401, detail=str(e))

def get_current_admin(token: str = Depends(oauth2_scheme)):
    session = get_current_user(token)
    if session.role != "admin":
        raise HTTPException(status_code=403, detail="Not enough permission")
    return session

#
#

async def fetch_user_data(pool, username: str):
    query = """
        SELECT 
            u.id, u.username, u.password, u.role, u.position, 
            u.group_id, u.email, u.is_active,
            g.group_name, g.description as group_description, g.organization_id as group_organization_id
        FROM public.users u
        LEFT JOIN public.groups g ON u.group_id = g.id
        WHERE u.username = $1
    """
    
    async with pool.acquire() as conn:
        user: UserWithGroupScheme = await conn.fetchrow(query, username)

    if user:
        if not user["is_active"]:
            raise HTTPException(status_code=401, detail="Inactive user")
    else:
        raise HTTPException(status_code=403, detail="Not found user")
    return user

async def authenticate_user(pool, username: str, password: str):
    query = """
        SELECT 
            u.id, u.username, u.password, u.role, u.position, 
            u.group_id, u.email, u.is_active,
            g.group_name, g.description as group_description, g.organization_id as group_organization_id
        FROM public.users u
        LEFT JOIN public.groups g ON u.group_id = g.id
        WHERE u.username = $1
    """
    
    async with pool.acquire() as conn:
        user: UserWithGroupScheme = await conn.fetchrow(query, username)

    if user:
        valid_pw = verify_password(password, user["password"])
        if not user["is_active"]:
            raise HTTPException(status_code=401, detail="Inactive user")
    else:
        # 시간차 공격 방지 (DUMMY_HASH 비교)
        verify_password(password, DUMMY_HASH)
        valid_pw = False

    if not user or not valid_pw:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user
