"""
Github Check Run에 대한 기능 구현 (API Outbound)

Check Run에 대한 정보는 아래 링크를 참조.  
    - https://docs.github.com/ko/pull-requests/collaborating-with-pull-requests/collaborating-on-repositories-with-code-quality-features/about-status-checks  

Check Run API에 대한 정보:  
    - https://docs.github.com/ko/rest/checks/runs?apiVersion=2022-11-28  

"""
import logging
import httpx
from datetime import datetime, timezone
from app.settings import api_settings
from enum import Enum

class GithubCheckRunStatusEnum(str, Enum):
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'

class GithubCheckRunConclusionEnum(str, Enum):
    FAILURE = 'failure'
    SUCCESS = 'success'

class GithubCheckRunDispatcher:
    GITHUB_API_CHECKRUN_BASE = "{base_url}/repos/{owner}/{repo}/check-runs"

    def __init__(
            self, 
            token: str, 
            owner: str, 
            repo: str, 
            sha: str,
    ) -> None:
        self._token = token
        self._owner = owner
        self._repo = repo
        self._sha = sha
        _ = self._base_url
        _ = self._header

    @property
    def _header(self):
        assert bool(self._token) == True 
        self.__header = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}", 
            "X-GitHub-Api-Version": "2022-11-28"
        }
        return self.__header

    @property
    def _base_url(self):
        self.__target_base_url = api_settings.GITHUB_API_BASE_URL
        assert self.__target_base_url is not None and \
            self.__target_base_url != "", "GITHUB_API_BASE_URL가 잘못되었습니다. .env파일을 점검하세요."
        self.__target_base_url = self.__target_base_url.rstrip('/')
        return self.__target_base_url

    async def start_check_run(
            self, 
            name: str,
    ):
        """Github Check Run을 생성합니다."""
        url = self.GITHUB_API_CHECKRUN_BASE.format(
            base_url=self._base_url,
            owner=self._owner, 
            repo=self._repo
        )

        logging.debug(url)

        
        payload = {
            "name": name, # GitHub UI에 뜰 이름
            "head_sha": self._sha,
            "status": GithubCheckRunStatusEnum.IN_PROGRESS.value,      
            "started_at": datetime.now(timezone.utc).isoformat()
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self._header)
            response.raise_for_status()
            return response.json()["id"] # 나중에 업데이트하기 위해 ID 반환
            
    async def end_of_check_run(
            self,
            check_run_id: int,
            conclusion: GithubCheckRunConclusionEnum,
            title: str,
            summary: str,
            text: str
    ):
        url = self.GITHUB_API_CHECKRUN_BASE\
                .format(base_url=self._base_url, owner=self._owner, repo=self._repo) + f"/{check_run_id}"
        
        logging.debug(url)
        
        payload = {
            "status": GithubCheckRunStatusEnum.COMPLETED.value,           
            "conclusion": conclusion.value, 
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "output": {
                "title": title,
                "summary": summary,
                "text": text
            }
        }
        
        async with httpx.AsyncClient() as client:
            await client.patch(url, json=payload, headers=self._header)
            logging.debug(f"[{check_run_id}] 상태 업데이트 완료: {payload['conclusion']}")

