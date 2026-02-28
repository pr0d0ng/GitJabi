
/*
 * 
 * 웹훅 이벤트 관련 테이블 
 * 
 * */

CREATE TABLE public._logs (
	id serial4 NOT NULL,
	"content" text NULL,
	CONSTRAINT _logs_pk PRIMARY KEY (id)
);


CREATE table if not EXISTS public.push_events (
    -- 고유 식별자 및 시간 기록
    id SERIAL PRIMARY KEY,
    pushed_at TIMESTAMP NOT NULL, 
    
    -- 레포지토리 정보
    repo_id BIGINT NOT NULL,              
    repo_name VARCHAR(255) NOT NULL,    
    repo_description TEXT,        
    repo_language VARCHAR(50),  
    
    -- 푸시 및 브랜치 정보
    ref VARCHAR(255),   
    pusher_name VARCHAR(100),  
    
    commit_count BIGINT DEFAULT 0,
    file_added BIGINT DEFAULT 0,
    file_modified BIGINT DEFAULT 0,
    
    head_commit_msg TEXT,   
    compare_url TEXT,
 
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);



CREATE table if not EXISTS github_pr_events (
	id SERIAL PRIMARY KEY,
    pr_id BIGINT,           
    pr_number BIGINT,                 
    repo_id BIGINT,                    
    repo_name VARCHAR(255),        
    
    action VARCHAR(50),               
    event_performer VARCHAR(100),     
    event_performer_type VARCHAR(20),
    
    pr_title TEXT,
    pr_author VARCHAR(100),            
    pr_state VARCHAR(20),             
    pr_body TEXT,                      
    
    head_ref VARCHAR(255),            
    head_sha VARCHAR(100),             
    base_ref VARCHAR(255),              
    
    pr_created_at TIMESTAMP WITH TIME ZONE,
    pr_closed_at TIMESTAMP WITH TIME ZONE,
    pr_merged_at TIMESTAMP WITH TIME ZONE,
    pr_additions BIGINT,
    pr_deletions BIGINT,
    assignee_count BIGINT,
    
    reviewers_raw JSONB,            
    labels_raw JSONB,        
    
    pr_diff_url TEXT,
    pr_patch_url TEXT,
    pr_html_url TEXT,
    repo_url TEXT,
    
    repo_language VARCHAR(50),
    repo_description TEXT,
    
    inserted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 성능 향상을 위한 인덱스 추가 (선택 사항)
CREATE INDEX idx_pr_repo_name ON github_pr_events(repo_name);
CREATE INDEX idx_pr_author ON github_pr_events(pr_author);
CREATE INDEX idx_pr_action ON github_pr_events(action);



--

/*
 * 
 * 지식 그래프 기반 추상적 정책 만들기  
 * 
 * */


CREATE TYPE policy_type AS ENUM ('security', 'design', 'quality', 'standard', 'audit', 'governance');
CREATE TYPE domain_type AS ENUM ('infra', 'backend', 'frontend', 'cloud', 'others');
CREATE TYPE priority_level AS ENUM ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW');
CREATE TYPE policy_status AS ENUM ('PROPOSED', 'ACTIVE');

CREATE TYPE user_role AS ENUM ('user', 'admin', 'collaborator');

-- 1. Organization 테이블 (Github)

create table if not exists organizations (
	id SERIAL primary KEY,
	org_id INT not null UNIQUE,
	org_name VARCHAR(1028) not null,
	description TEXT
);

-- 2. Groups 테이블 (권한 그룹)
CREATE table if not EXISTS groups (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(512) NOT NULL,
    organization_id INTEGER,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	CONSTRAINT fk_organization_id
	        FOREIGN KEY (organization_id) 
	        REFERENCES public.organizations(org_id)
	        ON DELETE SET NULL 
);

-- 3. Users 테이블 (사용자)
CREATE table if not EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) not null,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    role user_role DEFAULT 'user',
    position VARCHAR(512),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Policies 테이블
