import React, { useState } from 'react';

import { Share2, RefreshCw, Check, Bold, Italic, List, Code, Save, X } from 'lucide-react';
import api from '../../api/api'

const AddComplianceModal = ({ isOpen, onClose, onRefresh }) => {

  const initialState = {
    title: "",
    content: "",
    type: "",
    domain: "",
    risk_level: "MEDIUM",
    tag: "", 
    status: "ACTIVE" 
  };

  const [newCompliance, setNewCompliance] = useState(initialState);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setNewCompliance(prev => ({
      ...prev,
      [name]: value
    }));
  };

  if (!isOpen) return null;

  const ApplyBtn = async () => {
    // 유효성 검사
    if (!newCompliance.title.trim()) return alert("정책 제목을 입력해주세요.");
    if (!newCompliance.type) return alert("정책 유형을 선택해주세요.");
    if (!newCompliance.domain) return alert("도메인을 선택해주세요.");
    if (!newCompliance.content.trim()) return alert("정책 내용을 입력해주세요.");

    // 데이터 가공 (태그 문자열 -> 배열)
    const payload = {
      ...newCompliance,
      tag: newCompliance.tag ? newCompliance.tag.split(',').map(t => t.trim().replace('#', '')) : []
    };

    try {
      await api.post('/api/dashboard/policy', payload);
      alert("정책이 성공적으로 등록되었습니다!");
      setNewCompliance(initialState); 
      if (onRefresh) onRefresh();
      onClose();
    } catch (err) {
      alert("정책 등록 실패: " + (err.response?.data?.detail || "서버 오류"));
    }
  };

  return (  
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/60 backdrop-blur-sm p-4 overflow-y-auto">
        <div className="bg-white dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 shadow-2xl w-full max-w-3xl flex flex-col max-h-[90vh] animate-in fade-in zoom-in duration-200">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-100 dark:border-gray-800 bg-white dark:bg-card-dark rounded-t-xl sticky top-0 z-10">
            <div>
            <h3 className="font-bold text-xl text-gray-900 dark:text-white">새 정책 추가</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">GitJabi 컴플라이언스 센터에 새로운 거버넌스 규칙을 등록합니다.</p>
            </div>
            <button 
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors"
            >
            <X size={20} />
            </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto custom-scrollbar">
            {/* 폼 */}
            <form className="space-y-6" onSubmit={(e) => e.preventDefault()}>
                    
                <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    정책 제목 <span className="text-red-500">*</span>
                    </label>
                    <input 
                    name="title"
                    value={newCompliance.title}
                    onChange={handleChange}
                    className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 focus:border-primary focus:ring-primary/20 text-sm dark:text-white py-2.5 shadow-sm px-3 outline-none focus:ring-2 transition-all" 
                    placeholder="예: 클라우드 리소스 태깅 필수 정책" 
                    type="text"
                    />
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        유형 <span className="text-red-500">*</span>
                    </label>
                    <select name="type" value={newCompliance.type} onChange={handleChange} 
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 focus:border-primary focus:ring-primary/20 text-sm dark:text-white py-2.5 shadow-sm px-3 outline-none focus:ring-2 transition-all">
                        <option value="">선택하세요</option>
                        <option value="security">보안 (Security)</option>
                        <option value="design">설계 (Design)</option>
                        <option value="quality">품질 (Quality)</option>
                        <option value="standard">표준 (Standard)</option>
                        <option value="audit">감사 (Audit)</option>
                        <option value="governance">거버넌스 (Governance)</option>
                    </select>
                    </div>
                    <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        도메인 <span className="text-red-500">*</span>
                    </label>
                    <select name="domain" value={newCompliance.domain} onChange={handleChange} 
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 focus:border-primary focus:ring-primary/20 text-sm dark:text-white py-2.5 shadow-sm px-3 outline-none focus:ring-2 transition-all">
                        <option value="">선택하세요</option>
                        <option value="infra">인프라 (Infra)</option>
                        <option value="backend">백엔드 (Backend)</option>
                        <option value="frontend">프론트엔드 (Frontend)</option>
                        <option value="cloud">클라우드 (Cloud)</option>
                        <option value="others">기타 (Others)</option>
                    </select>
                    </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                        <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                            위험도
                        </label>
                        <div>
                            <div className="flex gap-4">
                                {['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].map((level) => (
                                <label key={level} className="inline-flex items-center cursor-pointer">
                                    <input 
                                    type="radio" 
                                    name="risk_level" 
                                    value={level} 
                                    checked={newCompliance.risk_level === level}
                                    onChange={handleChange}
                                    className="form-radio text-primary" 
                                    />
                                    <span className="ml-2 text-sm dark:text-gray-300">{level}</span>
                                </label>
                                ))}
                            </div>
                        </div>
                    </div>
                    <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        승인 권한 그룹
                    </label>
                    <select name="authority_group" value={newCompliance.authority_group} onChange={handleChange}
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 focus:border-primary focus:ring-primary/20 text-sm dark:text-white py-2.5 shadow-sm px-3 outline-none focus:ring-2 transition-all">
                        <option value="1">일반 사용자 (Guest)</option>
                        <option value="2">관리자 (Admin)</option>
                        <option value="3">기술 매니저 그룹 (Tech Manager)</option>
                        <option value="4">개발1팀 리드 그룹(DevTeam 1 Lead)</option>
                        <option value="6">보안팀 (Security Team)</option>
                    </select>
                    </div>
                </div>

                {/* <div className="bg-gray-50 dark:bg-gray-800/50 p-4 rounded-lg border border-gray-200 dark:border-gray-700 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                    <span className="text-sm font-bold text-gray-900 dark:text-white block">정책 로직 설정</span>
                    <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 block">엄격한 규칙 기반인지, AI가 판단하는 추상적 정책인지 선택하세요.</span>
                    </div>
                    <div className="flex items-center bg-white dark:bg-gray-900 rounded-lg p-1 border border-gray-200 dark:border-gray-600">
                    <button className="px-3 py-1.5 text-xs font-medium rounded-md bg-gray-100 text-gray-500 dark:bg-transparent dark:text-gray-400 hover:text-gray-700 transition-colors" type="button">룰베이스</button>
                    <button className="px-3 py-1.5 text-xs font-bold rounded-md bg-primary text-white shadow-sm" type="button">추상적 정책 (AI/RAG)</button>
                    </div>
                </div> */}

                <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    정책 내용 설명 <span className="text-red-500">*</span>
                    </label>
                    <div className="rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary transition-all shadow-sm">
                    <div className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 p-2 flex gap-2">
                        <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500" type="button"><Bold size={16} /></button>
                        <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500" type="button"><Italic size={16} /></button>
                        <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500" type="button"><List size={16} /></button>
                        <button className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500" type="button"><Code size={16} /></button>
                    </div>
                    <textarea 
                        name="content"
                        value={newCompliance.content}
                        onChange={handleChange}
                        className="w-full border-0 bg-white dark:bg-gray-900 p-3 text-sm text-gray-700 dark:text-gray-200 focus:ring-0 min-h-[120px] outline-none" 
                        placeholder="정책의 상세 내용, 근거, 예외 사항 등을 상세히 기술하세요..."
                    ></textarea>
                    </div>
                </div>

                <div className="grid grid-cols-1 gap-6">
                    <div>
                    <label className="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                        태그
                    </label>
                    <input 
                        name="tag"
                        value={newCompliance.tag}
                        onChange={handleChange}
                        className="w-full rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 focus:border-primary focus:ring-primary/20 text-sm dark:text-white py-2.5 shadow-sm px-3 outline-none focus:ring-2 transition-all" 
                        placeholder="#python, #azure, #compliance (쉼표로 구분)" 
                        type="text"
                    />
                    </div>
                    <div className="bg-primary/5 rounded-lg p-4 border border-primary/20 flex flex-col md:flex-row items-center justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <div className="p-2 bg-white dark:bg-card-dark rounded-full shadow-sm text-primary">
                        <Share2 size={20} />
                        </div>
                        <div>
                        <h4 className="text-sm font-bold text-gray-900 dark:text-white">컨텍스트 정합성 검증</h4>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">현재 정책 내용이 기존 지식 그래프와 충돌하지 않는지 확인합니다.</p>
                        </div>
                    </div>
                    <button className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-card-dark border border-primary text-primary hover:bg-primary hover:text-white text-sm font-medium rounded-lg transition-all shadow-sm whitespace-nowrap group" type="button">
                        <RefreshCw size={16} className="group-hover:animate-spin" />
                        검증 실행
                    </button>
                    </div>
                </div>
            </form>
        </div>

        {/* Modal Footer */}
        <div className="p-6 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 rounded-b-xl flex justify-end gap-3 sticky bottom-0 z-10">
            <button 
            onClick={onClose}
            className="px-5 py-2.5 rounded-lg text-gray-600 dark:text-gray-300 font-medium text-sm hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
            >
            취소
            </button>
            <button 
            onClick={ApplyBtn}
            className="px-5 py-2.5 rounded-lg bg-primary hover:bg-teal-700 text-white font-bold text-sm shadow-md shadow-primary/20 hover:shadow-lg transition-all transform active:scale-95"
            >
            정책 등록
            </button>
        </div>
        
        </div>
    </div>
  );
};

export default AddComplianceModal;

