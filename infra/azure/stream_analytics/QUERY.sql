/* 1. 공통 데이터 파싱 (JSON 문자열을 객체로 변환) */
WITH ParsedEvents AS (
    SELECT 
        event_type,
        -- payload가 문자열이므로 GetRecordPropertyValue를 통해 JSON 객체로 파싱
        TRY_CAST(payload AS RECORD) AS payload,
        EventProcessedUtcTime AS processed_time,
        timestamp AS event_time
    FROM [github-webhook-eventhub]
)

/* ----------------------------------- */
/*     1.  PSQL 로 보내는 요약 데이터       */
/* ----------------------------------- */
/* 1-1. Push 이벤트 요약본 -> Psql */
SELECT
    payload.ref AS ref,
    payload.pusher.name AS pusher_name,
    payload.repository.id AS repo_id,
    payload.repository.full_name AS repo_name,
    payload.repository.description AS repo_description,
    DATEADD(second, CAST(payload.repository.pushed_at AS bigint), '1970-01-01T00:00:00Z') AS pushed_at,
    payload.repository.language AS repo_language,
    -- 배열의 길이를 미리 계산해서 정수로 적재 (통계에 유리)
    GetArrayLength(TRY_CAST(payload.commits AS ARRAY)) AS commit_count,
    GetArrayLength(TRY_CAST(payload.head_commit.added AS ARRAY)) AS file_added,
    GetArrayLength(TRY_CAST(payload.head_commit.modified AS ARRAY)) AS file_modified,
    payload.head_commit.message AS head_commit_msg,
    payload.compare AS compare_url
INTO [az-psql-push-events]
FROM ParsedEvents
WHERE event_type = 'push'

/* 1-2. Pull Request 이벤트 요약본 -> Psql  */

SELECT
    payload.number AS pr_number,
    payload.action AS action,
    payload.sender.login AS event_performer,      -- 현재 이 이벤트를 일으킨 사람 (sender)
    payload.sender.type AS event_performer_type,            -- 'User' 인지 'Bot' 인지 구분
    payload.pull_request.id AS pr_id,
    payload.pull_request.title AS pr_title,
    payload.pull_request.state AS pr_state,
    udf.bodyprivacymasking(payload.pull_request.body) AS pr_body,
    payload.pull_request.[user].login AS pr_author,
    CAST(payload.pull_request.created_at AS datetime) AS pr_created_at,
    TRY_CAST(payload.pull_request.closed_at AS datetime) AS pr_closed_at,
    TRY_CAST(payload.pull_request.merged_at AS datetime) AS pr_merged_at,
    payload.pull_request.additions AS pr_additions,
    payload.pull_request.deletions AS pr_deletions,
    GetArrayLength(TRY_CAST(payload.pull_request.assignees AS ARRAY)) AS assignee_count,
    -- 2. Reviewers & Labels (필요시 GetArrayLength로 숫자만 저장하거나 원본 배열 캐스트)

    udf.parseusers(payload.pull_request.requested_reviewers) AS reviewers_list,
    udf.parselabels(payload.pull_request.labels) AS labels_list,

    payload.pull_request.head.ref AS head_ref,   -- 어디서 왔는지
    payload.pull_request.head.sha AS head_sha,
    payload.pull_request.base.ref AS base_ref,   -- 어디로 가는지 (main인지 확인용)

    payload.pull_request.diff_url AS pr_diff_url,
    payload.pull_request.patch_url AS pr_patch_url,
    payload.pull_request.html_url AS pr_html_url,

    payload.repository.id AS repo_id,
    payload.repository.full_name AS repo_name,
    payload.repository.html_url AS repo_url,
    payload.repository.language AS repo_language,
    payload.repository.description AS repo_description

INTO [az-psql-pull-requests]
FROM ParsedEvents
WHERE event_type = 'pull_request'
  AND (payload.action = 'opened' OR payload.action = 'closed' OR payload.action = 'ready_for_review') 
    AND (
        payload.pull_request.draft IS NULL 
        OR TRY_CAST(payload.pull_request.draft AS BIT) = 0
    )           
    -- draft = 일 경우 무시한다.


/* ----------------------------------- */
/*     1.  PSQL 로 보내는 요약 데이터       */
/* ----------------------------------- */
/*  1. Push 전체 --> ADLS Gen2          */
SELECT
    event_type,
    payload.action AS pr_action,
    payload.number AS pr_number,
    payload,
    processed_time
INTO [az-data-lake-storage-gen2-push-events] 
FROM ParsedEvents
WHERE event_type = 'push'


/* 2. Pull Request (Open/Close) 전체 --> ADLS Gen2      */
SELECT
    event_type,
    payload.action AS pr_action,
    payload.number AS pr_number,
    payload,
    processed_time
INTO [az-data-lake-storage-gen2] 
FROM ParsedEvents
WHERE event_type = 'pull_request'
  AND (payload.action = 'opened' OR payload.action = 'closed' OR payload.action = 'ready_for_review') -- 액션 필터링