CREATE table if not EXISTS compliance_policies (
    id SERIAL PRIMARY KEY,
    policy_id VARCHAR(128) NOT NULL UNIQUE,
    group_id SMALLINT DEFAULT 0,  
    
    type policy_type,                                    
    domain domain_type,                                  
    
    risk_level priority_level DEFAULT 'MEDIUM',
    
    authority_group INTEGER REFERENCES groups(id) ON DELETE SET NULL, 
    
    title TEXT NOT NULL,  
    reason TEXT,          
    action_plan TEXT,   
    description TEXT,         
    tag TEXT[],  
    status policy_status DEFAULT 'PROPOSED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. 인덱스 (조회 성능 최적화)
CREATE INDEX idx_policies_authority_group ON compliance_policies(authority_group);
CREATE INDEX idx_policies_status ON compliance_policies(status);


-- Policy ID 자동 생성 
CREATE OR REPLACE FUNCTION generate_policy_id()
RETURNS TRIGGER AS $$
DECLARE
    type_prefix TEXT;
    next_val INTEGER;
BEGIN
    CASE NEW.type
        WHEN 'security' THEN type_prefix := 'P-SEC-';
        WHEN 'governance' THEN type_prefix := 'P-GOV-';
        WHEN 'standard' THEN type_prefix := 'P-STD-';
		WHEN 'design' THEN type_prefix := 'P-DES-';
		WHEN 'quality' THEN type_prefix := 'P-QUL-';
		WHEN 'audit' THEN type_prefix := 'P-AUD-';
        ELSE type_prefix := 'P-ETC-';
    END CASE;

    -- 2. 해당 타입으로 시작하는 가장 큰 숫자 추출 (+1)
    -- substring으로 숫자 부분만 잘라내어 정수로 변환 후 MAX값 찾기
    SELECT COALESCE(MAX(CAST(substring(policy_id from '\d+$') AS INTEGER)), 0) + 1
    INTO next_val
    FROM public.compliance_policies
    WHERE type = NEW.type;

    -- 3. 접두어와 3자리 숫자를 조합 (예: P-SEC-001)
    NEW.policy_id := type_prefix || lpad(next_val::text, 3, '0');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Policy ID 자동생성 트리거등록 
CREATE TRIGGER trg_generate_policy_id
BEFORE INSERT ON public.compliance_policies
FOR EACH ROW
WHEN (NEW.policy_id IS NULL OR NEW.policy_id = '') -- ID가 없을 때만 자동 생성
EXECUTE FUNCTION generate_policy_id();


/*
 * PR에 대한 스캔 결과 로그 테이블 
 * */
DO $$ BEGIN
    CREATE TYPE scan_category AS ENUM ('COMPLIANCE', 'RULEBASE');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

CREATE TABLE IF NOT EXISTS public.pr_scan_compliance_runs_history (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(128) not null,                 
    event_id VARCHAR(128),               
    pr_id INTEGER REFERENCES public.pull_requests_master(pr_id) ON DELETE SET NULL,
    pr_number INTEGER,
    title TEXT,                                
    compliance_violations JSONB DEFAULT '[]'::jsonb, 
    rulebase_violations JSONB DEFAULT '[]'::jsonb,  
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
ALTER TABLE public.pr_scan_compliance_runs_history ADD CONSTRAINT pr_id_unique_pr_scan_compliance_runs_history UNIQUE (pr_id);


CREATE INDEX IF NOT EXISTS idx_pr_history_pr_number ON public.pr_scan_compliance_runs_history(pr_number);
CREATE INDEX IF NOT EXISTS idx_pr_history_category ON public.pr_scan_compliance_runs_history(category);



/*
 * 벡터 DB 활성화 (Compliance Policies) 
 */

/* Azure OpenAI를 벡터 임베딩에 사용합니다. 
 * compliance_polices 테이블에 INSERT시 발동.
 * */
CREATE EXTENSION IF NOT EXISTS azure_ai;
CREATE EXTENSION IF NOT EXISTS vector;

SELECT azure_ai.set_setting(
	'azure_openai.endpoint', 
	'https://2dt-final-team2-aoai.openai.azure.com/'
);
SELECT azure_ai.set_setting(
	'azure_openai.subscription_key', 
	'E465JgpH9yZClCSRv8WFJ7s1xmPUcb4mNAjA2KqGW4kUbhShQHM4JQQJ99CBACNns7RXJ3w3AAABACOGspjF'
);
ALTER TABLE public.compliance_policies ADD COLUMN embedding VECTOR(1536);
-- embedding의 null을 찾을 때 색인 속도 향상 
CREATE INDEX idx_compliance_policies_pending_embedding 
ON public.compliance_policies (id) 
WHERE embedding IS NULL;

-- 외부에서 쿼리시 사용할 수 있도록 함수 생
CREATE OR REPLACE FUNCTION public.get_search_embedding(search_text text)
RETURNS vector
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN azure_openai.create_embeddings('text-embedding-3-small', search_text);
END;
$$;
/*
 * 예시 코드 
 * 

SELECT public.get_search_embedding('개인정보 보호 정책 알려줘');

WITH search_param AS (
    SELECT public.get_search_embedding('개인정보 보호 정책 알려줘') AS v
)
SELECT 
    id, 
    title, 
    domain, 
    1 - (embedding <=> (SELECT v FROM search_param)) AS similarity
FROM public.compliance_policies
WHERE embedding IS NOT NULL
ORDER BY embedding <=> (SELECT v FROM search_param)
LIMIT 5;
 * 
 * */

-- 속도 최적화 HNSW
CREATE INDEX ON public.compliance_policies USING hnsw (embedding vector_cosine_ops);

-- TRIGGER 이용해 동기방식으로 구현이 아닌, 스케줄러로 비동기 방식으로 구현한다.
-- 대량의 데이터가 들어올 수도 있기 때문이다.
CREATE OR REPLACE PROCEDURE public.proc_generate_batch_embeddings_for_compliance_policies()
LANGUAGE plpgsql
AS $$
DECLARE
    row_count int;
BEGIN
    BEGIN
        UPDATE public.compliance_policies
		SET embedding = azure_openai.create_embeddings(
	        'text-embedding-3-small', 
	        'TITLE: ' || COALESCE(title, 'Untitled') || chr(10) ||
	        'DOMAIN: ' || COALESCE(domain, 'others') || chr(10) ||
	        'RISK: ' || COALESCE(risk_level, 'LOW') || chr(10) ||
	        'KEYWORDS: ' || COALESCE(array_to_string(tag, ', '), '') || chr(10) ||
	        'SUMMARY: ' || COALESCE(content, '')
	    )
        WHERE id IN (
            SELECT id 
            FROM public.compliance_policies 
            WHERE embedding IS NULL 
            -- 필수 데이터인 content나 title이 있는 경우만 진행
            AND (content IS NOT NULL OR title IS NOT NULL)
            LIMIT 100
        );
        
        GET DIAGNOSTICS row_count = ROW_COUNT;
        IF row_count > 0 THEN
            RAISE NOTICE '성공: %개의 정책 임베딩 처리 완료', row_count;
        END IF;

    EXCEPTION WHEN OTHERS THEN
        RAISE WARNING 'Azure OpenAI API 호출 중 오류 발생: %', SQLERRM;
    END;
END;
$$;

-- 프로시저 크론 스케줄링.
SELECT cron.schedule('generate-embeddings-job', '* * * * *', 'CALL proc_generate_batch_embeddings_for_compliance_policies()');

/*
 * <프로시저와 크론 확인> 

SELECT jobid, schedule, command, nodename, nodeport, database, username 
FROM cron.job;


SELECT jobid, runid, status, return_message, start_time, end_time 
FROM cron.job_run_details 
ORDER BY start_time DESC 
LIMIT 10;

 * */

--------------------------------------------


/*
 * 
 * 룰베이스 정책 만들기 
 * 
 * */


CREATE TYPE rule_trigger_stage AS ENUM ('PRE_COMMIT', 'PR_OPENED', 'PR_SYNCHRONIZED', 'MANUAL');

CREATE TYPE rule_severity AS ENUM ('BLOCK', 'WARNING', 'INFO');

-- 3. 룰베이스 규칙 테이블 생성
CREATE table rulebase_policies (
    id SERIAL PRIMARY KEY,
    rule_id VARCHAR(50) NOT NULL UNIQUE,         
    rule_name VARCHAR(255) NOT NULL,           
   
    target_file_pattern VARCHAR(255),            
    rule_logic_type VARCHAR(255), 
    rule_logic_content TEXT NOT NULL,           
    
    trigger_stage rule_trigger_stage DEFAULT 'PR_OPENED',
    severity rule_severity DEFAULT 'WARNING',     
    
    is_enabled BOOLEAN DEFAULT true,               
    error_message TEXT,                           
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. 업데이트 시각 자동 갱신 트리거  
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_rulebase_policies_modtime
    BEFORE UPDATE ON rulebase_policies
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();


/*
 *  
 *  풀 리퀘스트 마스터 테이
 * 
 * */

create type review_stage_status as enum ('PENDING', 'IN_PROGRESS', 'APPROVED', 'REJECTED', 'SKIPPED');
create type ai_analysis_result as enum ('PENDING', 'IN_PROGRESS', 'PASSED', 'WARNING', 'VIOLATED');

create table if not exists pull_requests_master (
	id SERIAL primary key,
	event_root_id BIGINT not null ,
	pr_id BIGINT not null,
	pr_number BIGINT not null,
	repo_id BIGINT not null,
	repo_name VARCHAR(512) not null,
	
	status review_stage_status default 'PENDING',
	ai_analysis_result ai_analysis_result default 'PENDING',
	
	reviewer_group_id INTEGER default 1,
	
	reviewer_comment TEXT,
	is_mandatory BOOLEAN default true, 
	
	created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
	closed_at TIMESTAMP WITH TIME ZONE,

	CONSTRAINT fk_pull_requests_master_pr 
        FOREIGN KEY (event_root_id) 
        REFERENCES github_pr_events(id) 
        ON DELETE CASCADE,

    CONSTRAINT fk_pull_requests_master_group 
        FOREIGN KEY (reviewer_group_id) 
        REFERENCES groups(id) 
        ON DELETE SET NULL
);
COMMENT ON COLUMN pull_requests_master.event_root_id IS '최초 이벤트 ID (github_pr_events 테이블과 FK)';
COMMENT ON COLUMN pull_requests_master.reviewer_group_id IS '해당 리뷰 단계를 담당하는 권한 그룹 ID';
COMMENT ON COLUMN pull_requests_master.status IS '리뷰 상태 표시 ';
COMMENT ON COLUMN pull_requests_master.reviewer_comment IS '리뷰어 코멘트  ';
COMMENT ON CONSTRAINT fk_review_stage_group ON pull_requests_master IS '리뷰 단계 담당 그룹은 groups 테이블을 참조함';


--
-- github_pr_events에 특정 이벤트가 들어올 경우 pull_requests_master 데이터 생성 
-- 
CREATE OR REPLACE FUNCTION public.fn_initialize_pull_requests_master()
 RETURNS trigger
 LANGUAGE plpgsql -- 언어 명시 추가
AS $function$
DECLARE
    v_error_msg TEXT;
    v_error_detail TEXT;
BEGIN
    -- 1. 디버그 알림
    RAISE NOTICE 'Trigger started for PR ID: %, Action: %', NEW.pr_id, NEW.action;

    -- 2. 메인 로직 실행
    IF NEW.action = 'opened' THEN
        BEGIN
            INSERT INTO public.pull_requests_master (
                event_root_id, 
                pr_id, 
                pr_number,
                repo_id,
                repo_name,
                reviewer_group_id,
                status, 
                ai_analysis_result,
                is_mandatory
            )
            VALUES (
                NEW.id, 
                NEW.pr_id, 
                NEW.pr_number, 
                NEW.repo_id, 
                NEW.repo_name,
                1,
                'PENDING',
                'PENDING',
                TRUE
            );
            RAISE NOTICE 'Insert to pull_requests_master successful';

        EXCEPTION WHEN OTHERS THEN
            -- 3. 오류 발생 시 처리
            GET STACKED DIAGNOSTICS 
                v_error_msg = MESSAGE_TEXT,
                v_error_detail = PG_EXCEPTION_DETAIL;
            -- 혹은 전용 로그 테이블이 있다면:
            INSERT INTO public._logs (content) VALUES ('PR Master Init Error: ' || v_error_msg || ' (PR_ID: ' || NEW.pr_id || ')');

            RAISE WARNING 'Error initialized PR Master: %. Details logged.', v_error_msg;
        END;
    ELSE
        RAISE NOTICE 'Condition not met: action is not opened (%)', NEW.action;
    END IF;
    
    -- 무조건 NEW를 반환하여 원본 테이블 저장을 보장함
    RETURN NEW;
END;
$function$;

-- 트리거 생성 
drop trigger if exists tr_after_pr_opened on public.github_pr_events;
CREATE TRIGGER tr_after_pr_opened
AFTER INSERT ON github_pr_events
FOR EACH ROW
EXECUTE FUNCTION fn_initialize_pull_requests_master();


/*
 * 
 * 감사 관리 테이블   
 * 
 */

CREATE TYPE audit_category AS ENUM ('No Category', 'System', 'GitHub', 'Teams');
CREATE TYPE audit_status AS ENUM ('Success', 'Info', 'Warning', 'Failure');

CREATE table if not exists audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, 
    actor_name VARCHAR(100),                                      
    actor_role VARCHAR(100),                                      
    category audit_category default 'No Category',                  
    action_detail TEXT NOT NULL,                                  
    status audit_status DEFAULT 'Success',                        
    metadata JSONB,                                               
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

/*
 * 
 * 기타 메타 정보 테이블  
 * 
 * */

-- 깃헙 레포지터리에 대한 정보 테이블  
CREATE table if not exists github_repositories (
    repo_id BIGINT PRIMARY KEY,        
    org_name VARCHAR(100),          
    repo_name VARCHAR(255) NOT NULL, 
    full_name VARCHAR(500),         
    description TEXT,
    language VARCHAR(50), 
    html_url TEXT,
    is_private BOOLEAN,
    created_at TIMESTAMP WITH TIME ZONE, 
    updated_at TIMESTAMP WITH TIME ZONE, 
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() 
);


/*
 * 
 * 기타 통계 및 Metric 테이블(뷰)
 * 
 * */

-- review_stage_prs에서 AI 분석 지표 및 기타 통계 자료에 대한 View 테이블  
CREATE OR REPLACE VIEW v_pr_review_stats AS
WITH stats AS (
    SELECT 
        COUNT(*) AS total_count,
        COUNT(*) FILTER (WHERE ai_analysis_result = 'VIOLATED') AS violated_count,
        COUNT(*) FILTER (WHERE ai_analysis_result = 'PENDING') AS pending_count,
        COUNT(*) FILTER (WHERE ai_analysis_result = 'PASSED') AS success_count
    FROM review_stage_prs
)
SELECT 
    total_count,
    violated_count,
    pending_count,
    success_count,
    ROUND(CAST(violated_count AS NUMERIC) / NULLIF(total_count, 0) * 100, 2) AS violation_rate,
    ROUND(CAST(success_count AS NUMERIC) / NULLIF(total_count, 0) * 100, 2) AS success_rate
FROM stats;



/*
 * 
 * 변경 요청 Change Request 마스터 테이블 
 * 
 * */
CREATE TYPE change_request_status AS ENUM ('PENDING', 'VIOLATION', 'APPROVED', 'IN_PROGRESS', 'REJECTED');
CREATE TYPE change_request_priority AS ENUM ('HIGH', 'MEDIUM', 'LOW');

CREATE table if not exists public.change_requests_master (
    cr_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status change_request_status DEFAULT 'PENDING', 
    current_stage INTEGER DEFAULT 2,
    is_hotfix BOOLEAN DEFAULT FALSE,
    requester_id VARCHAR(512), -- 사용자 ID
    target_env VARCHAR(128), -- Production, Staging 등
    priority change_request_priority,
    authority_group INTEGER,
    risk_score INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    add constraint fk_authority_group
		foreign key (authority_group)
		references public.groups(id)
		on delete set null
);

-- 2. CR과 PR을 연결하는 매핑 테이블 (N:M 관계 대응)
CREATE table if not exists public.cr_pr_mapping (
    id SERIAL PRIMARY KEY,
    cr_id TEXT REFERENCES public.change_requests_master(cr_id) ON DELETE CASCADE,
    pr_id INTEGER, -- pull_requests_master의 pr_id와 연결
    linked_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- 동일한 CR에 동일한 PR이 중복 연결되는 것 방지
    UNIQUE(cr_id, pr_id)
);

-- 3. 성능 최적화를 위한 인덱스
CREATE INDEX idx_cr_pr_mapping_cr_id ON public.cr_pr_mapping(cr_id);
CREATE INDEX idx_cr_pr_mapping_pr_id ON public.cr_pr_mapping(pr_id);

-- CR ID 자동 생성  
CREATE OR REPLACE FUNCTION generate_cr_id()
RETURNS TRIGGER AS $$
DECLARE
    current_year TEXT;
    last_seq INTEGER;
BEGIN
    current_year := TO_CHAR(CURRENT_DATE, 'YYYY');

    SELECT COALESCE(MAX(CAST(substring(cr_id from '\d+$') AS INTEGER)), 0)
    INTO last_seq
    FROM public.change_requests
    WHERE cr_id LIKE 'CR-' || current_year || '-%';

    NEW.cr_id := 'CR-' || current_year || '-' || LPAD((last_seq + 1)::text, 4, '0');

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- cr id 트리거 등
CREATE TRIGGER trg_generate_cr_id
BEFORE INSERT ON public.change_requests_master
FOR EACH ROW
WHEN (NEW.cr_id IS NULL OR NEW.cr_id = '')
EXECUTE FUNCTION generate_cr_id();



/*
 * CR 테이블과 매핑할 기타 메타 정보
 * 
 * */
-- 1. GitJabi/Rulebase 스캔 결과 (보안/기술 위반 사항)
CREATE TYPE general_priority AS ENUM ('HIGH', 'MEDIUM', 'LOW');
create type decision_status as enum ('APPROVED', 'REJECTED', 'PENDING', 'EXCEPTION');
create type transaction_type as enum ('INSERT', 'UPDATE', 'DELETE')

-- 2. 리스크 요인 (Risk Factors)
CREATE TABLE if not exists public.cr_risk_factors (
    factor_id SERIAL PRIMARY KEY,
    cr_id TEXT REFERENCES public.change_requests_master(cr_id) ON DELETE CASCADE,
    title TEXT not NULL,          
    value_text TEXT not NULL,   
    description TEXT,
    icon_type VARCHAR(128),
    color_theme VARCHAR(128)
);

-- 3. 승인 결정권자 상태 (Decisions)
CREATE TABLE if not exists public.cr_decisions (
    decision_id SERIAL PRIMARY KEY,
    cr_id TEXT REFERENCES public.change_requests_master(cr_id) ON DELETE CASCADE,
    approver_role VARCHAR(512),    
    approver_name VARCHAR(512),
    status decision_status,  
    comment TEXT,
    decided_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. 감사 로그 (Audit Logs)

CREATE TABLE if not exists public.cr_audit_logs (
    log_id SERIAL PRIMARY KEY,
    cr_id TEXT REFERENCES public.change_requests_master(cr_id) on delete set null,
    action_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    action_type transaction_type,      
    action_alias VARCHAR(256),
    actor_id TEXT      
);
ALTER TABLE public.cr_audit_logs
add column old_data JSONB,
add column new_data JSONB,
ADD COLUMN previous_hash TEXT,
ADD COLUMN record_hash TEXT;

/*
 * Change Requests 관련 트리거 함수 
 * 
 */

-- CR 생성시 authority_group 값으로 해당 사용자를 전부 cr_decisions에 추가한다 (PENDING)
CREATE OR REPLACE FUNCTION set_initial_cr_decisions()
RETURNS TRIGGER AS $$
BEGIN
    -- 1. 신규 생성된 CR의 authority_group에 속한 모든 사용자를 찾아서 결재 테이블에 삽입
    INSERT INTO public.cr_decisions (
        cr_id, 
        approver_role, 
        approver_name, 
        status, 
        comment, 
        decided_at
    )
    SELECT 
        NEW.cr_id, 
        u.position, 
        u.username,  
        'PENDING', 
        NULL,  
        NULL 
    FROM 
        public.users u
    WHERE 
        u.group_id = NEW.authority_group; -- CR에 지정된 그룹 ID와 일치하는 사용자들

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_after_cr_insert
AFTER INSERT ON public.change_requests_master
FOR EACH ROW
EXECUTE FUNCTION set_initial_cr_decisions();


--
-- PR 검사가 완료된 경우 해당하는 CR의 스테이지넘버 승력 
CREATE OR REPLACE FUNCTION fn_update_cr_stage_on_scan()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE public.change_requests_master
    SET current_stage = 5,
        updated_at = CURRENT_TIMESTAMP
    WHERE cr_id IN (
        SELECT m.cr_id 
        FROM public.cr_pr_mapping m 
        WHERE m.pr_id = NEW.pr_id
    )
    AND current_stage < 4;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_after_scan_insert
AFTER INSERT ON public.pr_scan_compliance_runs_history
FOR EACH ROW
EXECUTE FUNCTION fn_update_cr_stage_on_scan();

-- --------------------------------------------------------------

/*
 * Azure PSQL 사용할 경우, pgcrypto를 사용 설정해주어야 한다.
 *   PSQL 대시보드 -> Server Parameter -> azure.extensions -> PGCRYPTO 체크 후 Save 
 */

CREATE EXTENSION IF NOT EXISTS pgcrypto;



-- 감사 로그 생성 트리거 함수 

CREATE OR REPLACE FUNCTION log_unified_audit_events()
RETURNS TRIGGER AS $$
DECLARE
    current_app_user TEXT;
    v_prev_hash TEXT;
    v_payload TEXT;
    v_cr_id TEXT;
BEGIN
    -- 1. 사용자 ID 추출 (set_config로 설정한 값 읽기)
    current_app_user := current_setting('app.current_user', true);
    IF current_app_user IS NULL OR current_app_user = '' THEN
        current_app_user := 'SYSTEM';
    END IF;

    -- 2. CR_ID 추출 (테이블마다 컬럼명이 다를 수 있으니 유연하게 대응)
    IF (TG_OP = 'DELETE') THEN
        v_cr_id := OLD.cr_id;
    ELSE
        v_cr_id := NEW.cr_id;
    END IF;

    -- 3. 이전 해시값 가져오기 (박제 로직)
    SELECT record_hash INTO v_prev_hash 
    FROM public.cr_audit_logs 
    ORDER BY log_id DESC LIMIT 1;
    v_prev_hash := COALESCE(v_prev_hash, 'GENESIS_BLOCK');

    -- 4. 해시 생성을 위한 페이로드 조립
    -- 테이블명(TG_TABLE_NAME)과 작업(TG_OP)을 포함하여 어떤 변경인지 명확히 함
    v_payload := v_prev_hash || v_cr_id || TG_TABLE_NAME || TG_OP || current_app_user || 
                 COALESCE(row_to_json(NEW)::text, row_to_json(OLD)::text, '');

    -- 5. 감사 로그 삽입
    INSERT INTO public.cr_audit_logs (
        cr_id, 
        action_type, 
		action_alias,
        actor_id, 
        old_data, 
        new_data, 
        previous_hash, 
        record_hash,
        action_time
    )
    VALUES (
        v_cr_id,
		TG_OP::transaction_type,
        TG_TABLE_NAME || '_' || TG_OP, 
        current_app_user,
        CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN row_to_json(OLD)::jsonb ELSE NULL END,
        CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN row_to_json(NEW)::jsonb ELSE NULL END,
        v_prev_hash,
        encode(digest(v_payload, 'sha256'), 'hex'), 
        NOW()
    );

    IF (TG_OP = 'DELETE') THEN RETURN OLD; ELSE RETURN NEW; END IF;
END;
$$ LANGUAGE plpgsql;

-- 1. CR 마스터 정보 변경 감시
DROP TRIGGER IF EXISTS trg_audit_cr_master ON public.change_requests_master;
CREATE TRIGGER trg_audit_cr_master
AFTER INSERT OR UPDATE ON public.change_requests_master
FOR EACH ROW EXECUTE FUNCTION log_unified_audit_events();

-- 2. 결재 상태(승인/반려) 변경 감시
DROP TRIGGER IF EXISTS trg_audit_cr_decision ON public.cr_decisions;
CREATE TRIGGER trg_audit_cr_decision
AFTER INSERT OR UPDATE OR DELETE ON public.cr_decisions
FOR EACH ROW EXECUTE FUNCTION log_unified_audit_events();



/*
 * 
 *  PR 생성 및 이벤트 발동시, Change Request에 할당한다.
 *  
 * */

CREATE OR REPLACE FUNCTION public.fn_sync_pr_to_cr_mapping()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_cr_id TEXT;
    v_error_msg TEXT;
BEGIN
    -- 1. 대문자로 정규화하여 파싱 (패턴: CR-20XX-XXXX...)
    v_cr_id := UPPER(substring(NEW.pr_title from '(?i)CR-[0-9]{4}-[0-9]{1,10}'));

    IF v_cr_id IS NOT NULL THEN
        BEGIN
            -- 3. CR 마스터 테이블 존재 여부 확인
            IF EXISTS (SELECT 1 FROM public.change_requests_master WHERE cr_id = v_cr_id) THEN
                
                -- 4. 매핑 테이블 삽입 (Conflict 무시)
                INSERT INTO public.cr_pr_mapping (cr_id, pr_id)
                VALUES (v_cr_id, NEW.pr_id)
                ON CONFLICT (cr_id, pr_id) DO NOTHING;
                
                RAISE NOTICE 'Success: Linked PR(%) to CR(%)', NEW.pr_id, v_cr_id;
            ELSE
                -- CR ID가 마스터에 없는 경우 별도의 '미연결 로그'를 남길 수도 있습니다.
                RAISE WARNING 'Warning: CR ID % found in title but does not exist in master table.', v_cr_id;
            END IF;

        EXCEPTION WHEN OTHERS THEN
            GET STACKED DIAGNOSTICS v_error_msg = MESSAGE_TEXT;
            RAISE WARNING 'Error in fn_sync_pr_to_cr_mapping: %', v_error_msg;
			
			-- Logging
			INSERT INTO public._logs (content)
			VALUES (v_error_msg);
        END;
    END IF;

    RETURN NEW;
END;
$function$;

DROP TRIGGER IF EXISTS trg_sync_pr_mapping ON public.github_pr_events;
CREATE TRIGGER trg_sync_pr_mapping
AFTER INSERT ON public.github_pr_events
FOR EACH ROW
EXECUTE FUNCTION public.fn_sync_pr_to_cr_mapping();



/*
 * 컴플라이언스 리스크 분석 임시 뷰 (더미)
 * 
 * */
CREATE OR REPLACE VIEW vw_cr_risk_analysis AS
WITH violation_expanded AS (
    SELECT
        m.cr_id,
        s.run_id,
        v,

        CASE v->'output'->>'severity'
            WHEN 'CRITICAL' THEN 40
            WHEN 'HIGH'     THEN 20
            WHEN 'MEDIUM'   THEN 10
            ELSE 0
        END AS severity_weight,

        COALESCE((v->'output'->>'violation_confidence')::numeric, 0)
            AS confidence,

        (v->'output'->>'judgment_result') AS judgment,

        (v->'output'->'evaluation_results'->>'is_conflicting')::boolean
            AS is_conflicting,

        v->>'related_policy_id' AS policy_id,

        jsonb_array_length(
            COALESCE(
                v->'output'->'referenced_knowledge_card_ids',
                '[]'::jsonb
            )
        ) AS knowledge_count

    FROM public.cr_pr_mapping m
    JOIN public.pr_scan_compliance_runs_history s
        ON m.pr_id = s.pr_id
    CROSS JOIN LATERAL jsonb_array_elements(
        COALESCE(s.compliance_violations, '[]'::jsonb)
    ) v
),

scan_stats AS (
    SELECT
        cr_id,

        COUNT(*) FILTER (
            WHERE judgment = 'VIOLATION'
        ) AS violation_count,

        SUM(severity_weight * confidence)
            AS weighted_violation_score,

        COUNT(DISTINCT policy_id) AS policy_spread,

        COUNT(*) FILTER (
            WHERE is_conflicting = true
        ) AS conflict_count,

        COUNT(*) FILTER (
            WHERE judgment = 'INSUFFICIENT_CONTEXT'
        ) AS insufficient_count,

        SUM(knowledge_count) AS knowledge_impact

    FROM violation_expanded
    GROUP BY cr_id
),

risk_calc AS (
    SELECT
        cr.cr_id,

        COALESCE(ss.violation_count, 0)          AS violation_cnt,
        COALESCE(ss.weighted_violation_score, 0) AS weighted_score,
        COALESCE(ss.policy_spread, 0)            AS policy_spread,
        COALESCE(ss.conflict_count, 0)           AS conflict_cnt,
        COALESCE(ss.insufficient_count, 0)       AS insufficient_cnt,
        COALESCE(ss.knowledge_impact, 0)         AS knowledge_score,

        CASE
            WHEN cr.target_env = 'PRODUCTION' THEN 20
            ELSE 5
        END AS env_weight

    FROM public.change_requests_master cr
    LEFT JOIN scan_stats ss ON cr.cr_id = ss.cr_id
)

SELECT
    rc.cr_id,

    GREATEST(
        0,
        LEAST(
            93,
            rc.weighted_score
            + (rc.conflict_cnt * 10)
            + (rc.insufficient_cnt * 5)
            + (rc.policy_spread * 3)
            + rc.env_weight
        )
    ) AS risk_score,

    jsonb_build_object(
        'violation_count', rc.violation_cnt,
        'weighted_score', rc.weighted_score,
        'conflict_count', rc.conflict_cnt,
        'policy_spread', rc.policy_spread,
        'insufficient_context', rc.insufficient_cnt,
        'knowledge_impact', rc.knowledge_score,
        'environment_weight', rc.env_weight
    ) AS risk_breakdown,
    
	(
	    SELECT jsonb_agg(elem)
	    FROM jsonb_array_elements(
	        jsonb_build_array(
	            -- Severity Risk
	            CASE 
	                WHEN rc.weighted_score > 0 THEN
	                    jsonb_build_object(
	                        'id', 'severity',
	                        'title', '심각도 기반 위반',
	                        'value', rc.violation_cnt || '건 (가중 ' || round(rc.weighted_score,1) || '점)',
	                        'weight', rc.weighted_score,
	                        'icon', 'ShieldAlert',
	                        'color',
	                            CASE 
	                                WHEN rc.weighted_score >= 60 THEN 'red'
	                                WHEN rc.weighted_score >= 30 THEN 'orange'
	                                ELSE 'yellow'
	                            END,
	                        'description', 'Severity × Confidence 기반 계산된 리스크입니다.'
	                    )
	            END,
	
	            -- Conflict Risk
	            CASE 
	                WHEN rc.conflict_cnt > 0 THEN
	                    jsonb_build_object(
	                        'id', 'conflict',
	                        'title', '정책 충돌',
	                        'value', rc.conflict_cnt || '건',
	                        'weight', rc.conflict_cnt * 10,
	                        'icon', 'AlertTriangle',
	                        'color', 'red',
	                        'description', '정책과 직접 충돌하는 변경 사항이 존재합니다.'
	                    )
	            END,
	
	            -- Policy Spread
	            CASE 
	                WHEN rc.policy_spread >= 3 THEN
	                    jsonb_build_object(
	                        'id', 'spread',
	                        'title', '다중 정책 영향',
	                        'value', rc.policy_spread || '개 정책 영향',
	                        'weight', rc.policy_spread * 3,
	                        'icon', 'Layers',
	                        'color', 'orange',
	                        'description', '여러 보안 정책에 영향을 주는 변경입니다.'
	                    )
	            END,
	
	            -- Insufficient Context
	            CASE 
	                WHEN rc.insufficient_cnt > 0 THEN
	                    jsonb_build_object(
	                        'id', 'context',
	                        'title', '판단 불가 항목',
	                        'value', rc.insufficient_cnt || '건',
	                        'weight', rc.insufficient_cnt * 5,
	                        'icon', 'EyeOff',
	                        'color', 'gray',
	                        'description', '코드 맥락 부족으로 판단이 불가능한 항목입니다.'
	                    )
	            END,
	
	            -- Environment Risk
	            CASE 
	                WHEN rc.env_weight >= 20 THEN
	                    jsonb_build_object(
	                        'id', 'env',
	                        'title', '운영 환경 배포',
	                        'value', 'Production',
	                        'weight', rc.env_weight,
	                        'icon', 'Target',
	                        'color', 'purple',
	                        'description', '운영 환경 배포는 높은 승인 기준이 요구됩니다.'
	                    )
	            END
	        )
	    ) elem
	    WHERE elem IS NOT null or elem = 'null'
	) AS risk_factors

FROM risk_calc rc;



