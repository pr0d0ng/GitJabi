-- DROP SCHEMA public;

CREATE SCHEMA public AUTHORIZATION azure_pg_admin;

COMMENT ON SCHEMA public IS 'standard public schema';

-- DROP TYPE public."ai_analysis_result";

CREATE TYPE public."ai_analysis_result" AS ENUM (
	'PENDING',
	'IN_PROGRESS',
	'PASSED',
	'WARNING',
	'VIOLATED');

-- DROP TYPE public."audit_category";

CREATE TYPE public."audit_category" AS ENUM (
	'No Category',
	'System',
	'GitHub',
	'Teams');

-- DROP TYPE public."audit_status";

CREATE TYPE public."audit_status" AS ENUM (
	'Success',
	'Info',
	'Warning',
	'Failure');

-- DROP TYPE public."domain_type";

CREATE TYPE public."domain_type" AS ENUM (
	'infra',
	'backend',
	'frontend',
	'cloud',
	'others');

-- DROP TYPE public."policy_status";

CREATE TYPE public."policy_status" AS ENUM (
	'PROPOSED',
	'ACTIVE');

-- DROP TYPE public."policy_type";

CREATE TYPE public."policy_type" AS ENUM (
	'security',
	'design',
	'quality',
	'standard',
	'audit',
	'governance');

-- DROP TYPE public."priority_level";

CREATE TYPE public."priority_level" AS ENUM (
	'CRITICAL',
	'HIGH',
	'MEDIUM',
	'LOW');

-- DROP TYPE public."review_stage_status";

CREATE TYPE public."review_stage_status" AS ENUM (
	'PENDING',
	'IN_PROGRESS',
	'APPROVED',
	'REJECTED',
	'SKIPPED');

-- DROP TYPE public."rule_severity";

CREATE TYPE public."rule_severity" AS ENUM (
	'BLOCK',
	'WARNING',
	'INFO');

-- DROP TYPE public."rule_trigger_stage";

CREATE TYPE public."rule_trigger_stage" AS ENUM (
	'PRE_COMMIT',
	'PR_OPENED',
	'PR_SYNCHRONIZED',
	'MANUAL');

-- DROP TYPE public."user_role";

CREATE TYPE public."user_role" AS ENUM (
	'user',
	'admin',
	'collaborator');

-- DROP SEQUENCE public.audit_logs_id_seq;

CREATE SEQUENCE public.audit_logs_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.compliance_policies_id_seq;

CREATE SEQUENCE public.compliance_policies_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.github_pr_events_id_seq;

CREATE SEQUENCE public.github_pr_events_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.groups_id_seq;

CREATE SEQUENCE public.groups_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.organizations_id_seq;

CREATE SEQUENCE public.organizations_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.push_events_id_seq;

CREATE SEQUENCE public.push_events_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.review_stage_prs_id_seq;

CREATE SEQUENCE public.review_stage_prs_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.rulebase_policies_id_seq;

CREATE SEQUENCE public.rulebase_policies_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.users_id_seq;

CREATE SEQUENCE public.users_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;-- public.audit_logs definition

-- Drop table

-- DROP TABLE public.audit_logs;

