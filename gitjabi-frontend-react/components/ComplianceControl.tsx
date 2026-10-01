import React, { useState, useRef, useMemo, useEffect } from 'react';
import { 
  RefreshCw, Bell, User, Hourglass, CheckCircle, ExternalLink, Ban, Terminal, Ticket,
  Brain, AlertOctagon, ChevronRight, Code, Flag, Check, Cpu, CalendarCheck,
  History, ShieldCheck, UserCheck, Activity, GitPullRequest, AlertTriangle,
  Lock, Scale, Bold, MessageSquare, GitCommit, FileCode, CheckCircle2, XCircle, Plus,
  GitPullRequestArrow, 
  TrendingDown, ShieldAlert, Database, Target, FileSearch 
} from 'lucide-react';

import PRCarousel from './widgets/TimelinePRCarousel'
import TechComplianceViolationCards from './widgets/TechComplianceViolationCards'
import RulebaseScanList from './widgets/RulebaseComplianceViolationLists'
import IntegratedRiskScoreCard from './widgets/IntegratedRiskScoreCards'
import CRDecisionFooter from './widgets/DecisionFooterBar';

import AddChangeRequestModal from './modals/AddChangeRequestModal'
import CrIdBadge from './widgets/CopyableCRIdBadge'

import api from '../api/api'
// import {crListData} from './crListMockData'

