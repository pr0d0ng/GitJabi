# GitHub Upload Guide

## 1) Upload these files/folders

- `graph_api.py`
- `meeting_minutes_pipeline.py`
- `teams_mp4_to_minutes.py`
- `PIPELINE_DATAFLOW.md`
- `README.md` (create if missing)
- `whisperx-worker/whisperx_key_action_pipeline.py`
- `whisperx-worker/` small utility scripts (optional)
- `.gitignore`
- `.env.example` (do not upload real `.env`)

## 2) Do NOT upload

- `.env` (contains secrets)
- `datasets/` (very large)
- `outputs/` (trained model artifacts)
- `out/` (generated minutes)
- `temp/` (downloaded videos)
- `whisperx-worker/out/` (intermediate STT results)
- local media files (`*.mp4`, `*.wav`, etc.)

## 3) Required `.env.example` keys

- `TENANT_ID`
- `CLIENT_ID`
- `CLIENT_SECRET`
- `SHAREPOINT_DOMAIN`
- `SHAREPOINT_SITE_NAME`
- `SHAREPOINT_FOLDER_PATH`
- `BLOB_CONNECTION_STRING`
- `BLOB_CONTAINER_NAME`
- `LLAMA_ENDPOINT`
- `DATABRICKS_TOKEN`
- `HF_TOKEN`

Optional:
- `GRAPH_EVENT_USER_ID`
- `GRAPH_EVENT_ID`

## 4) Minimal run commands

- Single local media:
  - `python meeting_minutes_pipeline.py --media meeting_test.mp4`

- Teams latest mp4 from folder:
  - `python teams_mp4_to_minutes.py --name-contains "회의명 일부"`

## 5) Security note

Current local `.env` has real secrets. Rotate these before production/public sharing:

- Azure AD app client secret
- Databricks token
- Azure Blob account key / connection string
- Hugging Face token