CREATE TABLE public.audit_logs (
	id serial4 NOT NULL,
	"timestamp" timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	actor_name varchar(100) NULL,
	actor_role varchar(100) NULL,
	category public."audit_category" DEFAULT 'No Category'::audit_category NULL,
	action_detail text NOT NULL,
	status public."audit_status" DEFAULT 'Success'::audit_status NULL,
	metadata jsonb NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT audit_logs_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_audit_logs_timestamp ON public.audit_logs USING btree ("timestamp" DESC);


-- public.github_pr_events definition

-- Drop table

-- DROP TABLE public.github_pr_events;

CREATE TABLE public.github_pr_events (
	pr_id int8 NOT NULL,
	pr_number int8 NULL,
	repo_id int8 NULL,
	repo_name varchar(512) NULL,
	"action" varchar(52) NULL,
	event_performer varchar(100) NULL,
	event_performer_type varchar(52) NULL,
	pr_title text NULL,
	pr_author varchar(256) NULL,
	pr_state varchar(52) NULL,
	pr_body text NULL,
	head_ref varchar(255) NULL,
	head_sha varchar(100) NULL,
	base_ref varchar(255) NULL,
	pr_created_at timestamptz NULL,
	pr_closed_at timestamptz NULL,
	pr_merged_at timestamptz NULL,
	pr_additions int8 NULL,
	pr_deletions int8 NULL,
	assignee_count int8 NULL,
	reviewers_list varchar NULL,
	labels_list varchar NULL,
	pr_diff_url text NULL,
	pr_patch_url text NULL,
	pr_html_url text NULL,
	repo_url text NULL,
	repo_language varchar(128) NULL,
	repo_description text NULL,
	inserted_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	id serial4 NOT NULL,
	CONSTRAINT github_pr_events_pkey PRIMARY KEY (id)
);
CREATE INDEX idx_pr_action ON public.github_pr_events USING btree (action);
CREATE INDEX idx_pr_author ON public.github_pr_events USING btree (pr_author);
CREATE INDEX idx_pr_events_pr_id ON public.github_pr_events USING btree (pr_id);
CREATE INDEX idx_pr_repo_name ON public.github_pr_events USING btree (repo_name);

-- Table Triggers

create trigger tr_after_pr_opened after
insert
    on
    public.github_pr_events for each row execute function fn_initialize_review_stages();


-- public.organizations definition

-- Drop table

-- DROP TABLE public.organizations;

CREATE TABLE public.organizations (
	id serial4 NOT NULL,
	org_id int4 NOT NULL,
	org_name varchar(1028) NOT NULL,
	description text NULL,
	CONSTRAINT organizations_pkey PRIMARY KEY (id),
	CONSTRAINT organizations_unique UNIQUE (org_id)
);


-- public.push_events definition

-- Drop table

-- DROP TABLE public.push_events;

CREATE TABLE public.push_events (
	id serial4 NOT NULL,
	pushed_at timestamp NOT NULL,
	repo_id int8 NOT NULL,
	repo_name varchar(255) NOT NULL,
	repo_description text NULL,
	repo_language varchar(50) NULL,
	"ref" varchar(255) NULL,
	pusher_name varchar(100) NULL,
	commit_count int8 DEFAULT 0 NULL,
	file_added int8 DEFAULT 0 NULL,
	file_modified int8 DEFAULT 0 NULL,
	head_commit_msg text NULL,
	compare_url text NULL,
	created_at timestamp DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT push_events_pkey PRIMARY KEY (id)
);


-- public.rulebase_policies definition

-- Drop table

-- DROP TABLE public.rulebase_policies;

CREATE TABLE public.rulebase_policies (
	id serial4 NOT NULL,
	rule_id varchar(50) NOT NULL, -- 규칙 ID
	rule_name varchar(255) NOT NULL, -- 규칙 제목
	target_file_pattern varchar(255) NULL, -- 대상되는 파일 패턴   (예: "*.py", "src/**")
	rule_logic_type varchar(255) NULL, -- 로직 종류 (예: 'REGEX', 'AST_PARSER', 'API_SPEC')
	rule_logic_content text NOT NULL, -- 실제 검사 코드나 정규표현식 패턴
	trigger_stage public."rule_trigger_stage" DEFAULT 'PR_OPENED'::rule_trigger_stage NULL,
	severity public."rule_severity" DEFAULT 'WARNING'::rule_severity NULL, -- 위반 시 PR을 막을지(BLOCK) 경고만 줄지
	is_enabled bool DEFAULT true NULL, -- 규칙 활성화 여부
	error_message text NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	updated_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT rulebase_policies_pkey PRIMARY KEY (id),
	CONSTRAINT rulebase_policies_rule_id_key UNIQUE (rule_id)
);
COMMENT ON TABLE public.rulebase_policies IS '룰베이스 기반 정책에 대한 별도의 테이블.';

-- Column comments

COMMENT ON COLUMN public.rulebase_policies.rule_id IS '규칙 ID';
COMMENT ON COLUMN public.rulebase_policies.rule_name IS '규칙 제목';
COMMENT ON COLUMN public.rulebase_policies.target_file_pattern IS '대상되는 파일 패턴   (예: "*.py", "src/**")';
COMMENT ON COLUMN public.rulebase_policies.rule_logic_type IS '로직 종류 (예: ''REGEX'', ''AST_PARSER'', ''API_SPEC'')';
COMMENT ON COLUMN public.rulebase_policies.rule_logic_content IS '실제 검사 코드나 정규표현식 패턴';
COMMENT ON COLUMN public.rulebase_policies.severity IS '위반 시 PR을 막을지(BLOCK) 경고만 줄지';
COMMENT ON COLUMN public.rulebase_policies.is_enabled IS '규칙 활성화 여부';

-- Table Triggers

create trigger update_rulebase_policies_modtime before
update
    on
    public.rulebase_policies for each row execute function update_updated_at_column();


-- public."groups" definition

-- Drop table

-- DROP TABLE public."groups";

CREATE TABLE public."groups" (
	id serial4 NOT NULL,
	group_name varchar(512) NOT NULL,
	description text NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	organization_id int4 NULL,
	CONSTRAINT groups_pkey PRIMARY KEY (id),
	CONSTRAINT fk_organization_id_group FOREIGN KEY (organization_id) REFERENCES public.organizations(org_id) ON DELETE CASCADE
);


-- public.review_stage_prs definition

-- Drop table

-- DROP TABLE public.review_stage_prs;

CREATE TABLE public.review_stage_prs (
	id serial4 NOT NULL,
	event_root_id int8 NOT NULL, -- 최초 이벤트 ID (github_pr_events 테이블과 FK)
	pr_id int8 NOT NULL, -- 풀리퀘스트 고유 ID
	status public."review_stage_status" DEFAULT 'PENDING'::review_stage_status NULL, -- 리뷰 상태 표시 
	reviewer_group_id int4 DEFAULT 1 NULL, -- 해당 리뷰 단계를 담당하는 권한 그룹 ID
	reviewer_comment text NULL, -- 리뷰어 코멘트  
	is_mandatory bool DEFAULT true NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	closed_at timestamptz NULL,
	pr_number int8 NOT NULL, -- 개별 레포지터리의 PR 넘버
	repo_id int8 NOT NULL, -- 레포지터리 ID
	repo_name varchar(512) NOT NULL, -- 레포지터리 이름
	"ai_analysis_result" public."ai_analysis_result" DEFAULT 'PENDING'::ai_analysis_result NOT NULL, -- AI 분석 결과 상태
	CONSTRAINT review_stage_prs_pkey PRIMARY KEY (id),
	CONSTRAINT fk_review_stage_group FOREIGN KEY (reviewer_group_id) REFERENCES public."groups"(id) ON DELETE SET NULL,
	CONSTRAINT fk_review_stage_pr FOREIGN KEY (event_root_id) REFERENCES public.github_pr_events(id) ON DELETE CASCADE
);

-- Column comments

COMMENT ON COLUMN public.review_stage_prs.event_root_id IS '최초 이벤트 ID (github_pr_events 테이블과 FK)';
COMMENT ON COLUMN public.review_stage_prs.pr_id IS '풀리퀘스트 고유 ID';
COMMENT ON COLUMN public.review_stage_prs.status IS '리뷰 상태 표시 ';
COMMENT ON COLUMN public.review_stage_prs.reviewer_group_id IS '해당 리뷰 단계를 담당하는 권한 그룹 ID';
COMMENT ON COLUMN public.review_stage_prs.reviewer_comment IS '리뷰어 코멘트  ';
COMMENT ON COLUMN public.review_stage_prs.pr_number IS '개별 레포지터리의 PR 넘버';
COMMENT ON COLUMN public.review_stage_prs.repo_id IS '레포지터리 ID';
COMMENT ON COLUMN public.review_stage_prs.repo_name IS '레포지터리 이름';
COMMENT ON COLUMN public.review_stage_prs."ai_analysis_result" IS 'AI 분석 결과 상태';

-- Foreign key comments

COMMENT ON CONSTRAINT fk_review_stage_group ON public.review_stage_prs IS '리뷰 단계 담당 그룹은 groups 테이블을 참조함';


-- public.users definition

-- Drop table

-- DROP TABLE public.users;

CREATE TABLE public.users (
	id serial4 NOT NULL,
	username varchar(100) NOT NULL,
	email varchar(255) NOT NULL,
	full_name varchar(100) NULL,
	group_id int4 NULL,
	is_active bool DEFAULT true NULL,
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	"password" varchar(255) NOT NULL,
	"role" public."user_role" DEFAULT 'user'::user_role NOT NULL, -- 사용자 권한 역할 - user, admin, collaborator
	"position" varchar(512) NULL, -- 사용자 직책 (eg. DevOps Leader)
	CONSTRAINT users_email_key UNIQUE (email),
	CONSTRAINT users_pkey PRIMARY KEY (id),
	CONSTRAINT users_username_key UNIQUE (username),
	CONSTRAINT users_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."groups"(id) ON DELETE SET NULL
);

-- Column comments

COMMENT ON COLUMN public.users."role" IS '사용자 권한 역할 - user, admin, collaborator';
COMMENT ON COLUMN public.users."position" IS '사용자 직책 (eg. DevOps Leader)';


-- public.compliance_policies definition

-- Drop table

-- DROP TABLE public.compliance_policies;

CREATE TABLE public.compliance_policies (
	id serial4 NOT NULL,
	policy_id varchar(128) NOT NULL, -- 정책 ID
	group_id int2 DEFAULT 0 NULL,
	"type" public."policy_type" NULL, -- 정책 유형 ENUM ('security', 'design', 'quality', 'standard', 'audit', 'governance')
	"domain" public."domain_type" NULL, -- 도메인 유형 ENUM ('infra', 'backend', 'frontend', 'cloud', 'others')
	risk_level public."priority_level" DEFAULT 'MEDIUM'::priority_level NULL, -- 우선순위 or 위험 레벨 ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')
	authority_group int4 NULL, -- 해당 정책 승인 및 관리 가능한 그룹 ID
	title text NOT NULL, -- 제목
	reason text NULL, -- 도입 배경 및 이유
	action_plan text NULL, -- 구체적인 정책 준수 방안
	description text NULL, -- 배경적인 설명 및 기타 설명
	tag _text NULL, -- 텍스트 태그 (python, fastapi 등)
	status public."policy_status" DEFAULT 'PROPOSED'::policy_status NULL, -- 상태 표시 'PROPOSED', 'ACTIVE'
	created_at timestamptz DEFAULT CURRENT_TIMESTAMP NULL,
	CONSTRAINT compliance_policies_pkey PRIMARY KEY (id),
	CONSTRAINT compliance_policies_policy_id_key UNIQUE (policy_id),
	CONSTRAINT compliance_policies_authority_group_fkey FOREIGN KEY (authority_group) REFERENCES public."groups"(id) ON DELETE SET NULL
);
CREATE INDEX idx_policies_authority_group ON public.compliance_policies USING btree (authority_group);
CREATE INDEX idx_policies_status ON public.compliance_policies USING btree (status);
COMMENT ON TABLE public.compliance_policies IS '컴플라이언스 정책 (추상적 정책)에 대한 테이블.';

-- Column comments

COMMENT ON COLUMN public.compliance_policies.policy_id IS '정책 ID';
COMMENT ON COLUMN public.compliance_policies."type" IS '정책 유형 ENUM (''security'', ''design'', ''quality'', ''standard'', ''audit'', ''governance'')';
COMMENT ON COLUMN public.compliance_policies."domain" IS '도메인 유형 ENUM (''infra'', ''backend'', ''frontend'', ''cloud'', ''others'')';
COMMENT ON COLUMN public.compliance_policies.risk_level IS '우선순위 or 위험 레벨 (''CRITICAL'', ''HIGH'', ''MEDIUM'', ''LOW'')';
COMMENT ON COLUMN public.compliance_policies.authority_group IS '해당 정책 승인 및 관리 가능한 그룹 ID';
COMMENT ON COLUMN public.compliance_policies.title IS '제목';
COMMENT ON COLUMN public.compliance_policies.reason IS '도입 배경 및 이유';
COMMENT ON COLUMN public.compliance_policies.action_plan IS '구체적인 정책 준수 방안';
COMMENT ON COLUMN public.compliance_policies.description IS '배경적인 설명 및 기타 설명';
COMMENT ON COLUMN public.compliance_policies.tag IS '텍스트 태그 (python, fastapi 등)';
COMMENT ON COLUMN public.compliance_policies.status IS '상태 표시 ''PROPOSED'', ''ACTIVE''';


-- public.v_pr_review_stats source

CREATE OR REPLACE VIEW public.v_pr_review_stats
AS WITH stats AS (
         SELECT count(*) AS total_count,
            count(*) FILTER (WHERE review_stage_prs.ai_analysis_result = 'VIOLATED'::ai_analysis_result) AS violated_count,
            count(*) FILTER (WHERE review_stage_prs.ai_analysis_result = 'PENDING'::ai_analysis_result) AS pending_count,
            count(*) FILTER (WHERE review_stage_prs.ai_analysis_result = 'PASSED'::ai_analysis_result) AS success_count
           FROM review_stage_prs
        )
 SELECT total_count,
    violated_count,
    pending_count,
    success_count,
    round(violated_count::numeric / NULLIF(total_count, 0)::numeric * 100::numeric, 2) AS violation_rate,
    round(success_count::numeric / NULLIF(total_count, 0)::numeric * 100::numeric, 2) AS success_rate
   FROM stats;



-- DROP FUNCTION public.fn_initialize_review_stages();

CREATE OR REPLACE FUNCTION public.fn_initialize_review_stages()
 RETURNS trigger
 LANGUAGE plpgsql
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
$function$
;

-- DROP FUNCTION public.update_updated_at_column();

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$function$
;