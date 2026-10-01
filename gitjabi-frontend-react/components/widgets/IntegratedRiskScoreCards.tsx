import React from 'react';
import { 
  Activity, Hourglass, Target, Cpu, GitPullRequest, 
  ShieldAlert, TrendingDown, AlertTriangle 
} from "lucide-react";

// 내부용 간이 CircularProgress (없을 경우를 대비)
const InternalProgress = ({ percentage, color }) => {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percentage / 100) * circumference;
  return (
    <svg className="transform -rotate-90 w-16 h-16">
      <circle cx="32" cy="32" r={radius} stroke="currentColor" strokeWidth="4" fill="transparent" className="text-gray-200 dark:text-gray-800" />
      <circle cx="32" cy="32" r={radius} stroke={color} strokeWidth="4" fill="transparent"
        strokeDasharray={circumference} strokeDashoffset={offset} strokeLinecap="round" className="transition-all duration-500" />
    </svg>
  );
};

export default function IntegratedRiskScoreCard({ riskScore, riskFactors }) {
  const getRiskColor = (score) => {
    if (!score) return '#cbd5e1';
    if (score >= 80) return '#ef4444';
    if (score >= 60) return '#f97316';
    return '#27F5A3';
  };

  const IconMap = { Target, Cpu, GitPullRequest, ShieldAlert };

  return (
    <div className="bg-white dark:bg-gray-900/30 border border-gray-100 dark:border-gray-800 rounded-3xl p-8 shadow-sm space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-8 border-b border-gray-100 dark:border-gray-800/50">
        <div className="flex items-center gap-6">
          <div className="relative">
            <div className="h-16 w-16">
              <InternalProgress percentage={riskScore ?? 0} color={getRiskColor(riskScore)} />
            </div>
            <div className="absolute inset-0 flex items-center justify-center">
              {!riskScore ? <Hourglass size={20} className="text-gray-400 animate-pulse" /> 
                         : <span className="text-2xl font-black text-gray-900 dark:text-white">{riskScore}</span>}
            </div>
          </div>
          <div>
            <h4 className="text-lg font-bold text-gray-900 dark:text-white">통합 리스크 지수</h4>
            <p className="text-xs text-gray-500 font-medium max-w-sm">
              {!riskScore ? "현재 변경 사항에 대한 시스템 영향도 및 사고 예측률을 분석 중입니다." 
                          : "코드 복잡도, 모듈 장애 이력, 정책 위반을 종합한 정량 지표입니다."}
            </p>
          </div>
        </div>

        <div className={`shrink-0 px-6 py-3 rounded-2xl border-2 text-sm font-black uppercase tracking-widest flex items-center gap-2 ${
          !riskScore ? 'border-gray-300/50 text-gray-500' 
                     : riskScore >= 80 ? 'border-red-500/30 bg-red-50/10 text-red-600'
                     : riskScore >= 60 ? 'border-orange-500/30 bg-orange-50/10 text-orange-600'
                     : 'border-emerald-500/30 bg-emerald-50/10 text-emerald-600'
        }`}>
          <Activity size={18} className={!riskScore ? "animate-pulse" : ""} />
          {!riskScore ? '분석 대기 중...' : riskScore >= 80 ? '위험도 매우 높음' : riskScore >= 60 ? '위험도 높음' : '위험도 보통'}
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {riskFactors && riskFactors.length > 0 ? (
          riskFactors.map((factor) => {
            if (!factor || factor === 'null') return null;
            
            const Icon = IconMap[factor.icon] || AlertTriangle;
            const colorClass = {
              blue: "text-blue-500 bg-blue-50 dark:bg-blue-900/20",
              purple: "text-purple-500 bg-purple-50 dark:bg-purple-900/20",
              orange: "text-orange-500 bg-orange-50 dark:bg-orange-900/20",
              teal: "text-teal-500 bg-teal-50 dark:bg-teal-900/20",
            }[factor.color] || "text-gray-500 bg-gray-50";

            return (
              <div key={factor.id} className="p-5 rounded-2xl bg-gray-50/50 dark:bg-gray-800/30 border border-gray-100 dark:border-gray-800 transition-all hover:shadow-md">
                <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300 font-bold text-sm mb-3">
                  <div className={`p-1.5 rounded-lg ${colorClass}`}><Icon size={14} /></div>
                  {factor.title}
                </div>
                <div className="text-lg font-black text-gray-900 dark:text-white mb-1 flex items-baseline gap-2">
                  {factor.value}
                  {factor.subValue && <span className="text-[10px] text-red-500 flex items-center animate-pulse"><TrendingDown size={12}/> {factor.subValue}</span>}
                </div>
                <p className="text-xs text-gray-500 leading-relaxed">{factor.description}</p>
              </div>
            );
          })
        ) : (
            /* 2. riskFactors 데이터가 없거나 분석 중일 때 (Empty State) */
        //   <div className="col-span-full py-12 flex flex-col items-center justify-center border-2 border-dashed border-gray-100 dark:border-gray-800 rounded-3xl">
        //     <Cpu size={32} className="text-gray-300 animate-spin-slow mb-4" />
        //     <h4 className="text-sm font-bold text-gray-500">평가 요소 분석 대기 중..</h4>
        //   </div>
            <div className="col-span-full py-12 flex flex-col items-center justify-center border-2 border-dashed border-gray-100 dark:border-gray-800 rounded-3xl bg-gray-50/30 dark:bg-gray-900/10">
            <div className="relative mb-4">
                <div className="absolute inset-0 bg-primary/20 blur-xl rounded-full animate-pulse"></div>
                <div className="relative p-4 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                <Cpu size={32} className="text-gray-300 animate-spin-slow" />
                </div>
            </div>
            <h4 className="text-sm font-bold text-gray-500 dark:text-gray-400">평가 요소 분석 대기 중..</h4>
            <p className="text-[11px] text-gray-400 mt-1 max-w-[240px] text-center leading-relaxed">
                시스템이 CR 데이터를 기반으로 <br/>
                영향도 및 사고 위험을 산출하고 있습니다.
            </p>

            {/* 단순 스켈레톤 레이아웃 (선택사항) */}
            <div className="mt-8 flex gap-2">
                <div className="w-12 h-1.5 rounded-full bg-gray-200 dark:bg-gray-800 animate-pulse"></div>
                <div className="w-8 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 animate-pulse delay-75"></div>
                <div className="w-10 h-1.5 rounded-full bg-gray-100 dark:bg-gray-800 animate-pulse delay-150"></div>
            </div>
            </div>
        )}
      </div>
    </div>
  );
}