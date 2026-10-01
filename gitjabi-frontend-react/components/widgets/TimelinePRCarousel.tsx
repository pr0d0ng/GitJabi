import { useRef, useState } from "react";
import { ChevronLeft, ChevronRight, GitCommit, FileCode, Plus, AlertCircle, Calendar, GitPullRequest, Info, X } from "lucide-react";

import api from '../../api/api'


export default function PRCarousel({ currentCR, onAddPR }) {
  const scrollContainerRef = useRef(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [availablePRs, setAvailablePRs] = useState([]); // API에서 불러올 미연결 PR 목록

  console.log(availablePRs)
  // 1. 미연결 PR 목록 불러오기 (API 호출)
  const fetchAvailablePRs = async () => {
    const res = await api.get('/api/dashboard/change-request/unlinked-prs');
    setAvailablePRs(res.data);
    setIsModalOpen(true);
  };

  const scrollLeft = () => scrollContainerRef.current?.scrollBy({ left: -360, behavior: "smooth" });
  const scrollRight = () => scrollContainerRef.current?.scrollBy({ left: 360, behavior: "smooth" });


  /**
   * 특정 PR을 현재 CR에 연결하는 함수
   * @param {string} prId - 연결할 Pull Request의 ID
   */
  const handleLinkPR = async (prId) => {
    // 1. 로딩 상태 시작 (버튼 비활성화 등)
    setIsFetching(true); 

    try {
      // FastAPI 경로 매개변수 {cr_id}와 쿼리 매개변수 pr_id 전달
      const response = await api.post(`/api/dashboard/change-request/${currentCR.id}/link-pr`, null, {
        params: { pr_id: prId }
      });

      if (response.data.status === 'success') {
        console.log(`PR #${prId} 연결 성공!`);
        
        // 4. 데이터 최신화
        await onAddPR(); 
        
        setIsModalOpen(false);
        
        // toast.success("PR이 성공적으로 연결되었습니다.");
      }
    } catch (error) {
      console.error('PR 연결 중 오류 발생:', error);
      // 에러 피드백
      alert(error.response?.data?.detail || "PR 연결에 실패했습니다. 로그를 확인하세요.");
    } finally {
      setIsFetching(false);
    }
  };

  return (
    <div className="relative w-full">
      {/* Navigation Buttons */}
      <button onClick={scrollLeft} className="absolute left-0 top-1/2 -translate-y-1/2 z-10 bg-white/80 dark:bg-gray-900/80 border border-gray-200 dark:border-gray-700 rounded-full p-2 shadow-lg hover:scale-110 transition"><ChevronLeft size={20} /></button>
      <button onClick={scrollRight} className="absolute right-0 top-1/2 -translate-y-1/2 z-10 bg-white/80 dark:bg-gray-900/80 border border-gray-200 dark:border-gray-700 rounded-full p-2 shadow-lg hover:scale-110 transition"><ChevronRight size={20} /></button>

      <div ref={scrollContainerRef} className="flex overflow-x-auto gap-5 pb-8 snap-x snap-mandatory scroll-smooth no-scrollbar ml-4 mr-4">
        
        {/* 기존 PR 카드 렌더링 */}
        {currentCR.technical.pullRequests.map((pr) => (
          <div key={pr.id} className="snap-start min-w-[340px] p-6 rounded-2xl border border-gray-100 dark:border-gray-700 bg-white dark:bg-gray-800/40 hover:border-primary/40 transition-all group">
            <div className="flex justify-between items-center mb-6">
              <span className="text-[10px] font-black text-primary px-2 py-1 bg-primary/5 rounded-lg border border-primary/10 uppercase tracking-tighter">PR #{pr.prNum || pr.id}</span>
              <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full
                 ${pr.status === "PENDING" ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600"}`}>
                  LINKED {/* {pr.status} */}
                </span>
            </div>
            <div className="mb-6 h-12">
              <p className="text-xs font-bold text-gray-400 mb-1">
                <a href={pr.pr_html_url} target="_blank" rel="noopener ref">{pr.repo}</a>
              </p>
              <p className="text-sm font-black text-gray-900 dark:text-white truncate">
                {pr.branch}</p>
            </div>
            <div className="grid grid-cols-3 gap-3 pt-5 border-t border-gray-50 dark:border-gray-700">
              <div className="text-center">
                <p className="text-[10px] font-bold text-gray-400 mb-1 uppercase tracking-tighter">Target</p>
                <div className="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center justify-center gap-1">
                  <GitCommit size={12} />{pr.stats.target}</div>
              </div>
              <div className="text-center border-x border-gray-50 dark:border-gray-700 px-2">
                <p className="text-[10px] font-bold text-gray-400 mb-1 uppercase tracking-tighter">Additions</p>
                <div className="text-sm font-bold text-gray-700 dark:text-gray-300 flex items-center justify-center gap-1">
                  <Plus size={12} />{pr.stats.addition}</div>
              </div>
              <div className="text-center">
                <p className="text-[10px] font-bold text-gray-400 mb-1 uppercase tracking-tighter">
                  Language</p>
                <p className="text-sm font-bold text-teal-500">
                  {pr.stats.language}</p>
              </div>
            </div>
          </div>
        ))}

        {/* 2. PR 추가 스켈레톤 카드 (맨 우측 배치) */}
        <button
          onClick={fetchAvailablePRs}
          className="snap-start min-w-[340px] min-h-60 flex flex-col items-center justify-center p-6 rounded-2xl border-2 border-dashed border-gray-200 dark:border-gray-700 bg-gray-50/50 dark:bg-gray-800/20 hover:border-primary/50 hover:bg-primary/5 transition-all group"
        >
          <div className="w-12 h-12 rounded-full bg-white dark:bg-gray-800 shadow-sm flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
            <Plus className="text-gray-400 group-hover:text-primary" />
          </div>
          <p className="text-sm font-bold text-gray-500 group-hover:text-primary">New Pull Request</p>
          <p className="text-[10px] text-gray-400 mt-1 uppercase tracking-tighter">Click to link additional PR</p>
        </button>
      </div>


      {/* 3. PR 선택 모달 */}
      {isModalOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-gray-900 w-full max-w-2xl rounded-[32px] p-8 shadow-2xl border border-gray-100 dark:border-gray-800 animate-in fade-in zoom-in duration-200">
            
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="text-2xl font-black text-gray-900 dark:text-white mb-1">Link Pull Request</h3>
                <p className="text-sm text-gray-500">현재 CR 거버넌스 검증에 포함할 PR을 선택하세요.</p>
              </div>
              <button 
                onClick={() => setIsModalOpen(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition"
              >
                <X size={20} className="text-gray-400" />
              </button>
            </div>

            {/* 테이블 헤더 영역 */}
            <div className="grid grid-cols-12 px-4 py-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl mb-2 text-[10px] font-black text-gray-400 uppercase tracking-widest">
              <div className="col-span-2">PR Info</div>
              <div className="col-span-7">Repository</div>
              {/* <div className="col-span-3 text-center">Status</div> */}
              <div className="col-span-3 text-right">Created At</div>
            </div>

            {/* 데이터 영역 */}
            <div className="space-y-1 max-h-[400px] overflow-y-auto pr-2 mb-8 custom-scrollbar">
              {availablePRs.length > 0 ? (
                availablePRs.map((pr) => (
                  <div 
                    key={pr.pr_id}
                    onClick={() => {
                      const isConfirmed = window.confirm(`${pr.repo_name} [PR #${pr.pr_number}]를 현재 CR에 연결하시겠습니까?`);
                      if (isConfirmed) {
                        handleLinkPR(pr.pr_id); 
                        setIsModalOpen(false); 
                      }
                    }}
                    className="grid grid-cols-12 items-center px-4 py-4 rounded-xl border border-transparent hover:border-primary/20 hover:bg-primary/5 cursor-pointer transition-all group"
                  >
                    {/* ID & Mandatory */}
                    <div className="col-span-2 flex items-center gap-2">
                      <span className="text-sm font-black text-gray-900 dark:text-white">#{pr.pr_number}</span>
                      {pr.is_mandatory && (
                        <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" title="Mandatory" />
                      )}
                    </div>

                    {/* Repo Name */}
                    <div className="col-span-7">
                      <p className=" text-sm font-bold text-gray-700 dark:text-gray-300 truncate group-hover:text-primary transition-colors">
                        {pr.repo_name}
                      </p>
                      <div className="flex items-center gap-1 text-[10px] text-gray-400">
                        <Info size={10} />
                        <span>ID: {pr.pr_id}</span>
                      </div>
                    </div>

                    {/* Status Badge */}
                    {/* <div className="col-span-3 flex justify-center">
                      <span className={`text-[10px] font-black px-2.5 py-1 rounded-lg border ${
                        pr.status === 'APPROVED' 
                        ? 'bg-emerald-50 text-emerald-600 border-emerald-100' 
                        : 'bg-orange-50 text-orange-600 border-orange-100'
                      }`}>
                        {pr.status.toUpperCase()}
                      </span>
                    </div> */}

                    {/* Date */}
                    <div className="col-span-3 text-right">
                      <div className="flex items-center justify-end gap-1.5 text-xs font-medium text-gray-500">
                        <Calendar size={12} className="text-gray-400" />
                        {pr.created_at}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                /* 데이터가 0개일 때 표시될 Empty State */
                <div className="py-20 flex flex-col items-center justify-center border-2 border-dashed border-gray-100 dark:border-gray-800 rounded-2xl">
                  <GitPullRequest size={48} className="text-gray-200 dark:text-gray-700 mb-4" />
                  <p className="text-sm font-bold text-gray-400">연결 가능한 Pull Request가 없습니다.</p>
                  <p className="text-xs text-gray-400 mt-1">모든 PR이 이미 다른 CR에 연결되어 있거나 생성된 PR이 없습니다.</p>
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <button 
                onClick={() => setIsModalOpen(false)}
                className="flex-1 py-4 bg-gray-100 dark:bg-gray-800 rounded-2xl font-bold text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700 transition"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}