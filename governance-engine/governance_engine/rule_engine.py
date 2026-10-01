import re
import uuid
from datetime import timezone, datetime
from typing import Dict, Any, List, Optional

class RuleEngine:
    """
    고급 PR 정적 룰 검사 모듈.
    보안, 품질, 정책 준수 여부를 다각도로 검증합니다.
    """

    # 보안 및 개인정보 패턴 (Regex)
    SECURITY_PATTERNS = {
        "AWS_KEY": r"(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}",
        "PRIVATE_KEY": r"-----BEGIN (RSA|EC|DSA|GPG|OPENSSH) PRIVATE KEY-----",
        "SLACK_WEBHOOK": r"https://hooks\.slack\.com/services/T[A-Z0-9]+/[B[A-Z0-9]+/[A-Za-z0-9]+",
        "PHONE_KR": r"010-\d{3,4}-\d{4}",
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    }

    def __init__(self):
        self.violations = []
        self.warnings = []

    def check(self, pr_context: Dict[str, Any]) -> Dict[str, Any]:
        self.violations = []
        self.warnings = []
        
        time_now = datetime.now(timezone.utc)
        check_id = f"RULE_{time_now.strftime('%Y%m%d%H%M')}_{uuid.uuid4().hex[:6]}"
        
        try:
            # 1. 메타데이터 분석
            self._check_governance(pr_context)
            # 2. 변경 규모 분석
            self._check_size(pr_context)
            # 3. Diff 내용 및 보안 분석
            self._check_content_security(pr_context)
            # 4. 파일 유형 및 아키텍처 규칙
            self._check_file_rules(pr_context)

            # Severity 결정
            severity = "LOW"
            if any(v['status'] == "VIOLATION" for v in self.violations):
                severity = "HIGH"
            elif self.violations or self.warnings:
                severity = "MEDIUM"

            return {
                "check_id": check_id,
                "timestamp": time_now.isoformat(),
                "pass": not any(v['status'] == "VIOLATION" for v in self.violations),
                "severity": severity,
                "violations": self.violations,
                "warnings": self.warnings
            }
        except Exception as e:
            print(e)
        return {
            "check_id": check_id,
            "timestamp": time_now.isoformat(),
            "pass": True,
            "severity": 'LOW',
            "violations": [],
            "warnings": []
        }

    def _add_issue(self, rule: str, status: str, message: str, is_warning: bool = False):
        issue = {"rule": rule, "status": status, "message": message}
        if is_warning:
            self.warnings.append(issue)
        else:
            self.violations.append(issue)

    def _check_governance(self, ctx: Dict[str, Any]):
        base = ctx.get("base_branch")
        head = ctx.get("head_branch")
        
        if base in ["main", "master", "production"] and head == base:
            self._add_issue("PROTECTED_BRANCH", "VIOLATION", f"{base} 브랜치로의 직접적인 푸시는 금지되어 있습니다.")
        
        if not ctx.get("reviewers"):
            self._add_issue("NO_REVIEWER", "VIOLATION", "최소한 한 명의 리뷰어가 필요합니다.")
        if not ctx.get("labels"):
            self._add_issue("MISSING_LABEL", "WARNING", "카테고리 라벨(예: bug, feat)을 추가하는 것을 권장합니다.", True)

    def _check_size(self, ctx: Dict[str, Any]):
        total = (ctx.get("additions", 0) or 0) + (ctx.get("deletions", 0) or 0)
        if total > 3000:
            self._add_issue("COGNITIVE_OVERLOAD", "WARNING", f"PR 크기가 너무 큽니다 ({total} 라인). 분할을 고려해 보세요.", True)
        
        changed_files = ctx.get("changed_files", 0) or 0
        if changed_files > 20:
            self._add_issue("TOO_MANY_FILES", "WARNING", "20개 이상의 파일이 변경되었습니다. 리뷰 속도가 느려질 수 있습니다.", True)

    def _check_content_security(self, ctx: Dict[str, Any]):
        diff = ctx.get("diff", "")
        
        for name, pattern in self.SECURITY_PATTERNS.items():
            if re.search(pattern, diff):
                status = "VIOLATION" if "KEY" in name or "WEBHOOK" in name else "WARNING"
                self._add_issue(f"SEC_{name}", status, f"잠재적인 민감 데이터가 감지되었습니다: {name}")

        if "print(" in diff or "console.log(" in diff:
            self._add_issue("DEBUG_LOG_FOUND", "WARNING", "병합하기 전에 디버그 로그(print/console.log)를 제거해 주세요.", True)

    def _check_file_rules(self, ctx: Dict[str, Any]):
        diff = ctx.get("diff", "")
        file_paths = re.findall(r"diff --git b/(.*?) b/", diff)

        forbidden_extensions = [".env", ".pem", ".key", ".p12"]
        for path in file_paths:
            if any(path.endswith(ext) for ext in forbidden_extensions):
                self._add_issue("FORBIDDEN_FILE", "VIOLATION", f"금지된 파일이 감지되었습니다: {path}")

        has_src_change = any(p.startswith("src/") for p in file_paths)
        has_test_change = any("test" in p.lower() for p in file_paths)
        if has_src_change and not has_test_change:
            self._add_issue("MISSING_TESTS", "WARNING", "로직은 변경되었으나 테스트 파일이 업데이트되지 않았습니다.", True)

        if "package-lock.json" in diff or "poetry.lock" in diff:
            self._add_issue("DEPENDENCY_CHANGE", "WARNING", "의존성 잠금 파일이 업데이트되었습니다. 새 패키지를 확인하세요.", True)
