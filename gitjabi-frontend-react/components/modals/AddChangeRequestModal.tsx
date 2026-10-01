import React, { useState } from 'react';

import { Ticket, Building2, Check, Save, X } from 'lucide-react';
import api from '../../api/api'

const AddChangeRequestModal = ({ isOpen, onClose }) => {
  const initCR = {
    title: "",
    body: "",
    targetEnv: "PRODUCTION",
    priority: "MEDIUM",
    authorityGroup: 2,
    isHotfix: false
  }
  const [newCR, setNewCR] = useState(initCR);    // CR 상태

  if (!isOpen) return null;

  function closeDialog(){
    setNewCR(initCR)
    onClose()
  }

  async function ApplyBtn(){
    console.log("Create CR:", newCR)
    try {
      await api.post('/api/dashboard/change-request/publish', newCR);
      alert("CR이 성공적으로 등록되었습니다!");
      setNewCR(initCR)
      onClose()
    } catch (err) {
      alert("정책 등록 실패: " + (err.response?.data?.detail || "서버 오류"));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={closeDialog}
      />

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-white dark:bg-card-dark rounded-3xl shadow-2xl border border-gray-100 dark:border-gray-800 p-10 space-y-8 animate-in fade-in zoom-in-95 duration-200">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black flex items-center gap-2">
              <Ticket size={20} className="text-primary"/>
              변경 요청 등록
            </h2>
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mt-1">
              Create Change Request
            </p>
          </div>

          <button
            onClick={closeDialog}
            className="p-2 rounded-lg text-gray-400 hover:text-red-500 transition-colors"
          >
            <X size={18}/>
          </button>
        </div>

        {/* Form */}
        <div className="space-y-6">

          {/* Title */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
              Title
            </label>
            <input
              type="text"
              value={newCR.title}
              onChange={(e) => setNewCR({...newCR, title: e.target.value})}
              className="mt-2 w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all"
              placeholder="변경 요청 제목을 입력하세요"
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
              Description
            </label>
            <textarea
              rows={5}
              value={newCR.body}
              onChange={(e) => setNewCR({...newCR, body: e.target.value})}
              className="mt-2 w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all resize-none"
              placeholder="변경 목적, 영향 범위, 리스크 등을 작성하세요"
            />
          </div>

          {/* Environment + Priority */}
          <div className="grid grid-cols-2 gap-6">
            {/* 승인 권한  */}
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                AUTHORITY GROUP
              </label>
              <select
                value={newCR.authorityGroup}
                onChange={(e) => setNewCR({...newCR, authorityGroup: e.target.value})}
                className="mt-2 w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="2">관리자 그룹</option>
                <option value="3">기술 매니저 그룹</option>
                <option value="4">개발1팀 리드 그룹</option>
                <option value="6">보안팀 그룹</option>
              </select>
            </div>
            
            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                Target Environment
              </label>
              <select
                value={newCR.targetEnv}
                onChange={(e) => setNewCR({...newCR, targetEnv: e.target.value})}
                className="mt-2 w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="PRODUCTION">Production</option>
                <option value="STAGING">Staging</option>
                <option value="DEVELOPMENT">Development</option>
              </select>
            </div>

            <div>
              <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                Priority
              </label>
              <select
                value={newCR.priority}
                onChange={(e) => setNewCR({...newCR, priority: e.target.value})}
                className="mt-2 w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/60 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
              </select>
            </div>

            {/* 핫픽스 여부 */}
            <div className="flex items-center justify-between p-4 bg-white rounded-lg">
              <div className="flex flex-col">
                <label className="text-[10px] font-bold uppercase tracking-widest text-gray-400">
                  HOTFIX
                </label>
                <span className="text-xs text-gray-500">긴급 수정 사항인가요?</span>
              </div>
              <label htmlFor="hotfix-toggle" className="flex items-center cursor-pointer">
                <input 
                  type="checkbox" 
                  checked={newCR.isHotfix}
                  onChange={(e) => setNewCR({...newCR, isHotfix: e.target.checked})}
                  id="hotfix-toggle" 
                  className="sr-only peer"
                />
                <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600"></div>
              </label>
            </div>
            
          </div>

        </div>

        {/* Footer */}
        <div className="flex justify-end gap-4 pt-4 border-t border-gray-100 dark:border-gray-800">
          <button
            onClick={closeDialog}
            className="px-5 py-2 rounded-xl text-xs font-bold uppercase tracking-widest border border-gray-200 dark:border-gray-700 text-gray-500 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all"
          >
            취소
          </button>

          <button
            onClick={ApplyBtn}
            className="px-6 py-2 rounded-xl bg-primary text-white text-xs font-black uppercase tracking-widest shadow hover:shadow-md transition-all"
          >
            등록하기
          </button>
        </div>

      </div>
    </div>
  );
};

export default AddChangeRequestModal;