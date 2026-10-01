import React, { useState, useEffect } from 'react';
import { 
  Download, 
  Plus, 
  FileText, Activity, Clock, ArrowUp, AlertCircle, CheckCircle2, ArrowRight, Sparkles
} from 'lucide-react';

import AddComplianceModal from './modals/AddComplianceModal';
import PolicyShowTable from './widgets/PolicyMgmtComplianceTable';
import PolicyManagementMetric from './widgets/PolicyMgmtMetric';
import api from '../api/api'

export const PolicyManagementPage: React.FC = () => {
  const [isAddComplianceModalOpen, setIsAddComplianceModalOpen] = useState(false);

  const [policies, setPolicies] = useState([]);
  
  // API 호출 함수
  const fetchPolicies = async () => {
    try {
      const response = await api.get(`/api/dashboard/policy`);
      setPolicies(response.data.items || []);
    } catch (error) {
      console.error('정책 목록을 불러오는 데 실패했습니다.', error);
    }
  };
  useEffect(() => {
    fetchPolicies();
  }, []);

  return (
    <div className="flex flex-col h-full bg-background-light dark:bg-background-dark text-gray-900 dark:text-gray-100 font-sans">
      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 custom-scrollbar">
        <div className="max-w-8xl mx-auto space-y-6">
          {/* Header Section */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            {/* Breadcrumb & Title */}
            <div>
                <nav className="flex text-xs text-gray-500 dark:text-gray-400 mb-2">
                    <ol className="flex items-center space-x-2">
                        <li><a className="hover:text-primary transition-colors" href="#">
                          홈</a>
                        </li>
                        <li><span className="text-gray-300">/</span></li>
                        <li><span className="text-gray-900 dark:text-white font-medium">
                          정책 관리
                        </span>
                        </li>
                    </ol>
                </nav>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">정책 관리</h1>
                <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">IT 거버넌스 정책을 관리하고 프로젝트 전반의 준수 상태를 확인합니다.</p>
            </div>
            <div className="flex items-center gap-3">
              <button className="bg-card-light dark:bg-card-dark text-gray-700 dark:text-gray-200 px-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors flex items-center gap-2 text-sm font-medium shadow-sm">
                <Download size={16} />
                보고서 내보내기
              </button>
              <button 
                onClick={() => setIsAddComplianceModalOpen(true)}
                className="bg-primary hover:bg-teal-700 text-white px-4 py-2 rounded-lg transition-colors flex items-center gap-2 text-sm font-bold shadow-md shadow-primary/20"
              >
                <Plus size={16} />
                새 정책 추가
              </button>
            </div>
          </div>

          {/* Policy Metric  */}
          <PolicyManagementMetric
            policies={policies}
          />

          {/* 데이터 Table Section */}
          <PolicyShowTable 
            policies={policies}
            setPolicies={setPolicies}
          />

        </div>
      </main>

      <AddComplianceModal 
        isOpen={isAddComplianceModalOpen}
        onClose={() => setIsAddComplianceModalOpen(false)}
        onRefresh={() => fetchPolicies()}
      />
      
      {/* Footer */}
      <footer className="mt-auto border-t border-gray-200 dark:border-gray-700 bg-card-light dark:bg-card-dark py-6">
        <div className="max-w-8xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row justify-between items-center text-xs text-gray-500 dark:text-gray-400">
          <p>© 2026 GitJabi. All rights reserved.</p>
          <div className="flex gap-4 mt-2 md:mt-0">
            <a href="#" className="hover:text-primary transition-colors">시스템 상태</a>
            <a href="#" className="hover:text-primary transition-colors">문서</a>
            <a href="#" className="hover:text-primary transition-colors">고객지원</a>
          </div>
        </div>
      </footer>

    </div>
  );
};