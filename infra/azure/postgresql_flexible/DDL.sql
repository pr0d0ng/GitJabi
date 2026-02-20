/*
 * 
 * 웹훅 이벤트 관련 테이블 
 * 
 * */

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

-- 2. Groups 테이블 (권한 그룹)
CREATE table if not EXISTS groups (
    id SERIAL PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Users 테이블 (사용자)
CREATE table if not EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(100),
    group_id INTEGER REFERENCES groups(id) ON DELETE SET NULL,
    role VARCHAR(50) DEFAULT 'MEMBER',
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
 * 리뷰 스테이지 (PR 검사 현황) 테이블 
 * 
 * */

create type review_stage_status as enum ('PENDING', 'IN_PROGRESS', 'APPROVED', 'REJECTED', 'SKIPPED');
create type ai_analysis_result as enum ('PENDING', 'IN_PROGRESS', 'PASSED', 'WARNING', 'VIOLATED');

create table if not exists review_stage_prs (
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

	CONSTRAINT fk_review_stage_pr 
        FOREIGN KEY (event_root_id) 
        REFERENCES github_pr_events(id) 
        ON DELETE CASCADE,

    CONSTRAINT fk_review_stage_group 
        FOREIGN KEY (reviewer_group_id) 
        REFERENCES groups(id) 
        ON DELETE SET NULL
);
COMMENT ON COLUMN review_stage_prs.event_root_id IS '최초 이벤트 ID (github_pr_events 테이블과 FK)';
COMMENT ON COLUMN review_stage_prs.reviewer_group_id IS '해당 리뷰 단계를 담당하는 권한 그룹 ID';
COMMENT ON COLUMN review_stage_prs.status IS '리뷰 상태 표시 ';
COMMENT ON COLUMN review_stage_prs.reviewer_comment IS '리뷰어 코멘트  ';
COMMENT ON CONSTRAINT fk_review_stage_group ON review_stage_prs IS '리뷰 단계 담당 그룹은 groups 테이블을 참조함';


--
-- github_pr_events에 특정 이벤트가 들어올 경우 review_stage_prs 데이터 생성 
-- 
CREATE OR REPLACE FUNCTION public.fn_initialize_review_stages()
 RETURNS trigger
AS $function$
BEGIN
    RAISE NOTICE 'Trigger started for PR ID: %, Action: %', NEW.pr_id, NEW.action;

    IF NEW.action = 'opened' THEN
        INSERT INTO review_stage_prs (
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
		RAISE NOTICE 'Insert to review_stage_prs successful';
    ELSE
        RAISE NOTICE 'Condition not met: action is not opened';
    END IF;
    
    RETURN NEW;
END;
$function$;

-- 트리거 생성 
CREATE TRIGGER tr_after_pr_opened
AFTER INSERT ON github_pr_events
FOR EACH ROW
EXECUTE FUNCTION fn_initialize_review_stages();


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




