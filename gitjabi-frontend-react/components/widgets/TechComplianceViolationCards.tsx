import { Terminal, ShieldCheck, Fingerprint, Activity, CheckCircle2, AlertTriangle, ShieldAlert, Info, Clock } from "lucide-react";

// 상태별 스타일 및 아이콘 매핑
const JUDGMENT_CONFIG = {
  VIOLATION: {
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-50 dark:bg-red-900/20",
    border: "border-red-200 dark:border-red-500/30",
    accent: "bg-red-500",
    icon: <ShieldAlert size={18} />,
    label: "정책 위반"
  },
  ADVISORY_WARNING: {
    color: "text-orange-600 dark:text-orange-400",
    bg: "bg-orange-50 dark:bg-orange-900/20",
    border: "border-orange-200 dark:border-orange-500/30",
    accent: "bg-orange-500",
    icon: <AlertTriangle size={18} />,
    label: "권고 주의"
  },
  INSUFFICIENT_CONTEXT: {
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-50 dark:bg-blue-900/20",
    border: "border-blue-200 dark:border-blue-500/30",
    accent: "bg-blue-500",
    icon: <Info size={18} />,
    label: "판단 유보"
  },
  COMPLIANT: {
    color: "text-green-600 dark:text-green-400",
    bg: "bg-green-50 dark:bg-green-900/20",
    border: "border-green-200 dark:border-green-500/30",
    accent: "bg-green-500",
    icon: <CheckCircle2 size={18} />,
    label: "준수 완료"
  }
};

