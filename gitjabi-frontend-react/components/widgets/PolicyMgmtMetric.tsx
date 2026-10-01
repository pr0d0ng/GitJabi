import React, { useState, useEffect } from 'react';
import { FileText, Activity, Clock, ArrowUp, AlertCircle, CheckCircle2, ArrowRight, Sparkles } from 'lucide-react';


export default function PolicyManagementMetric( {policies} ) {
    const totalPolicies = policies.length;
    
    // 상태별 개수 계산 (status 필드 기준)
    // const activeCount = policies.filter(p => p.status === 'ACTIVE').length;
    // const proposedCount = policies.filter(p => p.status === 'PROPOSED').length;
    const activeCount = policies.filter(p => p.status === 'PROPOSED').length;
    const proposedCount = policies.filter(p => p.status === 'ACTIVE').length;
    //
    //
    // 개발 테스트에서는 Active 와 Proposed 반전 하기로 함
    //
    //
    // 위험도별 분포 (risk_level 필드 기준)
    const criticalCount = policies.filter(p => p.risk_level === 'CRITICAL').length;
    
    // 활성화 비율 계산 (0으로 나누기 방지 포함)
    const activationRate = totalPolicies > 0 ? Math.round((activeCount / totalPolicies) * 100) : 0;

    const typeCounts = policies.reduce((acc, curr) => {
        acc[curr.type] = (acc[curr.type] || 0) + 1;
        return acc;
    }, {});

    // 3. 가장 높은 비중을 차지하는 타입 찾기
    const topTypeEntry = Object.entries(typeCounts).sort((a, b) => b[1] - a[1])[0];
    const topTypeName = topTypeEntry ? topTypeEntry[0] : 'N/A';
    const topTypeCount = topTypeEntry ? topTypeEntry[1] : 0;

    // 타입 이름을 한글로 매핑
    const typeMap = {
        'SECURITY': '보안',
        'GOVERNANCE': '거버넌스',
        'STANDARD': '기술 표준',
        'INFRA': '인프라 설정',
        'N/A': 'N/A'
    };

    return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        {/* 1. 전체 정책 및 활성화 현황 */}
        <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 flex items-center justify-between relative overflow-hidden group">
            <div className="z-10 relative">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">전체 정책 (현재 페이지)</p>
            <div className="mt-2 flex items-baseline gap-2">
                <span className="text-4xl font-bold text-gray-900 dark:text-white">{totalPolicies}</span>
                <span className="text-sm font-medium text-emerald-500 flex items-center gap-0.5">
                <CheckCircle2 size={16} /> {activeCount} 활성
                </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">현재 {activationRate}% 가동 중</p>
            </div>
            <div className="relative w-20 h-20">
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path className="text-gray-100 dark:text-gray-700" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeWidth="3"></path>
                <path className="text-primary" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="currentColor" strokeDasharray={`${activationRate}, 100`} strokeWidth="3"></path>
            </svg>
            <div className="absolute inset-0 flex items-center justify-center text-primary font-bold text-xs">
                {activationRate}%
            </div>
            </div>
        </div>

        {/* 2. 위험 정책 및 제안된 정책 현황 */}
        <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 relative overflow-hidden group">
            <div className="z-10 relative">
            <p className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">검토 및 위험 항목</p>
            <div className="mt-2 flex items-baseline gap-2">
                <span className="text-4xl font-bold text-gray-900 dark:text-white">{proposedCount}</span>
                <span className="px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-xs font-medium border border-red-200 dark:border-red-800">
                Critical {criticalCount}
                </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">검토 대기 상태의 신규 정책들</p>
            </div>
            <div className="absolute right-4 top-4 bg-amber-50 dark:bg-amber-900/10 p-2 rounded-lg">
            <AlertCircle className="text-amber-500" size={24} />
            </div>
        </div>

        {/* 3. 도메인별 요약 정보 */}
        <div className="bg-gradient-to-br from-white to-primary/5 dark:from-card-dark dark:to-primary/10 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700 relative overflow-hidden">
            <div className="flex items-center gap-2 mb-3">
                <Sparkles className="text-primary" size={20} />
                <h3 className="font-bold text-gray-800 dark:text-white text-sm uppercase tracking-wider">메트릭 요약</h3>
            </div>
            <div className="space-y-1">
                <p className="text-sm text-gray-600 dark:text-gray-300">
                {topTypeCount > 0 ? (
                    <>
                    <span className="font-semibold text-primary">{typeMap[topTypeName.toUpperCase()] || topTypeName}</span> 정책이 
                    <strong className="text-primary ml-1">{topTypeCount}개</strong>로 가장 높은 비중을 차지합니다.
                    </>
                ) : (
                    "분석할 정책 데이터가 없습니다."
                )}
                </p>
                
                <div className="mt-3 flex gap-4">
                    <div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-tight">보안 정책</p>
                        <p className="text-sm font-bold text-gray-700 dark:text-gray-200">
                        {policies.filter(p => p.type.toUpperCase() === 'SECURITY').length}
                        </p>
                    </div>
                    <div className="w-px h-6 bg-gray-200 dark:bg-gray-700"></div>
                    <div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-tight">거버넌스</p>
                        <p className="text-sm font-bold text-gray-700 dark:text-gray-200">
                        {policies.filter(p => p.type.toUpperCase() === 'GOVERNANCE').length}
                        </p>
                    </div>
                    <div className="w-px h-6 bg-gray-200 dark:bg-gray-700"></div>
                    <div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-tight">표준 정책</p>
                        <p className="text-sm font-bold text-gray-700 dark:text-gray-200">
                        {policies.filter(p => p.type.toUpperCase() === 'STANDARD').length}
                        </p>
                    </div>
                    <div className="w-px h-6 bg-gray-200 dark:bg-gray-700"></div>
                    <div>
                        <p className="text-[10px] text-gray-400 uppercase tracking-tight">설계 정책</p>
                        <p className="text-sm font-bold text-gray-700 dark:text-gray-200">
                        {policies.filter(p => p.type.toUpperCase() === 'DESIGN').length}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    </div>
    );

};