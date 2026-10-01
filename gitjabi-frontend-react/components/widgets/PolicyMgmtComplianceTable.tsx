import React, { useState, useEffect } from 'react';
import { ChevronLeft, ChevronRight, Search, Filter, ListFilter, MoreHorizontal } from 'lucide-react';

// 2. UI 스타일 매핑 헬퍼 함수
// 'security', 'design', 'quality', 'standard', 'audit', 'governance'
const getTypeStyle = (type) => {
  const styles = {
    security: { label: '보안', classes: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800' },
    design: { label: '설계', classes: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 border-purple-200 dark:border-purple-800' },
    quality: { label: '품질', classes: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300 border-yellow-200 dark:border-yellow-800' },
    standard: { label: '표준', classes: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300 border-red-200 dark:border-red-800' },
    audit: { label: '감사', classes: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300 border-orange-200 dark:border-orange-800' },
    governance: { label: '거버넌스', classes: 'bg-cyan-100 text-cyan-800 dark:bg-cyan-900/30 dark:text-cyan-300 border-cyan-200 dark:border-cyan-800' },
  };
  return styles[type] || { label: '기타', classes: 'bg-gray-100 text-gray-800 border-gray-200' };
};

const getRiskStyle = (level) => {
  const styles = {
    CRITICAL: { label: '심각', color: 'bg-red-600' },
    HIGH: { label: '높음', color: 'bg-red-500' },
    MEDIUM: { label: '중간', color: 'bg-amber-400' },
    LOW: { label: '낮음', color: 'bg-gray-300 dark:bg-gray-600' },
  };
  return styles[level] || { label: '미정', color: 'bg-gray-200' };
};

const getStatusStyle = (status) => {
  const styles = {
    ACTIVE: { label: '활성', classes: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800' },
    PROPOSED: { label: '초안/제안', classes: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 border-gray-200 dark:border-gray-700' },
  };
  return styles[status] || { label: status, classes: 'bg-gray-100 text-gray-800 border-gray-200' };
};

export default function ComplianceShowTable({policies, setPolicies}) {
    const [isLoading, setIsLoading] = useState(true);

    const [currentPage, setCurrentPage] = useState(1);
    const totalCount = policies.length;
    const pageSize = 25; // 페이지당 항목 수

    const totalPages = Math.ceil(totalCount / pageSize);

    const indexOfLastItem = currentPage * pageSize;
    const indexOfFirstItem = indexOfLastItem - pageSize;
    const currentItems = policies.slice(indexOfFirstItem, indexOfLastItem);

    return (
        <div className="bg-card-light dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden flex flex-col h-[600px]">
            {/* Table Controls */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-gray-50 dark:bg-gray-800/30">
            <div className="relative flex-1 max-w-lg">
                <Search className="absolute left-3 top-2.5 text-gray-400" size={18} />
                <input 
                className="w-full pl-10 pr-4 py-2 text-sm bg-white dark:bg-card-dark border border-gray-200 dark:border-gray-700 focus:bg-white dark:focus:bg-card-dark focus:border-primary focus:ring-0 rounded-lg transition-all text-gray-900 dark:text-white outline-none" 
                placeholder="ID, 제목 또는 태그로 정책 검색..." 
                type="text"
                />
            </div>
            <div className="flex gap-2">
                <button className="flex items-center gap-1 px-3 py-2 bg-white dark:bg-card-dark border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <Filter size={16} /> 필터
                </button>
                <button className="flex items-center gap-1 px-3 py-2 bg-white dark:bg-card-dark border border-gray-200 dark:border-gray-700 rounded-lg text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                <ListFilter size={16} /> 정렬
                </button>
            </div>
            </div>


            {/* ============================= */}
            {/*     MOBILE CARD VERSION       */}
            {/* ============================= */}
            <div className="flex-1 overflow-auto p-4 space-y-4 md:hidden">

              {currentItems.map((policy) => {
                const typeStyle = getTypeStyle(policy.type);
                const riskStyle = getRiskStyle(policy.risk_level);
                const statusStyle = getStatusStyle(policy.status);

                return (
                  <div
                    key={policy.id}
                    className="bg-white dark:bg-card-dark border border-gray-200 dark:border-gray-700 rounded-xl p-4 shadow-sm space-y-3"
                  >
                    {/* 상단 */}
                    <div className="flex justify-between items-start gap-4"> 
                      <div className="min-w-0 flex-1"> 
                        <div className="font-semibold text-gray-900 dark:text-white" title={policy.title}>
                          {policy.title}
                        </div>
                        <div className="text-xs font-mono text-gray-400">
                          {policy.policy_id}
                        </div>
                      </div>

                      <span className={`text-xs px-3 py-1 rounded-full border whitespace-nowrap flex-shrink-0 ${typeStyle.classes}`}>
                        {typeStyle.label}
                      </span>
                    </div>

                    {/* 도메인 */}
                    <div className="text-sm text-gray-600 dark:text-gray-300">
                      도메인: <span className="font-medium">{policy.domain}</span>
                    </div>

                    {/* 태그 */}
                    <div className="flex flex-wrap gap-1">
                      {policy.tag.map((t, index) => (
                        <span
                          key={index}
                          className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400"
                        >
                          #{t}
                        </span>
                      ))}
                    </div>

                    {/* 위험도 + 상태 */}
                    <div className="flex justify-between items-center text-sm">
                      <div className="flex items-center gap-2">
                        <div className={`h-2 w-2 rounded-full ${riskStyle.color}`}></div>
                        <span>{riskStyle.label}</span>
                      </div>

                      <span className={`px-2 py-1 text-xs rounded-full border ${statusStyle.classes}`}>
                        {statusStyle.label}
                      </span>
                    </div>

                    {/* 승인 그룹 */}
                    <div>
                      <span className="text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 px-2 py-1 rounded-full border border-blue-200 dark:border-blue-800">
                        {policy.group_description}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
              
            {/* ============================= */}
            {/*      DESKTOP TABLE VERSION    */}
            {/* ============================= */}
            <div className="hidden md:block overflow-auto flex-1 custom-scrollbar">
            <table className="w-full text-sm text-left border-collapse">
                <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 font-medium sticky top-0 z-10 shadow-sm">
                <tr>
                    <th className="px-4 py-3 whitespace-nowrap border-b border-gray-200 dark:border-gray-700 w-24">유형</th>
                    <th className="px-4 py-3 whitespace-nowrap border-b border-gray-200 dark:border-gray-700 w-32">도메인</th>
                    <th className="px-4 py-3 whitespace-nowrap border-b border-gray-200 dark:border-gray-700">제목 / ID</th>
                    <th className="px-4 py-3 whitespace-nowrap border-b border-gray-200 dark:border-gray-700">태그</th>
                    <th className="px-4 py-3 whitespace-nowrap border-b border-gray-200 dark:border-gray-700 w-28">위험도</th>
                    <th className="px-4 py-3 whitespace-nowrap border-b border-gray-200 dark:border-gray-700 w-60">승인 권한</th>
                    <th className="px-4 py-3 whitespace-nowrap border-b border-gray-200 dark:border-gray-700 w-24">상태</th>
                    <th className="px-4 py-3 whitespace-nowrap border-b border-gray-200 dark:border-gray-700 w-20 text-center">작업</th>
                </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                
                {/* 3. 데이터 배열 매핑 (동적 렌더링) */}
                {currentItems.map((policy) => {
                    const typeStyle = getTypeStyle(policy.type);
                    const riskStyle = getRiskStyle(policy.risk_level);
                    const statusStyle = getStatusStyle(policy.status);

                    return (
                    <tr key={policy.id} className="hover:bg-primary/5 dark:hover:bg-primary/5 transition-colors group bg-white dark:bg-card-dark">
                        <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${typeStyle.classes}`}>
                            {typeStyle.label}
                        </span>
                        </td>
                        <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                        <div className="capitalize">{policy.domain}</div>
                        </td>
                        <td className="px-4 py-3">
                        <div className="font-medium text-gray-900 dark:text-white">{policy.title}</div>
                        <div className="text-xs font-mono text-gray-400">{policy.policy_id}</div>
                        </td>
                        <td className="px-4 py-3">
                        <div className="flex gap-1 flex-wrap">
                            {policy.tag.map((t, index) => (
                            <span key={index} className="text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400">
                                #{t}
                            </span>
                            ))}
                        </div>
                        </td>
                        <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                            <div className={`h-2 w-2 rounded-full ${riskStyle.color}`}></div>
                            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{riskStyle.label}</span>
                        </div>
                        </td>
                        
                        <td className="px-5 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800`}>
                            {policy.group_description}
                        </span>
                        </td>

                        <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium border ${statusStyle.classes}`}>
                            {statusStyle.label}
                        </span>
                        </td>
                        <td className="px-4 py-3 text-center">
                        <button className="text-gray-400 hover:text-primary transition-colors p-1">
                            <MoreHorizontal size={20} />
                        </button>
                        </td>
                    </tr>
                    );
                })}
                </tbody>
            </table>
            </div>

            {/*  Pagination Controls - 하단 고정 */}

            <div className="
              sticky bottom-0
              p-4
              border-t border-gray-200 dark:border-gray-700
              bg-white/95 dark:bg-card-dark/95
              backdrop-blur
            ">

              {/*  Mobile Layout */}
              <div className="flex md:hidden items-center justify-between">

                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 disabled:opacity-30"
                >
                  이전
                </button>

                <div className="text-sm font-medium">
                  {currentPage} / {totalPages}
                </div>

                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-800 disabled:opacity-30"
                >
                  다음
                </button>
              </div>

                {/* PC 버전  */}
              <div className="hidden md:flex items-center justify-between">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  총 <span className="font-semibold text-gray-900 dark:text-white">
                    {totalCount}
                  </span>
                  개 중 {(currentPage - 1) * pageSize + 1}-
                  {Math.min(currentPage * pageSize, totalCount)} 표시
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                    disabled={currentPage === 1}
                    className="p-2 border rounded-lg disabled:opacity-30"
                  >
                    <ChevronLeft size={18} />
                  </button>

                  <div className="flex items-center gap-1">
                    {[...Array(totalPages)].map((_, i) => (
                      <button
                        key={i + 1}
                        onClick={() => setCurrentPage(i + 1)}
                        className={`w-9 h-9 rounded-lg ${
                          currentPage === i + 1
                            ? 'bg-primary text-white'
                            : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                        }`}
                      >
                        {i + 1}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                    disabled={currentPage === totalPages}
                    className="p-2 border rounded-lg disabled:opacity-30"
                  >
                    <ChevronRight size={18} />
                  </button>
                </div>

              </div>
            </div>



        </div>
    );
};
