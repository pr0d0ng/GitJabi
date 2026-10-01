import React from 'react';
import { KPICard, CircularProgress } from './widgets/KPICard';
import { ViolationChart } from './widgets/ViolationChart';
import { RepoTable } from './widgets/RepoTable';
import { ReviewList } from './widgets/ReviewList';
import { Bell, Plus, Moon, Sun, Shield, Share2, ChevronLeft, ChevronRight, History, Github } from 'lucide-react';

interface DashboardProps {
  isDark: boolean;
  setIsDark: (val: boolean) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ isDark, setIsDark }) => {
  return (
    <>
      {/* Header */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-8 gap-4 md:gap-0">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">대시보드</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            환영합니다. 대시보드를 통해 프로젝트 전체의 흐름을 확인하세요!
          </p>
        </div>
        <div className="flex items-center gap-4">
          <button className="relative p-2 rounded-full bg-white dark:bg-card-dark shadow-sm text-gray-500 dark:text-gray-400 hover:text-primary transition-colors">
            <Bell size={20} />
            <span className="absolute top-2 right-2 h-2 w-2 bg-red-500 rounded-full border border-white dark:border-card-dark"></span>
          </button>
          <button className="flex items-center gap-2 bg-primary text-white px-4 py-2 rounded-lg hover:bg-teal-700 transition-colors shadow-lg shadow-teal-500/30 font-medium text-sm">
            <Github size={16} />
            Github 연동 현황
          </button>
          <button 
            className="p-2 rounded-full bg-white dark:bg-card-dark shadow-sm text-gray-500 dark:text-gray-400 hover:text-primary transition-colors"
            onClick={() => setIsDark(!isDark)}
          >
            {isDark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </div>
      </header>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <KPICard 
          title="Compliance Rate" 
          value="94.2%" 
          change="+2.4%" 
          changeType="positive" 
          changeText="지난주 대비"
          chart={<CircularProgress radius={16} percentage={94.2} color="#108b77" />}
        />
        <KPICard 
          title="Risk Index" 
          value="12" 
          change="-5 pts" 
          changeType="negative"
          changeText="감소 추세 (긍정)"
          icon={<Shield size={32} />}
        />
        <KPICard 
          title="Context Nodes" 
          value="8,402" 
          change="Active" 
          changeType="positive"
          changeText="Knowledge Graph"
          icon={<Share2 size={32} />}
        />
      </div>

      {/* Charts & Lists Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {/* Main Chart */}
        <div className="lg:col-span-2 bg-card-light dark:bg-card-dark p-6 rounded-xl shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)] border border-gray-100 dark:border-gray-700 relative">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-3">
              <button className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-primary transition-colors">
                <ChevronLeft size={18} />
              </button>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">정책 위반 트렌드 (Policy Violation Trends)</h3>
              <button className="p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-primary transition-colors">
                <ChevronRight size={18} />
              </button>
            </div>
            <select className="bg-gray-50 dark:bg-gray-800 border-none text-sm text-gray-600 dark:text-gray-300 rounded-md py-1 px-3 focus:ring-1 focus:ring-primary cursor-pointer outline-none">
              <option>최근 6개월</option>
              <option>최근 1년</option>
            </select>
          </div>
          
          <ViolationChart />
          
          <div className="flex justify-center items-center gap-2 mt-4">
            <button className="w-2 h-2 rounded-full bg-primary transition-colors ring-2 ring-offset-2 ring-primary ring-offset-white dark:ring-offset-card-dark"></button>
            <button className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600 hover:bg-primary/50 transition-colors"></button>
            <button className="w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600 hover:bg-primary/50 transition-colors"></button>
          </div>
        </div>

        {/* Side List */}
        <div className="bg-card-light dark:bg-card-dark p-6 rounded-xl shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)] border border-gray-100 dark:border-gray-700 flex flex-col h-full">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">Change Request 현황</h3>
            <History className="text-gray-400" size={20} />
          </div>
          
          <ReviewList />
          
          <button className="w-full mt-auto pt-4 text-sm text-primary font-medium hover:text-teal-700 dark:hover:text-teal-400 transition-colors">
            모든 요청 보기
          </button>
        </div>
      </div>

      {/* Bottom Table */}
      <div className="bg-card-light dark:bg-card-dark p-6 rounded-xl shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)] border border-gray-100 dark:border-gray-700 mb-8">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">레포지토리 핵심 지표 (Repository Key Metrics)</h3>
          <button className="text-sm text-primary font-medium hover:text-teal-700 dark:hover:text-teal-400 transition-colors">
            리포트 내보내기
          </button>
        </div>
        <RepoTable />
      </div>

      <div className="h-8"></div>
    </>
  );
};