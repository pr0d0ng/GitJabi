import logging
import os, time
import hmac, hashlib, jwt
import httpx
from fastapi import HTTPException
from app.modules.database.cache import CacheProxy

def get_github_app_authenticator_singleton():
    if not hasattr(get_github_app_authenticator_singleton, "_instance"):
        get_github_app_authenticator_singleton._instance = GithubAppAuthenticator() #type: ignore
    return get_github_app_authenticator_singleton._instance                         #type: ignore


class GithubAppAuthenticator:
    """깃헙 App에 대한 인증 절차를 관리 및 수행한다.
    
    """
    __private_key = ""
    _CACHE_1HOUR = CacheProxy(maxsize=100, ttl=3000) 
    _CACHE_5MIN = CacheProxy(maxsize=100, ttl=300) 

    def __init__(self) -> None:
        self.__github_app_id: str = os.getenv("GITHUB_APP_ID", "")
        self.__github_app_webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
        self.__github_app_private_key_path: str = os.getenv("GITHUB_PRIVATE_KEY_PATH", "")

        assert self.__github_app_id != "", "GITHUB_APP_ID를 .env에서 할당하세요."
        assert self.__github_app_webhook_secret != "", "WEBHOOK_SECRET를 .env에서 할당하세요."
        assert self.__github_app_private_key_path != "", "PRIVATE_KEY_PATH를 .env에서 할당하세요."
        if self.__github_app_private_key_path and not os.path.exists(self.__github_app_private_key_path):
            raise OSError("PRIVATE_KEY_PATH가 존재하지 않습니다.")

        with open(self.__github_app_private_key_path, "r") as f:
            self.__private_key = f.read()
            assert self.__private_key is not None and self.__private_key != ""

    def verify_signature(self, payload: bytes, signature: str):
        """
        :param payload: 설명
        :type payload: bytes
        :param signature: 설명
        :type signature: str

        Exceptions
        -------
        `HTTPException`
        """
        mac = hmac.new(
            self.__github_app_webhook_secret.encode(),
            msg=payload,
            digestmod=hashlib.sha256,
        )
        expected = "sha256=" + mac.hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")


    def _generate_jwt(self):
        now = int(time.time())
        payload = {
            "iat": now - 60,
            "exp": now + (10 * 60),
            "iss": self.__github_app_id,
        }
        return jwt.encode(payload, self.__private_key, algorithm="RS256")


    async def async_get_access_token(self, installation_id: int):
        if await self._CACHE_1HOUR.acontains(installation_id):
            logging.debug(f"Cached access token (installation id: {installation_id})... ")
            return await self._CACHE_1HOUR.aget(installation_id)

        base_url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        jwt_token = self._generate_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                base_url,
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            response.raise_for_status()
            token = response.json()["token"]
        # 캐시 저장
        await self._CACHE_1HOUR.aset(installation_id, token)
        return token

    async def get_all_installations(self, cached=True):
        """Github APP을 설치한 Organization의 Installation ID 목록을 가져온다."""
        cache_key = "GithubAppAuthenticator:github_all_installations"
        if cached:
            if await self._CACHE_5MIN.acontains(cache_key):
                return await self._CACHE_5MIN.aget(cache_key)
        #
        #   :NOTE
        #   내부적으로 DB 트랜잭션 로직을 추가해야 하지만,
        #   MVP이므로 간단한 캐시로 대체
        #
        jwt_token = self._generate_jwt()
        
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/app/installations", headers=headers)
            installations = response.json()

            # 캐시 저장
            if cached:
                await self._CACHE_5MIN.aset(cache_key, installations)
            
            return installations 

    async def get_installation_id_by_org(self, org_name: str):
        """특정 조직의 이름으로 installation_id만 찾아준다."""
        installations = await self.get_all_installations()
        logging.debug(f"Github App Installations: {installations}")

        if installations:
            for inst in installations:
                if inst.get("account", {}).get("login") == org_name:
                    return inst["id"]
        return None