export const ComplianceControlPage: React.FC = () => {
  const [initialized, setInitialized] = useState(false);
  const [crListData, setChangeRequestsData] = useState([]);
  const [activeTab, setActiveTab] = useState('ALL');  // CR 분류 탭
  const [selectedCrId, setSelectedCrId] = useState<string | null>(null);
  const [isChangeReqCreateOpen, setIsChangeReqCreateOpen] = useState(false)   // CR 등록 다이얼로그 UI
  const [isRefreshing, setIsRefreshing] = useState(false);

  const detailScrollRef = useRef<HTMLDivElement>(null);

  const fetchChangeRequests = async () => {
    try {
      const response = await api.get(`/api/dashboard/change-request/`);
      const data = Array.isArray(response.data) ? response.data : (response.data.items || []);
      
      setChangeRequestsData(data);
      
      setSelectedCrId((prevId) => {
        if (prevId !== null && prevId !== undefined) {
          return prevId;
        }
        return data.length > 0 ? String(data[0].id) : null;
      });

    } catch (error) {
      console.error('CR 목록 로딩 실패:', error);
    }
  };

  // User selected CR
  const currentCR = useMemo(() => {
    if (crListData.length === 0) return null;
    const found = crListData.find((cr) => String(cr.id) === String(selectedCrId));
    
    if (found) return found;

    return crListData[0];
  }, [selectedCrId, crListData]);

  // Filtered List
  const filteredList = useMemo(() => {
    if (activeTab === 'ALL') return crListData;
    return crListData.filter(cr => cr.status === activeTab);
  }, [activeTab, crListData]);

  // Sidebar Handler
  const handleSelectCr = (id: string) => {
    setSelectedCrId(id);
  };

  useEffect(() => {
    fetchChangeRequests();
    if (detailScrollRef.current) {
      detailScrollRef.current.scrollTo({
        top: 0,
        behavior: 'smooth'
      });
    }
  }, [selectedCrId]);

  function onAddPR(){
    fetchChangeRequests();
  }

  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    await fetchChangeRequests();
    setTimeout(() => setIsRefreshing(false), 500); 
  };

  if (crListData.length == 0) { return };

  if (!initialized) setInitialized(true);

  return (
    <div className="flex flex-col h-full bg-gray-50 dark:bg-background-dark text-gray-900 dark:text-gray-100">
      {/* Top Navbar */}
      <nav className="h-16 flex-none bg-white dark:bg-card-dark border-b border-gray-200 dark:border-gray-700 px-8 flex items-center justify-between z-30 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="p-2.5 bg-primary/10 rounded-xl">
            <Scale className="text-primary" size={22} />
          </div>
          <div>
            <h1 className="text-lg font-bold">
                컴플라이언스 통제</h1>
            <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">
                Compliance Control System
            </p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          {/* CR 등록 */}
          <button
            onClick={() => setIsChangeReqCreateOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-primary text-white text-s font-black uppercase tracking-widest shadow-sm hover:shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <Ticket size={14} strokeWidth={3} />
            CR 발행
          </button>
          {/* 알림 */}
          <button className="p-2 text-gray-400 hover:text-primary transition-colors">
            <Bell size={20}/>
          </button>
        </div>
      </nav>

      {/* 모달 */}
      <AddChangeRequestModal
        isOpen={isChangeReqCreateOpen} 
        onClose={() => setIsChangeReqCreateOpen(false)} 
      />

      {/* 사이드바 */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Sidebar: CR List (Wider & Spacious) */}
        <aside className="w-[420px] flex-none border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900/50 flex flex-col">
          <div className="p-6 space-y-5 border-b border-gray-100 dark:border-gray-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Ticket />
                <h2 className="text-sm font-bold text-gray-600 uppercase tracking-widest">
                  변경 요청(CR) 목록</h2>
                {/* 새로고침 버튼 추가 */}
                <button 
                  onClick={handleManualRefresh}
                  disabled={isRefreshing}
                  className={`p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-all ${
                    isRefreshing ? 'opacity-50' : ''
                  }`}
                  title="새로고침"
                >
                  <RefreshCw 
                    size={16} 
                    className={`text-gray-500 ${isRefreshing ? 'animate-spin' : ''}`} 
                  />
                </button>
              </div>

              <span className="text-[10px] font-bold bg-primary/10 text-primary px-2 py-1 rounded-full">
                전체 {crListData.length}건
              </span>
            </div>
            {/* Tabs Restored */}
            <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl overflow-x-auto no-scrollbar">
              {['ALL', 'VIOLATION', 'IN PROGRESS', 'APPROVED'].map((tab) => (
                <button 
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`whitespace-nowrap flex-1 py-2 text-[10px] font-bold rounded-lg transition-all ${
                    activeTab === tab ? 'bg-white dark:bg-gray-700 text-primary shadow-sm' : 'text-gray-500'
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar mb-20 pb-20">
            {filteredList.map((cr) => (
              <div 
                key={cr.id}
                onClick={() => handleSelectCr(cr.id)}
                className={`group p-5 rounded-2xl border-2 shadow-sm transition-all cursor-pointer ${
                  selectedCrId === cr.id ? 'bg-white dark:bg-gray-800 border-primary shadow-lg ring-4 ring-primary/5' : 'bg-transparent border-transparent hover:border-gray-200 dark:hover:border-gray-700'
                }`}
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="space-y-1">
                    <span className="text-[10px] font-mono font-bold text-primary bg-primary/5 px-2 py-1 rounded-lg">{cr.id}</span>
                    <div className="flex items-center gap-1 text-[10px] text-gray-400 font-bold">
                       <History size={12}/> {cr.createdAt}
                    </div>
                  </div>
                    {/* 상태별 색상 매핑 수정 */}
                    <span className={`text-[10px] font-black px-2.5 py-1 rounded-full ${
                        cr.status === 'VIOLATION' 
                        ? 'bg-red-50 text-red-600' 
                        : cr.status === 'IN_PROGRESS' 
                            ? 'bg-orange-50 text-orange-600' 
                            : cr.status === 'APPROVED' 
                            ? 'bg-green-50 text-green-600' 
                            : 'bg-gray-50 text-gray-500'   
                    }`}>
                        {cr.status.replace('_', ' ')}
                    </span>
                </div>
                <h3 className="text-sm font-bold leading-snug line-clamp-2 mb-4 group-hover:text-primary transition-colors">{cr.title}</h3>
                <div className="flex items-center justify-between pt-4 border-t border-gray-50 dark:border-gray-800">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-gray-200 overflow-hidden border border-white">
                       <img src={`https://api.dicebear.com/7.x/identicon/svg?seed=${cr.requester}}`} alt="" />
                       {/* <img src={`https://github.com/${cr.requester}.png`} alt="" /> */}
                    </div>
                    <span className="text-xs font-semibold text-gray-600">{cr.requester}</span>
                  </div>
                  <ChevronRight size={16} className="text-gray-300 group-hover:translate-x-1 transition-transform" />
                </div>
              </div>
            ))}
          </div>
        </aside>

        {/* Main Content Area */}
        <main ref={detailScrollRef}
          className="flex-1 overflow-y-auto bg-white dark:bg-card-dark custom-scrollbar pb-32">
          {/* Header Summary */}
          <div className="px-10 py-10 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-900/20">
            <div className="max-w-6xl mx-auto flex justify-between items-start gap-8">
              <div className="flex-1">
                {/* 상단 메타 정보 영역: 환경 정보와 CR ID를 세련되게 배치 */}
                <div className="flex items-center gap-3 mb-4">
                  {/* CR ID 칩: 박제된 느낌을 주는 보더와 백그라운드 */}
                  <CrIdBadge crId={currentCR.id}/>
                  
                  <div className="h-3 w-px bg-gray-300 dark:bg-gray-700" /> {/* 수직 구분선 */}
                  
                  <div className="flex items-center gap-1.5 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-tight">
                    <ShieldCheck size={14} className="text-primary/70"/>
                    <span>배포 환경:</span>
                    <span className="text-gray-900 dark:text-white font-black decoration-primary/30 underline underline-offset-4">
                      {currentCR.targetEnv}
                    </span>
                  </div>
                </div>

                {/* 타이틀 영역: 가독성을 위해 자간과 행간 최적화 */}
                <h2 className="text-4xl font-black text-gray-900 dark:text-white leading-[1.1] tracking-tight group">
                  <span className="bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-400 bg-clip-text text-transparent">
                    {currentCR.title}
                  </span>
                </h2>
              </div>
                <div className="flex flex-col items-end gap-1.5 shrink-0">
                {/* <div className="text-[10px] font-black text-gray-400 dark:text-gray-500 uppercase tracking-[0.15em] mx-auto">
                  GOVERNANCE GATE
                </div> */}
                <div className={`px-4 py-2.5 rounded-xl border-2 flex items-center gap-3 transition-all duration-300 ${
                    currentCR.status === 'VIOLATION' 
                    ? 'border-red-500/50 bg-red-50/50 dark:bg-red-900/10 text-red-600 dark:text-red-400 shadow-[0_0_15px_rgba(239,68,68,0.1)]' 
                    : currentCR.status === 'APPROVED'
                    ? 'border-emerald-500/50 bg-emerald-50/50 dark:bg-emerald-900/10 text-emerald-600 dark:text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                    : 'border-orange-500/50 bg-orange-50/50 dark:bg-orange-900/10 text-orange-600 dark:text-orange-400 shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                }`}>
                    {currentCR.status === 'VIOLATION' ? (
                    <div className="p-1 bg-red-100 dark:bg-red-900/30 rounded-md">
                        <Lock size={18} strokeWidth={2.5} />
                    </div>
                    ) : currentCR.status === 'APPROVED' ? (
                    <div className="p-1 bg-emerald-100 dark:bg-emerald-900/30 rounded-md">
                        <CheckCircle size={18} strokeWidth={2.5} />
                    </div>
                    ) : (
                    <div className="p-1 bg-orange-100 dark:bg-orange-900/30 rounded-md">
                        <CheckCircle size={18} strokeWidth={2.5} />
                    </div>
                    )}
                    <span className="text-sm font-black tracking-tight uppercase">
                    {currentCR.status === 'VIOLATION' ? 
                      '배포 제한' : currentCR.status === 'APPROVED' ?
                      '배포 준비': '승인 대기 중'}
                    </span>
                </div>
                </div>
            </div>
          </div>

          <div className="px-10 py-12">
            <div className="max-w-6xl mx-auto space-y-16">
              
              {/* CR Overview Section */}
              <section
                className={`relative pl-10 border-l-2 transition-colors duration-300 ${
                  currentCR.currentStage > 1
                    ? "border-primary/30"
                    : currentCR.currentStage == 1
                    ? "border-blue-300"
                    : "border-gray-200 dark:border-gray-800"
                }`}
              >
                <div
                  className={`absolute -left-2 top-0 w-4 h-4 bg-white rounded-full border-2 shadow-sm flex items-center justify-center transition-all duration-300 ${
                    currentCR.currentStage > 1
                      ? "dark:bg-card-dark border-primary"
                      : currentCR.currentStage == 1
                      ? "bg-blue-500 border-blue-500"
                      : "bg-white dark:bg-card-dark border-gray-400"
                  }`}
                />
                <div className="mb-8">
                  <h3 className="text-xl font-black flex items-center gap-2">
                    <Ticket size={22} className={`${
                      currentCR.currentStage > 1 
                      ? 'text-primary' : currentCR.currentStage == 1
                      ? 'text-blue-400' : 'text-gray-400'
                    }`}/>
                    변경 요청 개요 <sub className="font-light">(CR Overview)</sub>
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">
                    변경 요청의 기본 정보 및 상세 설명입니다.
                  </p>
                </div>

                <div className="bg-white dark:bg-gray-900/40 border border-gray-100 dark:border-gray-800 rounded-3xl p-8 shadow-sm space-y-8">

                  {/* CR 번호 */}
                  <div className="flex justify-between">
                    <div className="space-y-2">
                      <div className="flex items-center">
                        <div>
                          {/* Badges */}
                          <div className="flex items-center gap-2">
                            {/* 핫픽스 */}
                            <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2">
                              <span className={`text-xs font-mono font-bold bg-primary/5 px-3 py-1.5 rounded-xl ${
                                currentCR.IsHotfix == true 
                                ? 'text-red-600'
                                : 'text-primary'
                              }`}>
                                #{currentCR.IsHotfix == true ? '핫픽스' : '일반'}
                              </span>
                            </div>

                            {/* CR ID */}
                            <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2">
                              <span className="text-xs font-mono font-bold text-primary bg-primary/5 px-3 py-1.5 rounded-xl">
                                #{currentCR.id}
                              </span>
                            </div>
                            
                            {/* 우선순위 */}
                            <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2">
                              <span className={`text-xs font-mono font-bold text-blue-600 bg-primary/5 px-3 py-1.5 rounded-xl ${
                                currentCR.priority.toUpperCase() === 'HIGH' || currentCR.priority.toUpperCase() === 'CRITICAL' 
                                ? 'text-red-600'
                                : currentCR.priority.toUpperCase() === 'MEDIUM' ? 'text-blue-600' 
                                : 'text-primary' 
                              }`}>
                                우선순위 {currentCR.priority}
                              </span>
                            </div>
                          </div>

                          {/* Title */}
                          {/* <h2 className="text-2xl font-black text-gray-900 dark:text-white leading-tight">
                            {currentCR.title}
                          </h2> */}
                        </div>
                      </div>
                    </div>
                    <span className="flex items-center gap-2 font-semibold">
                      <User size={14}/>
                      {currentCR.requester}
                    </span>
                  </div>

                  {/* Body */}
                  <div>
                    <div className="p-6 rounded-2xl bg-gray-50 dark:bg-gray-800/60 border border-gray-100 dark:border-gray-700 text-md leading-relaxed text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {currentCR.description || "설명이 입력되지 않았습니다."}
                    </div>
                  </div>
                  <div className="flex items-center justify-end gap-2 text-xs text-gray-500">
                    <div className="flex gap-4">
                      <span className="flex gap-2 text-xs text-gray-400">
                        <CalendarCheck size={14}/>
                        {currentCR.createdAt}
                      </span>
                    </div>
                  </div>
                </div>
              </section>

              {/* Section A: 기술 준법 (Carousel PRs) */}
              <section
                className={`relative pl-10 border-l-2 transition-colors duration-300 ${
                  currentCR.currentStage > 2
                    ? "border-primary/30"
                    : currentCR.currentStage == 2
                    ? "border-blue-300"
                    : "border-gray-200 dark:border-gray-800"
                }`}
              >
                <div
                  className={`absolute -left-2 top-0 w-4 h-4 bg-white rounded-full border-2 shadow-sm flex items-center justify-center transition-all duration-300 ${
                    currentCR.currentStage > 2
                      ? "dark:bg-card-dark border-primary"
                      : currentCR.currentStage == 2
                      ? "bg-blue-500 border-blue-500"
                      : "bg-white dark:bg-card-dark border-gray-400"
                  }`}
                />
                <div className="mb-8">
                  <h3 className="text-xl font-black flex items-center gap-2">
                    <Cpu size={22} className={`${
                      currentCR.currentStage > 2 
                      ? 'text-primary' : currentCR.currentStage == 2
                      ? 'text-blue-400' : 'text-gray-400'
                    }`}/>
                   기술 준법 <sub className="font-light">(Tech Compliance)</sub></h3>
                   <p className="text-xs text-gray-500 mt-1">개발 단계에서 컴플라이언스와 정책 준수와 통합 지표 등을 확인합니다.</p>
                </div>

                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-lg ${currentCR.technical.pullRequests.length > 0 ? 'bg-emerald-50 text-emerald-500' : 'bg-blue-50 text-blue-500'}`}>
                        <Activity size={20} />
                        </div>
                        <div>
                        <h2 className="text-md font-black text-gray-800 dark:text-gray-100">
                            풀 리퀘스트 및 컴플라이언스 분석</h2>
                        <p className="text-xs text-gray-400 uppercase tracking-wider">Related Pull Requests & Governance</p>
                        </div>
                    </div>
                    
                    <div className={`px-3 py-1 rounded-full text-[10px] font-black border ${
                        currentCR.technical.pullRequests.length > 0 
                        ? 'bg-blue-50 border-blue-100 text-blue-600' 
                        : 'bg-emerald-50 border-emerald-100 text-emerald-600'
                    }`}>
                        {currentCR.technical.pullRequests.length} PULL REQUESTS
                    </div>
                </div>
                <PRCarousel
                 currentCR={currentCR} 
                 onAddPR={onAddPR}
                />

                {/* Modern Gitjabi Violation UI */}
                <div className="space-y-6 mt-6">
                {/* Violation Cards */}
                <section>

                    {/* 조건부 렌더링: 위반 사항이 있을 때와 없을 때 */}
                    {/* 1단계: PR 존재 여부 체크 */}
                    {currentCR.technical.pullRequests.length === 0 ? (
                      <div className="relative overflow-hidden group">
                        <div className="p-10 rounded-3xl border-2 border-dashed border-gray-100 dark:border-gray-800 bg-gray-50/30 dark:bg-gray-900/10 flex flex-col items-center justify-center text-center transition-all">
                          <div className="relative mb-6">
                            <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 text-gray-400 rounded-2xl flex items-center justify-center border border-gray-200 dark:border-gray-700">
                              <GitPullRequest size={32} />
                            </div>
                          </div>
                          <h3 className="text-xl font-black text-gray-700 dark:text-gray-300 mb-2">
                            검증할 Pull Request가 없습니다
                          </h3>
                          <p className="text-sm text-gray-500 dark:text-gray-500 max-w-md leading-relaxed">
                            이 Change Request에 연결된 기술 변경 사항이 발견되지 않았습니다. <br/>
                            상단에서 PR을 추가하거나 Github PR 생성시 제목에 CR 고유번호를 포함하여 등록하면 연결됩니다.
                          </p>
                        </div>
                      </div>
                    ) : (
                      currentCR.technical.gitjabiScan !== null && currentCR.technical.gitjabiScan.length > 0 ? (
                        /* 위반 사항이 발견된 경우 */
                        <TechComplianceViolationCards currentCR={currentCR} />
                      ) : currentCR.technical.gitjabiScan === null ? 
                        /* 2단계: PR은 존재하지만 검사 결과가 아직 없으면 */
                        <div className="relative overflow-hidden group">
                          <div className="p-10 rounded-3xl border-2 border-dashed border-gray-100 dark:border-gray-800 bg-gray-50/30 dark:bg-gray-900/10 flex flex-col items-center justify-center text-center transition-all">
                            <div className="relative mb-6">
                              <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 text-gray-400 rounded-2xl flex items-center justify-center border border-gray-200 dark:border-gray-700">
                                <Terminal size={32} />
                              </div>
                            </div>
                            <h3 className="text-xl font-black text-gray-700 dark:text-gray-300 mb-2">
                              검사 결과를 기다리고 있습니다.
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-500 max-w-md leading-relaxed">
                              전체 검사가 완료될 때 까지 조금의 시간이 소요됩니다.
                            </p>
                          </div>
                        </div>
                      : (
                        /* 성공(Success) 상태 UI */
                        <div className="relative overflow-hidden group">
                          <div className="p-10 rounded-3xl border-2 border-dashed border-emerald-100 dark:border-emerald-900/30 bg-emerald-50/20 dark:bg-emerald-900/5 flex flex-col items-center justify-center text-center transition-all">
                            <ShieldCheck size={120} className="absolute -right-8 -bottom-8 text-emerald-500/5 rotate-12" />
                            <div className="relative mb-6">
                              <div className="absolute inset-0 bg-emerald-400/20 blur-2xl rounded-full animate-pulse"></div>
                              <div className="relative w-16 h-16 bg-emerald-500 text-white rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
                                <CheckCircle2 size={32} strokeWidth={2.5} />
                              </div>
                            </div>
                            <h3 className="text-xl font-black text-emerald-700 dark:text-emerald-400 mb-2">
                              컴플라이언스 통과
                            </h3>
                            <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md leading-relaxed">
                              연결된 모든 Pull Request가 사내 기술 표준 및 보안 정책을 완벽히 준수하고 있습니다.
                            </p>
                            <div className="mt-8 flex gap-6">
                              <div className="flex items-center gap-2 text-[10px] font-black text-emerald-600/60 uppercase tracking-widest">
                                <Cpu size={14}/> AI Scan Passed
                              </div>
                              <div className="flex items-center gap-2 text-[10px] font-black text-emerald-600/60 uppercase tracking-widest">
                                <ShieldCheck size={14}/> 0 Security Threats
                              </div>
                            </div>
                          </div>
                        </div>
                      )
                    )}

                </section>
                </div>
              </section>

              {/* Section B: 기업 준법 (Multiple Policies) */}
              <section
                className={`relative pl-10 border-l-2 transition-colors duration-300 ${
                  currentCR.currentStage > 3
                    ? "border-primary/30"
                    : currentCR.currentStage == 3
                    ? "border-blue-300"
                    : "border-gray-200 dark:border-gray-800"
                }`}
              >
                <div
                  className={`absolute -left-2 top-0 w-4 h-4 bg-white rounded-full border-2 shadow-sm flex items-center justify-center transition-all duration-300 ${
                    currentCR.currentStage > 3
                      ? "dark:bg-card-dark border-primary"
                      : currentCR.currentStage == 3
                      ? "bg-blue-500 border-blue-500"
                      : "bg-white dark:bg-card-dark border-gray-400"
                  }`}
                />
                <div className="mb-8">
                  <h3 className="text-xl font-black flex items-center gap-2">
                    <ShieldCheck size={22} className={`${
                      currentCR.currentStage > 3 
                      ? 'text-primary' : currentCR.currentStage == 3
                      ? 'text-blue-400' : 'text-gray-400'
                    }`}/>
                    거버넌스 준수 <sub className="font-light">(Enterprise Governance)</sub>
                  </h3>
                  <p className="text-xs text-gray-500 mt-1">사내 거버넌스 규칙 준수 여부를 판단하여 위험 요소를 사전에 방지합니다.</p>
                </div>
                
                <div className="space-y-3">
                  <RulebaseScanList
                    currentCR={currentCR}
                  />
                </div>
              </section>

              {/* Section C : 위험 평가 Risk Assessment */}
              <section
                className={`relative pl-10 border-l-2 transition-colors duration-300 ${
                  currentCR.currentStage > 4
                    ? "border-primary/30"
                    : currentCR.currentStage == 4
                    ? "border-blue-300"
                    : "border-gray-200 dark:border-gray-800"
                }`}
              >
                <div
                  className={`absolute -left-2 top-0 w-4 h-4 bg-white rounded-full border-2 shadow-sm flex items-center justify-center transition-all duration-300 ${
                    currentCR.currentStage > 4
                      ? "dark:bg-card-dark border-primary"
                      : currentCR.currentStage == 4
                      ? "bg-blue-500 border-blue-500"
                      : "bg-white dark:bg-card-dark border-gray-400"
                  }`}
                />

                  <div className="mb-8 flex items-end justify-between">
                    <div>
                      <h3 className="text-xl font-black flex items-center gap-2">
                        <AlertTriangle size={22} className={`${
                          currentCR.currentStage > 4 
                          ? 'text-primary' : currentCR.currentStage == 4
                          ? 'text-blue-400' : 'text-gray-400'
                        }`}/>
                        위험 평가 <sub className="font-light">(Risk Assessment)</sub>
                      </h3>
                      <p className="text-xs text-gray-500 mt-1">
                        PR 내역과 과거 배포/장애 데이터를 바탕으로 시스템 영향도를 정량 분석합니다.
                      </p>
                    </div>
                    <button className="text-[10px] font-bold text-gray-400 hover:text-primary transition-colors flex items-center gap-1">
                      <FileSearch size={14}/> 상세 영향도 분석 리포트
                    </button>
                  </div>

                  <IntegratedRiskScoreCard
                    riskScore={currentCR.riskScore}
                    riskFactors={currentCR.riskFactors}
                  />
              </section>

              {/* Section D: 의사결정 (Responsive 1-3 Columns) */}
              <section
                className={`relative pl-10 border-l-2 transition-colors duration-300 ${
                  currentCR.currentStage > 5
                    ? "border-primary/30"
                    : currentCR.currentStage == 5
                    ? "border-blue-300"
                    : "border-gray-200 dark:border-gray-800"
                }`}
              >
                <div
                  className={`absolute -left-2 top-0 w-4 h-4 bg-white rounded-full border-2 shadow-sm flex items-center justify-center transition-all duration-300 ${
                    currentCR.currentStage > 5
                      ? "dark:bg-card-dark border-primary"
                      : currentCR.currentStage == 5
                      ? "bg-blue-500 border-blue-500"
                      : "bg-white dark:bg-card-dark border-gray-400"
                  }`}
                />
                <div className="mb-8">
                  <h3 className="text-xl font-black flex items-center gap-2">
                    <UserCheck size={22} className={`${
                      currentCR.currentStage > 5 
                      ? 'text-primary' : currentCR.currentStage == 5
                      ? 'text-blue-400' : 'text-gray-400'
                    }`}/>
                   의사결정 <sub className="font-light">(Decision Gate)</sub></h3>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                  {currentCR.decision.map((dec, idx) => (
                    <div key={idx} className="p-5 rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-800/50 shadow-sm flex flex-col">
                      <div className="flex items-center justify-between mb-4">
                         <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center text-gray-400">
                              {/* <UserCheck size={18}/> */}
                               {dec.name ?
                                   <img src={`https://api.dicebear.com/7.x/identicon/svg?seed=${dec.name}}`} alt="" />
                                 :
                                 <UserCheck size={18}/>
                                }
                            </div>
                            <div>
                               <p className="text-s font-black text-gray-900 dark:text-white leading-tight">{dec.name}</p>
                               <p className="text-[12px] text-gray-500 font-bold">{dec.role}</p>
                            </div>
                         </div>
                         <span className={`text-[11px] font-black px-2 py-0.5 rounded-full ${
                           dec.status === 'APPROVED' ? 'bg-green-100 text-green-600' : 
                           dec.status === 'REJECTED' ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'
                         }`}>{dec.status.toUpperCase()}</span>
                      </div>
                      {dec.comment ? (
                        <div className="mt-auto p-3 bg-gray-50 dark:bg-gray-900 rounded-lg border border-gray-100 dark:border-gray-700 italic">
                          <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed flex gap-2">
                             <MessageSquare size={12} className="shrink-0 mt-0.5 opacity-50"/> "{dec.comment}"
                          </p>
                        </div>
                      ) : (
                        <div className="mt-auto text-[10px] text-gray-400 text-center py-4 border border-dashed rounded-lg border-gray-200">의견 대기 중</div>
                      )}
                    </div>
                  ))}
                </div>
              </section>

              {/* Section D: Audit Log */}
              <section
                className={`relative pl-10 border-l-2 transition-colors duration-300 ${
                  currentCR.currentStage > 6
                    ? "border-primary/30"
                    : currentCR.currentStage == 6
                    ? "border-blue-300"
                    : "border-gray-200 dark:border-gray-800"
                }`}
              >
                <div
                  className={`absolute -left-2 top-0 w-4 h-4 bg-white rounded-full border-2 shadow-sm flex items-center justify-center transition-all duration-300 ${
                    currentCR.currentStage > 6
                      ? "dark:bg-card-dark border-primary"
                      : currentCR.currentStage == 6
                      ? "bg-blue-500 border-blue-500"
                      : "bg-white dark:bg-card-dark border-gray-400"
                  }`}
                />
                <div className="mb-8">
                  <h3 className="text-xl font-black flex items-center gap-2">
                    <History size={22} className={`${
                          currentCR.currentStage > 6 
                          ? 'text-primary' : currentCR.currentStage == 6
                          ? 'text-blue-400' : 'text-gray-400'
                        }`}/>
                   감사 로그 <sub className="font-light">(Audit Log)</sub></h3>
                </div>
                <div className="space-y-4 max-w-2xl">
                   {currentCR.auditLogs.map((log, idx) => (
                     <div key={idx} className="flex items-center gap-6 p-2">
                        <span className="text-xs font-mono font-bold text-gray-400 w-26">{log.time}</span>
                        <div className="h-2 w-2 rounded-full bg-gray-200"></div>
                        <span className="text-sm font-bold text-gray-700 dark:text-gray-300">{log.action}</span>
                        <span className="text-xs text-gray-400 ml-auto">by {log.user}</span>
                     </div>
                   ))}
                </div>
              </section>

            </div>
          </div>
        </main>
      </div>

      {/* 의사결정 푸터 바 */}
      <CRDecisionFooter
        currentCR={currentCR} 
        onRefresh={fetchChangeRequests} 
      />
    </div>
  );
};