# Meeting Minutes Pipeline (SharePoint -> STT -> Minutes -> Blob)

이 프로젝트는 SharePoint(Teams 녹화 포함)에서 mp4를 가져와,
STT + key/action 분류 + LLM 요약으로 회의록(`.md`)을 만들고,
메타데이터(`.json`)와 함께 Azure Blob에 업로드합니다.

---

## 0. 핵심 스크립트

- `teams_mp4_to_minutes.py`
  - SharePoint 폴더에서 mp4 1개 선택/다운로드
  - `meeting_minutes_pipeline.py` 실행
- `meeting_minutes_pipeline.py`
  - WhisperX key/action 결과 기반으로 회의록 생성
  - `.md`, `.meta.json` 저장 + Blob 업로드
- `graph_api.py`
  - Graph 인증/사이트 조회/파일 열람 유틸

---

## 1. 사전 준비

### 1-1. Python 환경

권장: 가상환경(예: `audio_chat`) 활성화 후, **프로젝트 루트**에서 실행

```powershell
python -V
```

### 1-2. 필수 패키지 설치

```powershell
python -m pip install requests python-dotenv azure-storage-blob msal
```

WhisperX 관련 의존성은 기존 `whisperx-worker` 실행 환경을 사용합니다.

### 1-3. 모델/토큰 준비

- Hugging Face token (`HF_TOKEN`)
- Databricks endpoint/token (`LLAMA_ENDPOINT`, `DATABRICKS_TOKEN`)
- Azure Blob connection string
- Microsoft Graph 앱 권한
  - `Sites.Read.All` (Application)
  - `Files.Read.All` (Application)
  - 관리자 동의 완료

---

## 2. .env 설정

루트의 `.env`에 최소 아래 값이 필요합니다.

```env
TENANT_ID=
CLIENT_ID=
CLIENT_SECRET=

SHAREPOINT_DOMAIN=elixirrkc.sharepoint.com
SHAREPOINT_SITE_NAME=DATA2-2
SHAREPOINT_FOLDER_PATH=기록

GRAPH_AUTH_MODE=app

BLOB_CONNECTION_STRING=
BLOB_CONTAINER_NAME=meeting-videos

LLAMA_ENDPOINT=
DATABRICKS_TOKEN=
HF_TOKEN=

# 선택: Graph 캘린더 이벤트 기반 메타데이터
GRAPH_EVENT_USER_ID=
GRAPH_EVENT_ID=
```

참고:
- `SHAREPOINT_FOLDER_PATH`는 보통 `기록`처럼 드라이브 루트 기준 경로를 사용합니다.
- 실제 비밀값은 절대 GitHub에 올리지 마세요(`.env` 제외 필수).

---

## 3. 가장 간단한 실행 (권장)

### SharePoint 폴더에서 최신 mp4 1개 처리

```powershell
python teams_mp4_to_minutes.py
```

### 파일명 일부로 필터해서 처리

```powershell
python teams_mp4_to_minutes.py --name-contains "모임 녹음녹화"
```

실행 결과:
- 로컬
  - `out/meeting_minutes/<timestamp>.minutes.md`
  - `out/meeting_minutes/<timestamp>.minutes.meta.json`
- Blob
  - `meeting-minutes/<timestamp>.minutes.md`
  - `meeting-minutes/<timestamp>.minutes.meta.json`

`<timestamp>`는 원본 mp4의 `lastModifiedDateTime` 기반입니다.

---

## 4. 상세 옵션

### teams_mp4_to_minutes.py

```powershell
python teams_mp4_to_minutes.py ^
  --folder-path "기록" ^
  --name-contains "회의명 일부" ^
  --output-stem "20260219-090638" ^
  --blob-prefix "meeting-minutes" ^
  --key-limit 180 ^
  --action-limit 120 ^
  --other-sample-limit 20 ^
  --max-prompt-chars 18000
```

옵션 설명:
- `--output-stem`: 출력 파일명 강제 지정
- `--no-blob-upload`: Blob 업로드 없이 로컬만 저장
- `--skip-stt`: 이미 `whisperx-worker/out/<stem>.key_action.json` 있을 때 STT 스킵

### meeting_minutes_pipeline.py 단독 실행

```powershell
python meeting_minutes_pipeline.py --media meeting_test.mp4
```

---

## 5. 처리 흐름 (요약)

1. Graph 인증 후 사이트/폴더 파일 목록 조회
2. mp4 선택 + 로컬 다운로드
3. WhisperX 파이프라인으로 발화/화자/key/action 산출
4. LLM에 구조화 프롬프트 전달하여 회의록 생성
5. `일시`가 비어 있으면 원본 mp4 수정시각을 자동 대입
6. `.md` + `.meta.json` 저장 후 Blob 업로드

---

## 6. 품질 튜닝 팁

- 회의록이 너무 두루뭉실하면
  - `--max-prompt-chars` 증가 (예: 22000)
  - `--other-sample-limit` 소폭 증가 (예: 25)
- Action Item 정확도 개선
  - 현재 규칙 추출(담당/기한/작업) + LLM 보조 방식
  - STT 품질이 낮으면 결과도 같이 떨어집니다

---

## 7. 자주 발생하는 오류

### `Missing LLAMA_ENDPOINT or DATABRICKS_TOKEN`
- `.env` 로드 경로/값 확인
- 실행 Python이 같은 환경인지 확인

### Graph 400/404
- `SHAREPOINT_SITE_NAME`, `SHAREPOINT_FOLDER_PATH` 확인
- 앱 권한/관리자 동의 확인

### 모듈 없음 (`ModuleNotFoundError`)
- 해당 환경에 패키지 재설치

```powershell
python -m pip install requests python-dotenv azure-storage-blob msal
```

---

## 8. GitHub 업로드

- 가이드: `GITHUB_UPLOAD_GUIDE.md`
- 예시 env: `.env.example`
- 반드시 제외: `.env`, `datasets/`, `outputs/`, `out/`, `temp/`, `whisperx-worker/out/`

---

## 9. 관련 문서

- `PIPELINE_DATAFLOW.md`: 입력/출력 데이터 흐름
- `ROOT_FILE_MAP.md`: 루트 파일 정리 맵
- `functions_poller/README.md`: Azure Functions Timer Poller(SharePoint -> AKS Job 등록)
- `deploy/aks/README.md`: AKS Meeting Minutes API 배포 가이드
