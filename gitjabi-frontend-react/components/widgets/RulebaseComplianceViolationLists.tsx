import { CheckCircle2, XCircle, AlertCircle, Terminal } from "lucide-react";

export default function RulebaseScanList({ currentCR }) {
  // 스캔 데이터가 없을 경우 처리
  if (!currentCR?.rulebaseScan || currentCR.rulebaseScan.length === 0) {
    return (
      <div className="p-8 border-2 border-dashed border-gray-100 dark:border-gray-800 rounded-xl text-center text-gray-400 text-sm">
        진행된 거버넌스 스캔 내역이 없습니다.
      </div>
    );
  }

  return (
    <div className="space-y-3 mt-4">
      {currentCR.rulebaseScan.map((scan) => {
        // 모든 위반(violations)과 경고(warnings)를 하나의 리스트로 합쳐서 표시
        const allItems = [
          ...scan.violations.map(v => ({ ...v, type: 'VIOLATION' })),
          ...scan.warnings.map(w => ({ ...w, type: 'WARNING' }))
        ];

        return (
          <div key={scan.run_id} className="space-y-2">
            {/* 스캔 헤더 정보 (선택 사항: run_id와 시간을 작게 표시) */}
            <div className="flex items-center justify-between px-1">
              <div className="flex items-center gap-2 text-[10px] font-bold text-gray-400 uppercase tracking-tight">
                <Terminal size={12} /> {scan.run_id}
              </div>
              <span className="text-[10px] text-gray-400">{scan.executed_at}</span>
            </div>

            {/* 항목 루프 */}
            {allItems.map((item, idx) => (
              <div 
                key={`${scan.run_id}-${idx}`} 
                className="p-4 rounded-xl border border-gray-100 dark:border-gray-800 flex items-center justify-between group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors bg-white dark:bg-transparent"
              >
                <div className="flex items-center gap-4">
                  {/* 상태별 아이콘 박스 (VIOLATION: Red, WARNING: Orange) */}
                  <div className={`p-2 rounded-lg ${
                    item.type === 'VIOLATION' 
                      ? 'bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400' 
                      : 'bg-orange-50 text-orange-600 dark:bg-orange-900/20 dark:text-orange-400'
                  }`}>
                    {item.type === 'VIOLATION' ? <XCircle size={18}/> : <AlertCircle size={18}/>}
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-bold text-gray-800 dark:text-gray-200">
                        {item.rule}
                      </p>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-black ${
                        item.type === 'VIOLATION' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'
                      }`}>
                        {item.status}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {item.message}
                    </p>
                  </div>
                </div>

                {/* 우측 상단 스타일의 Severity 라벨 */}
                <div className="flex flex-col items-end gap-1">
                  <span className="text-[10px] font-mono font-bold text-gray-400 uppercase group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors">
                    {scan.severity}
                  </span>
                </div>
              </div>
            ))}

            {/* 모든 항목이 Pass일 경우 표시 */}
            {allItems.length === 0 && scan.pass && (
              <div className="p-4 rounded-xl border border-gray-100 dark:border-gray-800 flex items-center gap-4 bg-white dark:bg-transparent">
                <div className="p-2 rounded-lg bg-green-50 text-green-600 dark:bg-green-900/20 dark:text-green-400">
                  <CheckCircle2 size={18}/>
                </div>
                <div>
                  <p className="text-sm font-bold text-gray-800 dark:text-gray-200">모든 규칙 준수</p>
                  <p className="text-xs text-gray-500">지정된 룰베이스의 모든 검사를 통과했습니다.</p>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}