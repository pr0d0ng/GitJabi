# Azure Functions Poller

`functions_poller/function_app.py`는 10분 주기 타이머로 SharePoint mp4를 찾고, AKS 회의록 API에 작업을 등록합니다.

## 1. 동작

1. Graph 앱 토큰 발급
2. 대상 사이트/폴더에서 mp4 조회
3. 이미 처리한 항목(idempotency key) 제외
4. 신규 mp4를 `POST /jobs/meeting-minutes`로 전송
5. 처리 이력을 Blob(`POLLER_STATE_CONTAINER/POLLER_STATE_BLOB`)에 저장

## 2. 로컬 실행

프로젝트 루트 기준:

```powershell
python -m pip install azure-functions
func start --script-root functions_poller
```

`Azure Functions Core Tools`(`func`)가 설치되어 있어야 합니다.

## 3. 필수 환경변수

- Graph 인증
  - `TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`
- SharePoint 기본 타깃(단일)
  - `SHAREPOINT_DOMAIN`, `SHAREPOINT_SITE_NAME`, `SHAREPOINT_SITE_PATH`, `SHAREPOINT_FOLDER_PATH`
- AKS API
  - `MEETING_API_BASE_URL` (예: `http://meeting-minutes-api.default.svc.cluster.local`)
  - `MEETING_API_KEY` (옵션)
- 상태 저장
  - `BLOB_CONNECTION_STRING`
  - `POLLER_STATE_CONTAINER` (기본: `meeting-automation-state`)
  - `POLLER_STATE_BLOB` (기본: `processed_items.json`)

## 4. 다중 팀/폴더

`POLLER_TARGETS_JSON`에 JSON 배열 문자열을 넣으면 복수 타깃을 순회합니다.

```json
[
  {
    "tenant_id": "b0e1d4a7-9742-4ff7-8a34-f7e6a838494a",
    "domain": "elixirrkc.sharepoint.com",
    "site_name": "DATA2-2",
    "site_path": "/sites/DATA2-2",
    "folder_path": "기록",
    "enabled": true
  }
]
```

## 5. 주의사항

- `@microsoft.graph.downloadUrl`은 만료되는 URL이므로 폴러가 찾은 직후 작업 등록해야 합니다.
- 중복방지는 `tenant:site:drive_item_id:etag` 키 기준입니다.
- Poller는 "작업 등록"만 수행하고 실제 회의록 생성은 AKS API 워커가 수행합니다.
