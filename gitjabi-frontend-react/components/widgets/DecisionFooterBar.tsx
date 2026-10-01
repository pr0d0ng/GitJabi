
import React, { useState, useContext } from 'react';
import { Bold, Code, Flag, Ban, Check, Loader2, ShieldAlert } from "lucide-react";
import { toast } from 'react-hot-toast'; 
import api from '../../api/api'
import { AuthContext } from '../../App';

export default function CRDecisionFooter({ currentCR, onRefresh }) {
  const { user } = useContext(AuthContext)

  const [comment, setComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isAssignedApprover = currentCR?.decision?.some(
    (d) => 
      d.name === user.username && 
      d.status === 'PENDING'
  );
  const isStageReady = currentCR.currentStage >= 5;
  const isStatusActive = currentCR.status === 'IN_PROGRESS'; 

  const isActionable = isAssignedApprover && isStageReady && isStatusActive;

  const getDisabledReason = () => {
    if (!isStatusActive) return "이미 처리가 완료되었거나 대기중인 요청건입니다.";
    if (!isStageReady) return "시스템 분석이 진행 중입니다. 잠시만 기다려주세요.";
    if (!isAssignedApprover) return "귀하는 이 요청에 대한 의사 결정권자가 아니거나 이미 의사결정을 완료했습니다.";
    return "";
  };

  const handleDecision = async (status) => {
    let mapping = {
        'REJECTED': '거절',
        'APPROVED': '승인',
        'EXCEPTION': '예외 처리'
    }
    if (!comment) {
      toast.error("사유를 반드시 입력해주세요.");
      return;
    }

    if (!window.confirm(`정말로 이 CR을 ${mapping[status] || status}하시겠습니까?`)) {
      return;
    }

    setIsSubmitting(true);

    try {
        try {
            const payload = {
                approver_name: user.username,
                approver_role: user.role,
                status: status, 
                comment: comment || "" 
            };
            console.log(payload);
            const response = await api.post(`/api/dashboard/change-request/${currentCR.id}/decision`, payload);
            toast.success(response.data.message);
            setComment(""); // 입력창 초기화
            if (onRefresh) onRefresh(); // 상위 컴포넌트 데이터 갱신
        } catch (error) {
            if (error.response?.status === 422) {
                console.error("Validation Error Details:", error.response.data.detail);
            }
        } 
    } catch (error) {
      console.error(error);
      const errorMsg = error.response?.data?.detail || "의사결정 처리 중 오류가 발생했습니다.";
      toast.error(errorMsg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <footer className="absolute bottom-0 left-0 right-0 bg-white/95 dark:bg-gray-900/95 backdrop-blur-md border-t border-gray-200 dark:border-gray-700 p-6 z-20 shadow-[0_-5px_20px_rgba(0,0,0,0.03)]">
      <div className="max-w-5xl mx-auto flex flex-col md:flex-row gap-6 items-start md:items-end">
        
        {/* 입력 영역 */}
        <div className="flex-1 w-full">
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wide">
              의사 결정 입력
            </label>
            {/* 권한이 없을 경우 경고 라벨 표시 */}
            {!isAssignedApprover && isStatusActive && (
              <span className="flex items-center gap-2 py-1 text-[13px] font-bold text-orange-500 bg-orange-50 dark:bg-orange-950/30 px-2 py-0.5 rounded">
                <ShieldAlert size={12} /> 의사 결정 불가
              </span>
            )}
          </div>

          <div className="relative group">
            <textarea 
              className={`w-full border rounded-lg p-3 text-sm transition-all resize-none shadow-inner outline-none
                ${isActionable 
                  ? "bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 focus:ring-2 focus:ring-primary/20 focus:border-primary" 
                  : "bg-gray-100 dark:bg-gray-800/50 border-gray-200 dark:border-gray-800 text-gray-400 cursor-not-allowed"
                }`} 
              placeholder={isActionable ? "피드백 또는 지시 사항을 입력하세요." : getDisabledReason()} 
              rows={2}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              disabled={!isActionable || isSubmitting}
            ></textarea>
            
            {isActionable && (
              <div className="absolute bottom-2 right-2 flex gap-1 opacity-50 group-hover:opacity-100 transition-opacity">
                <button className="p-1.5 text-gray-400 hover:text-primary transition-colors rounded hover:bg-primary/10"><Bold size={16} /></button>
                <button className="p-1.5 text-gray-400 hover:text-primary transition-colors rounded hover:bg-primary/10"><Code size={16} /></button>
              </div>
            )}
          </div>
        </div>

        {/* 액션 버튼 영역 */}
        <div className="flex gap-3 shrink-0">
          <button 
            onClick={() => handleDecision('EXCEPTION')}
            className="px-5 py-2.5 rounded-lg border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 font-semibold text-sm hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50 disabled:grayscale"
            disabled={!isActionable || isSubmitting}
          >
            <Flag size={18} /> 예외 처리
          </button>
          
          <button 
            onClick={() => handleDecision('REJECTED')}
            className="px-5 py-2.5 rounded-lg bg-white dark:bg-gray-800 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400 font-bold text-sm hover:bg-red-50 dark:hover:bg-red-900/20 hover:border-red-500 hover:shadow-md transition-all flex items-center gap-2 shadow-sm disabled:opacity-50"
            disabled={!isActionable || isSubmitting}
          >
            <Ban size={18} /> 거절
          </button>
          
          <button 
            onClick={() => handleDecision('APPROVED')}
            className="px-8 py-2.5 rounded-lg bg-primary text-white font-bold text-sm hover:bg-teal-700 hover:shadow-lg hover:shadow-primary/20 transition-all flex items-center gap-2 shadow-md disabled:opacity-50"
            disabled={!isActionable || isSubmitting}
          >
            {isSubmitting ? <Loader2 size={18} className="animate-spin" /> : <Check size={18} />}
            승인
          </button>
        </div>
      </div>
    </footer>
  );
}