export default function TechComplianceViolationCards({ currentCR }) {
  const scans = currentCR?.technical?.gitjabiScan;

  console.log(scans);

  // 데이터가 없을 경우 처리
  if (!scans || scans.length === 0) {
    return (
      <div className="mt-6 p-10 border-2 border-dashed border-gray-200 dark:border-gray-800 rounded-2xl text-center">
        <p className="text-gray-500 dark:text-gray-400">검색된 컴플라이언스 위반 내역이 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 mt-6">
      {scans.map((scan) => (
        <div key={scan.scan_id || scan.run_id} className="space-y-4">
        {/* 스캔 요약 헤더 - 모던 스타일 */}
        <div className="relative flex flex-col md:flex-row md:items-center justify-between gap-3 px-1 pb-2 mb-2 border-b border-gray-100 dark:border-gray-800/60">
          
          <div className="flex items-center gap-3">
            {/* 아이콘: 박스 배경 대신 링(Ring) 스타일로 변경해 가벼운 느낌 부여 */}
            <div className="relative flex items-center justify-center w-9 h-9 rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm">
              <Activity size={16} className="text-blue-500 dark:text-blue-400" />
              <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-green-500 border-2 border-white dark:border-gray-900 rounded-full"></div>
            </div>

            <div className="flex flex-col">
              <h2 className="text-[15px] font-bold text-gray-900 dark:text-gray-100 tracking-tight flex items-center gap-2">
                {scan.title || "Untitled Scan Analysis"}
                <span className="px-1.5 py-0.5 rounded text-md bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-black uppercase tracking-tighter">
                  PR #{scan.pr_number}
                </span>
              </h2>
              
              <div className="flex items-center gap-3 mt-0.5">
                <div className="flex items-center gap-1.5 text-[11px] text-gray-500 dark:text-gray-400 font-medium">
                  <Clock size={13} className="opacity-70" />
                  {scan.executed_at}
                </div>
                <span className="w-1 h-1 rounded-full bg-gray-300 dark:bg-gray-600"></span>
                <div className="flex items-center gap-1.5 text-[11px] text-gray-400 dark:text-gray-500 italic">
                  by {currentCR.requesterName?.split(' ')[0] || "System"}
                </div>
              </div>
            </div>
          </div>

          {/* 오른쪽: ID 정보를 별도의 Badge 스타일로 분리하여 시각적 분산 방지 */}
          <div className="flex items-center self-end md:self-center">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-50/50 dark:bg-gray-800/40 border border-gray-100 dark:border-gray-700/50 group hover:border-blue-200 dark:hover:border-blue-900/50 transition-colors">
              <Fingerprint size={12} className="text-gray-400 group-hover:text-blue-500 transition-colors" />
              <span className="text-[10px] font-mono font-bold text-gray-500 dark:text-gray-400 tracking-tight">
                {scan.run_id}
              </span>
            </div>
          </div>
        </div>

          {/* 개별 위반 내역 루프 */}
          <div className="grid gap-4">
            {scan.violations && scan.violations.length > 0 ? (
              scan.violations?.map((violation, idx) => {
                const judgment = violation.output?.judgment_result || "INSUFFICIENT_CONTEXT";
                const config = JUDGMENT_CONFIG[judgment];
                const severity = violation.output?.severity?.toUpperCase() || "LOW";

              return (
                <div
                  key={`${scan.run_id}-${idx}`}
                  className={`relative rounded-xl border ${config.border} ${config.bg} overflow-hidden transition-all hover:shadow-md`}
                >
                  <div className="p-5 flex flex-col md:flex-row gap-5">
                    {/* 왼쪽 섹션: 상태 및 정책 내용 */}
                    <div className="flex-1 space-y-3">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-black text-white ${config.accent}`}>
                          {judgment}
                        </span>
                        <span className="text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Severity: {severity}
                        </span>
                      </div>

                      <div>
                        <h4 className="font-bold text-gray-900 dark:text-white flex items-center gap-2">
                          <span className={config.color}>{config.icon}</span>
                          {violation.related_policy}
                        </h4>
                        <div className="mt-2 text-sm text-gray-700 dark:text-gray-300 bg-white/50 dark:bg-black/20 p-3 rounded-lg border border-white/50 dark:border-white/5">
                          <p className="font-semibold text-xs mb-1 text-gray-500">AI 분석 결과:</p>
                          {violation.output?.analysis?.step_1_context || "상세 분석 내용이 없습니다."}
                        </div>
                      </div>
                    </div>

                    {/* 오른쪽 섹션: 판단 근거 및 Action */}
                    <div className="md:w-80 flex flex-col gap-3">
                      <div className="flex-1 bg-white/60 dark:bg-gray-900/40 rounded-lg p-4 border border-white/40 dark:border-white/5">
                        <p className="text-[11px] font-bold text-gray-500 uppercase mb-2">판단 근거 (Reason)</p>
                        <p className="text-xs leading-relaxed text-gray-800 dark:text-gray-200">
                          {violation.output?.reason || "근거 정보 부족"}
                        </p>
                      </div>
                      
                      <div className={`p-3 rounded-lg flex items-center gap-3 ${config.accent} text-white`}>
                        <CheckCircle2 size={18} className="shrink-0" />
                        <div className="text-[11px] leading-tight font-medium">
                          <strong>조치 필요:</strong> 해당 정책 위반 여부를 검토하고 코드를 수정하거나 사유를 등록하세요.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          ) : (
            /* 위반 사항이 없을 때 표시 */
            <div className={`flex items-center gap-3 p-3 rounded-xl border shadow-sm ${JUDGMENT_CONFIG.COMPLIANT.border} ${JUDGMENT_CONFIG.COMPLIANT.bg} transition-all`}>
              <div className={`flex-none w-8 h-8 rounded-full ${JUDGMENT_CONFIG.COMPLIANT.accent} flex items-center justify-center text-white`}>
                <ShieldCheck size={16} />
              </div>
              <div>
                <h4 className={`text-[15px] font-bold leading-none ${JUDGMENT_CONFIG.COMPLIANT.color}`}>
                  정책 준수 완료
                </h4>
                <p className="text-xs leading-tight text-gray-600 dark:text-gray-400 mt-1.5">
                  해당 PR에 대한 컴플라이언스 분석 결과, 발견된 보안 및 기술 정책 위반 사항을 발견하지 못했습니다.
                  <br className="md:hidden" /> 
                  <span className="md:ml-1">자세한 시스템 판단 로그는 Github 페이지에서 확인할 수 있습니다.</span>
                </p>
              </div>
            </div>
          )}
          </div>
        </div>
      ))}
    </div>
  );
}