import logging
import httpx
from app.modules.github_app.authenticator import GithubAppAuthenticator
from app.modules.database.cache import CacheProxy


class GithubOrgDataDispatcher:
    _CACHE_SHORT = CacheProxy(maxsize=100, ttl=300) 

    def __init__(
            self, 
            github_auth: GithubAppAuthenticator,
            organization_name: str,
    ) -> None:
        self._authenticator = github_auth
        self._orgname = organization_name
        assert isinstance(github_auth, GithubAppAuthenticator) == True, "Invalid parameter: github_auth"

    async def get_org_repos(self, per_page=100):
        """[아웃바운드 GET] Organization의 레포 목록 조회.
        
        기본 캐시: 5분
        """
        cache_key = f"GithubOrgDataDispatcher:organization_repo:{self._orgname}"
        if await self._CACHE_SHORT.acontains(cache_key):
            logging.debug(f"Org Repos 캐시 존재: {cache_key}")
            return await self._CACHE_SHORT.aget(cache_key)

        org_installation_id = await self._authenticator.get_installation_id_by_org(self._orgname)
        if not org_installation_id:
            logging.error(
                f"{self._orgname}으로 Installtion ID 찾기 실패로 인해 Organization의 데이터 조회 실패"
            )
            return None
        headers = {
            "Authorization": f"Bearer {await self._authenticator.async_get_access_token(org_installation_id)}", 
            "Accept": "application/vnd.github.v3+json"
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/orgs/{self._orgname}/repos",
                headers=headers,
                params={"sort": "pushed", "direction": "desc", "per_page": per_page}
            )
            data = response.json()
            # 캐시 저장
            await self._CACHE_SHORT.aset(cache_key, data)
            return data

    # async def get_code_diff(self, diff_url):
    #     org_installation_id = await self._authenticator.get_installation_id_by_org(self._orgname)
    #     headers = {
    #         "Authorization": f"Bearer {await self._authenticator.async_get_access_token(org_installation_id)}", 
    #         "Accept": "application/vnd.github.v3+json"
    #     }
    #     async with httpx.AsyncClient() as client:
    #         response = await client.get(
    #             diff_url,
    #             headers=headers
    #         )
    #         data = response.json()
    #         return data
