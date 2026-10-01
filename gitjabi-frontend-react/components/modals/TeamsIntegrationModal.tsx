import React, { useState } from 'react';

import { Users, Building2, Check, Save, X } from 'lucide-react';

const TeamsIntegrationModal = ({ isOpen, onClose }) => {
  const [autoSync, setAutoSync] = useState(true);
  const [piiFilter, setPiiFilter] = useState(true);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-900/40 dark:bg-black/60 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      ></div>

      {/* Modal Container */}
      <div className="relative z-20 w-full max-w-2xl bg-white dark:bg-[#1a2c29] rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden transform transition-all">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-100 dark:border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 dark:bg-indigo-900/30 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <Users/>
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-900 dark:text-white">Teams 연동 관리</h2>
              <p className="text-sm text-slate-500 dark:text-slate-400">회의와 지식 데이터 추출 및 저장 통합 연동</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700">
            <X />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 max-h-[75vh] overflow-y-auto">
          {/* Connection Status */}
          <div className="mb-8 bg-slate-50 dark:bg-slate-800/40 rounded-lg p-4 border border-slate-100 dark:border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="relative">
                <div className="w-10 h-10 rounded-full bg-slate-300 flex items-center justify-center text-white">
                  <Building2/>
                </div>
                <div className="absolute -bottom-1 -right-1 w-4 h-4 bg-[#1be4c3] border-2 border-white dark:border-slate-800 rounded-full flex items-center justify-center">
                  <Check />
                </div>
              </div>
              <div>
                <div className="text-sm font-medium text-slate-900 dark:text-white">
                    연결된 테넌트: &nbsp;
                    <span className="font-bold">Microsoft Academy Dataschool</span>
                </div>
              </div>
            </div>
            <button className="text-xs font-medium text-slate-500 hover:text-red-500 dark:text-slate-400 dark:hover:text-red-400">
                연결 해제
            </button>
          </div>

          {/* Sync Configuration */}
          <div className="space-y-6 mb-8">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                동기화 설정
            </h3>
            
            {/* Toggles */}
            {[
              { id: 'auto-sync', label: '회의록 자동 추출 및 DB 동기화', desc: '지식 데이터 수집을 위해 자동화 프로세스를 활성화합니다.', state: autoSync, setState: setAutoSync },
              { id: 'pii-filter', label: '개인정보 가명 처리 필터링', desc: '데이터 수집 전 개인정보보호를 위해 특수 필터링을 거쳐야 합니다.', state: piiFilter, setState: setPiiFilter }
            ].map(item => (
              <div key={item.id} className="flex items-center justify-between">
                <div className="pr-4">
                  <label className="text-base font-medium text-slate-800 dark:text-slate-200 block">{item.label}</label>
                  <p className="text-sm text-slate-500 dark:text-slate-400">{item.desc}</p>
                </div>
                <button 
                  onClick={() => item.setState(!item.state)}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${item.state ? 'bg-[#1be4c3]' : 'bg-slate-300 dark:bg-slate-700'}`}
                >
                  <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${item.state ? 'translate-x-6' : 'translate-x-1'}`} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 dark:bg-slate-800/40 border-t border-slate-100 dark:border-slate-700/50 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-slate-300 dark:border-slate-600 rounded-lg">
            취소
          </button>
          <button className="px-4 py-2 text-sm font-semibold text-slate-900 bg-[#1be4c3] hover:bg-[#16c2a6] rounded-lg shadow-sm flex items-center gap-2">
            <Save /> 설정 저장
          </button>
        </div>
      </div>
    </div>
  );
};

export default TeamsIntegrationModal;