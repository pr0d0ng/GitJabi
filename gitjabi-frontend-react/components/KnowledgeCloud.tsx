import React, { useState, useEffect, useContext } from 'react';
import { 
  Upload, Network, TrendingUp, Database, BrainCircuit, 
  CheckCircle, Search, Plus, Minus, Scan, Shield, 
  FileText, ThumbsUp, ThumbsDown, Video,
  Crosshair, LayoutGrid, ChevronRight,
  Maximize
} from 'lucide-react';
import TeamsIntegrationModal from './modals/TeamsIntegrationModal';
import KnowledgeUploadModal from './modals/KnowledgeUploadModal';
import api, {host} from '../api/api'
import { AuthContext } from '../App';
import { toast } from 'react-hot-toast'; 
  
const auraStyle = `
@keyframes aura-pulse {
  0% { box-shadow: 0 0 0 0px rgba(16, 139, 119, 0.7); }
  70% { box-shadow: 0 0 0 15px rgba(16, 139, 119, 0); }
  100% { box-shadow: 0 0 0 0px rgba(16, 139, 119, 0); }
}
.animate-aura {
  animation: aura-pulse 2s infinite;
}
`;

const renderInlineStyles = (text: string) => {
  const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
  
  return parts.map((part, j) => {

    if (!part || part.length === 0) return null;

    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={j}>{part.slice(2, -2)}</strong>;
    }
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={j} className="ai-code">{part.slice(1, -1)}</code>;
    }
    
    const cleanedPart = part.replace(/\*\*/g, '');

    return cleanedPart === "" ? null : cleanedPart;
  }).filter(Boolean);
};

const renderFormattedAnswer = (text: string) => {
  if (!text) return null;
  
  const cleanText = text.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\u200B-\u200D\uFEFF]/g, "");

  return cleanText.split('\n').map((line, i) => {
    const trimmedLine = line.trim();
    
    if (!trimmedLine) return <div key={i} className="h-3" />;

    const isMarkdownHeader = trimmedLine.startsWith('###');
    const isSectionTitle = /^(?:\d+\.\s*)?(###\s*)?(관련 정책|상세 안내|권장 조치|핵심 발견 사항)/.test(trimmedLine);

    if (isMarkdownHeader || isSectionTitle) {
      
      const headerText = trimmedLine.replace(/^(?:\d+\.\s*)?(?:###\s*)?/, "").trim();
      return <h3 key={i} className="ai-header">{headerText}</h3>;
    }

    if (/^[*|-]\s+/.test(trimmedLine)) {
      const content = trimmedLine.replace(/^[*|-]+\s*/, '').trim();
      return (
        <li key={i} className="ml-5 list-disc mb-2 text-gray-700 dark:text-gray-300 font-sans">
          {renderInlineStyles(content)}
        </li>
      );
    }

    if (trimmedLine.startsWith('>')) {
      return (
        <blockquote key={i} className="ai-blockquote">
          {renderInlineStyles(trimmedLine.replace(/^>\s*/, ''))}
        </blockquote>
      );
    }

    return (
      <p key={i} className="mb-2 leading-relaxed text-gray-600 dark:text-gray-400">
        {renderInlineStyles(line)}
      </p>
    );
  });
};

const contentStyle = `
  /* 헤더: 초록띠와 그라데이션 배경 */
  .ai-content .ai-header {
    border-left: 4px solid #108b77 !important;
    padding-left: 1rem !important;
    background: linear-gradient(to right, rgba(16, 139, 119, 0.1), transparent) !important;
    margin: 1.5rem 0 0.8rem 0 !important;
    color: #108b77 !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    border-radius: 0 4px 4px 0 !important;
  }
  .ai-content strong {
    color: #108b77 !important;
    font-weight: 800 !important;
  }
  /* 코드블록: 파일명, 변수 등 강조 */
  .ai-content .ai-code {
    background-color: rgba(16, 139, 119, 0.05) !important;
    color: #0f766e !important;
    padding: 0.15rem 0.4rem !important;
    border-radius: 0.375rem !important;
    font-family: monospace !important;
    font-size: 0.9em !important;
    border: 1px solid rgba(16, 139, 119, 0.2) !important;
  }
  .dark .ai-content .ai-code {
    background-color: rgba(16, 139, 119, 0.2) !important;
    color: #5eead4 !important;
    border-color: rgba(16, 139, 119, 0.3) !important;
  }
  /* 인용구: 상세 안내 하단 박스 */
  .ai-content .ai-blockquote {
    border-left: 4px solid #cbd5e1 !important;
    background: #f8fafc !important;
    padding: 1rem !important;
    margin: 1.2rem 0 !important;
    border-radius: 0 0.75rem 0.75rem 0 !important;
    color: #475569 !important;
    font-style: italic !important;
    font-size: 0.95rem !important;
  }
  .dark .ai-content .ai-blockquote {
    border-left-color: #475569 !important;
    background: #1e293b !important;
    color: #cbd5e1 !important;
  }
`;

export const KnowledgeCloud: React.FC = () => {
  const { user } = useContext(AuthContext);

  const [isTeamsIntegrationModalOpen, setIsTeamsIntegrationModalOpen] = useState(false);
  
  // 1. 상태 변수 정의
  const [stats, setStats] = useState({
    total_nodes: "Loading...",
    graph_density: "0.89",
    ai_accuracy: "0%"
  });
  const [recentUpdates, setRecentUpdates] = useState<any[]>([]);
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [searchQuery, setSearchQuery] = useState("");
  const [aiAnswer, setAiAnswer] = useState<string>("질문을 입력하고 RAG 검색을 눌러보세요.");
  const [isSearching, setIsSearching] = useState(false);

  // 2. 줌 및 드래그 상태
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // 3. 데이터 로드 로직
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsRes, updatesRes, graphRes] = await Promise.all([
          fetch(`${host}/api/knowledge/stats`),
          fetch(`${host}/api/knowledge/recent-updates`),
          fetch(`${host}/api/knowledge/graph`)
        ]);
        setStats(await statsRes.json());
        setRecentUpdates(await updatesRes.json());
        setGraphData(await graphRes.json());
      } catch (err) {
        console.error("데이터 동기화 실패:", err);
      }
    };
    fetchData();
  }, []);

  // 4. 이벤트 핸들러 및 헬퍼 함수 (에러가 났던 부분!)
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
  };
  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };
  const handleMouseUp = () => setIsDragging(false);

  // 자연스러운 나선형 배치를 위한 함수
  const getOrganicPos = (idx: number) => {
    const angle = idx * 2.4; 
    const distance = 8 + idx * 3.5; // 인덱스에 따라 서서히 멀어지게 설정
    return { 
      x: 50 + distance * Math.cos(angle), 
      y: 50 + distance * Math.sin(angle) 
    };
  };

  const focusOnNode = (nodeId: string) => {
    if (!nodeId || !graphContainerRef.current) return;

    // 노드 찾기 (문자열 비교 시 공백 제거 및 대소문자 통일로 정합성 강화)
    const targetIdx = graphData.nodes.findIndex(
      (n: any) => 
        n.id?.toString().trim() === nodeId.toString().trim() || 
        n.node_id?.toString().trim() === nodeId.toString().trim()
    );

    if (targetIdx === -1) {
      console.warn(`⚠️ 포커싱 실패: '${nodeId}'를 찾지 못함. 현재 로드된 노드 수: ${graphData.nodes.length}`);
      return;
    }

    const pos = getOrganicPos(targetIdx);
    const container = graphContainerRef.current;
    const { width, height } = graphContainerRef.current.getBoundingClientRect();
    const targetZoom = 1.2;

    // 1. 노드의 픽셀 위치
    const nodePixelX = (pos.x / 100) * width;
    const nodePixelY = (pos.y / 100) * height;

    // 2. 중앙점(center)과의 거리 차이에 줌 배율을 곱해야 정확히 중앙에 꽂힙니다.
    // 공식: (중앙 - 노드위치) * 줌
    const finalX = (width / 2 - nodePixelX) * targetZoom;
    const finalY = (height / 2 - nodePixelY) * targetZoom;

    setZoom(targetZoom);
    setOffset({ x: finalX, y: finalY });
    
    console.log(`노드 '${nodeId}' 타겟팅 완료`);
  };

  const [relatedNodes, setRelatedNodes] = useState<string[]>([]);

  const handleSearch = async () => {
    console.log('Search starts...');
    if (!searchQuery) return;
    
    setIsSearching(true);
    setAiAnswer("AI가 지식 베이스를 분석 중입니다...");

    // 1. 타임아웃 설정을 위한 AbortController 생성 (60초)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000); 

    try {
      // 2. 기본 fetch 사용
      const token = localStorage.getItem('accessToken');
        if (!token) {
            console.error("토큰이 없습니다. 로그인이 필요합니다.");
            toast.error("토근이 없습니다. 재로그인 해주세요.")
            return;
        }
      const response = await fetch(`${host}/api/knowledge/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        credentials: 'include',
        body: JSON.stringify({ query: searchQuery }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`서버 오류: ${response.status}`);
      }

      const data = await response.json();
      setAiAnswer(data.answer);
      if (data.related_ids) {
        setRelatedNodes(data.related_ids);

        setGraphData(prev => ({
          ...prev,
          related_ids: data.related_ids 
        }));
      }

      if (data.related_ids && data.related_ids.length > 0) {
          setTimeout(() => {
          focusOnNode(data.related_ids[0]);
        }, 100);
      }

    } catch (error) {
      toast.error(`${error}`)
      if (error.name === 'AbortError') {
        setAiAnswer("요청 시간이 초과되었습니다. 다시 시도해주세요 (60초 초과).");
      } else {
        console.error("검색 에러:", error);
        setAiAnswer("지식 베이스 분석 중 오류가 발생했습니다.");
      }
    } finally {
      setIsSearching(false);
    }
  };
  

  // 노드 클릭 시 상세 정보 표시 
  const [selectedNodeContent, setSelectedNodeContent] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<any | null>(null);
  const graphContainerRef = React.useRef<HTMLDivElement>(null);

  // 휠 이벤트 핸들러 추가
  const handleWheel = (e: React.WheelEvent) => {
    // 지식 그래프 영역 내부에서만 작동 (부모 스크롤 방지)
    e.stopPropagation();
    
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(prev => Math.min(Math.max(prev + delta, 0.08), 3));
  };

  // 노드 클릭 핸들러 (내용 조회)
  const handleNodeClick = (node: any) => {
    
    setAiAnswer(`[지식 정보: ${node.title}]\n\nID: ${node.id}\n태그: ${node.tags.join(', ')}\n\n이 노드를 클릭하셨습니다. 관련 정책 전문은 지식 베이스에서 조회 가능합니다.`);
  };

  const [isFullscreen, setIsFullscreen] = useState<boolean>(false);

  useEffect(() => {
    const container = graphContainerRef.current;
    if (!container) return;

    const handleWheelNative = (e: WheelEvent) => {
      e.preventDefault(); 
      const delta = e.deltaY > 0 ? -0.1 : 0.1;
      setZoom(prev => Math.min(Math.max(prev + delta, 0.08), 3));
    };

    container.addEventListener('wheel', handleWheelNative, { passive: false });
    return () => container.removeEventListener('wheel', handleWheelNative);
  }, [isFullscreen]); 

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  
  // 그래프 밀도 계산 로직
  const calculateDensity = () => {
    const V = graphData.nodes.length;
    const E = graphData.links.length;
    
    if (V <= 1) return "0.00%";
    
    // 무방향 그래프 밀도 공식: E / [V(V-1)/2]
    const density = E / (V * (V - 1) / 2);
    
    // 100을 곱해 퍼센트로 변환하고 소수점 둘째 자리까지 표기
    return `${(density * 100).toFixed(2)}%`;
  };

  return (
    <div className="flex flex-col h-full bg-background-light dark:bg-background-dark text-gray-900 dark:text-gray-100 font-sans">
      <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 w-full space-y-8 custom-scrollbar">
        <div className="max-w-8xl mx-auto space-y-8">
          
          {/* 홈 / 지식 클라우드 Breadcrumb */}
          <nav className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-widest text-gray-400">
            <LayoutGrid size={12} />
            <span>홈</span>
            <ChevronRight size={12} />
            <span className="text-primary">지식 클라우드</span>
          </nav>

          {/* Header */}
          <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">지식 클라우드</h1>
              <p className="text-gray-500 dark:text-gray-400 text-sm mt-1">조직의 컴플라이언스 및 코드 지식 베이스를 관리하세요.</p>
            </div>
            <button 
              onClick={() => setIsUploadModalOpen(true)}
              className="inline-flex items-center justify-center px-5 py-2.5 rounded-lg text-white bg-primary hover:bg-primary/90 transition-all shadow-sm"
            >
              <Upload size={18} className="mr-2" /> 지식 데이터 분석 및 등록
            </button>
          </section>

          {/* KPI Stats */}
          <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm relative overflow-hidden group">
              <div className="absolute top-4 right-4 p-2 bg-primary/5 rounded-lg text-primary group-hover:scale-110 transition-transform">
                <Database size={20} />
              </div>
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">총 지식 노드 수</h3>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-3xl font-bold">{stats.total_nodes}</span>
                <span className="text-sm text-primary flex items-center font-medium"><TrendingUp size={14} className="mr-1"/> +12%</span>
              </div>
            </div>

            <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm relative overflow-hidden group">
              <div className="absolute top-4 right-4 p-2 bg-blue-500/5 rounded-lg text-blue-500 group-hover:scale-110 transition-transform">
                <Network size={20} />
              </div>
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">그래프 밀도</h3>
              <div className="flex items-baseline gap-2 mt-2">
                <span className="text-3xl font-bold">{calculateDensity()}</span>
                <span className="text-sm text-blue-500 font-medium">유기적 연결</span>
              </div>
            </div>

            <div className="bg-card-light dark:bg-card-dark rounded-xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm relative overflow-hidden group">
              <div className="absolute top-4 right-4 p-2 bg-green-500/5 rounded-lg text-green-500 group-hover:scale-110 transition-transform">
                <BrainCircuit size={20} />
              </div>
              <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">지식 활성화율</h3>
              <div className="flex items-baseline gap-2 mt-2">
                {/* <span className="text-3xl font-bold">{stats.ai_accuracy}</span> */}
                <span className="text-3xl font-bold">99.8%</span>
                <span className="text-sm text-green-500 font-medium">안정적</span>
              </div>
            </div>
          </section>

          {/* Search & Graph Section */}
          <section className="space-y-6">
            <div className="relative group">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 group-focus-within:text-primary transition-colors" size={24} />
              <input 
                className="block w-full pl-12 pr-32 py-4 bg-card-light dark:bg-card-dark border border-gray-200 dark:border-gray-700 rounded-xl text-lg focus:outline-none focus:ring-2 focus:ring-primary shadow-sm" 
                placeholder="컴플라이언스 정책에 대해 물어보세요..." 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <button onClick={handleSearch} disabled={isSearching} className="absolute right-3 top-1/2 transform -translate-y-1/2 bg-primary text-white px-4 py-2 rounded-lg font-bold hover:bg-primary/90 disabled:opacity-50 transition-all">
                {isSearching ? "분석 중..." : "RAG 검색"}
              </button>
            </div>

            <div className={`grid grid-cols-1 lg:grid-cols-12 gap-6 ${
              isFullscreen 
                ? 'fixed inset-4 z-[150] bg-white/70 dark:bg-[#0a1513]/70 backdrop-blur-xl p-8 shadow-2xl rounded-3xl border border-gray-200 dark:border-gray-800' 
                : 'lg:h-[600px] h-auto'
            }`}>
              {isFullscreen && (
                <div className="absolute inset-0 -z-10 backdrop-blur-2xl rounded-3xl" />
              )}
              {/* [Left] Interactive Graph */}
              <div className={`${isFullscreen ? 'col-span-12 h-full' : 'lg:col-span-7'} bg-card-light dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col overflow-hidden relative`}>
                {isFullscreen && (
                  <button 
                    onClick={() => setIsFullscreen(false)} 
                    className="absolute top-6 right-6 z-50 p-2 bg-gray-100 dark:bg-gray-800 rounded-full hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                  >
                    <Plus size={28} className="rotate-45 text-gray-500 hover:text-red-500" />
                  </button>
                )}
                <div className="absolute top-4 left-4 z-40 bg-white/90 dark:bg-black/50 px-3 py-1 rounded-full text-xs font-medium border border-gray-200">실시간 지식 관계망</div>
                <div className="absolute bottom-4 right-4 z-40 flex flex-col gap-2">
                  <button onClick={() => setZoom(z => Math.min(z + 0.2, 3))} className="bg-white dark:bg-gray-800 p-2 rounded shadow border hover:text-primary"><Plus size={18} /></button>
                  <button onClick={() => setZoom(z => Math.max(z - 0.2, 0.5))} className="bg-white dark:bg-gray-800 p-2 rounded shadow border hover:text-primary"><Minus size={18} /></button>
                  <button onClick={() => {setZoom(0.8); setOffset({x:0, y:0})}} title="중앙으로 정렬" className="bg-white dark:bg-gray-800 p-2 rounded shadow border hover:text-primary"><Crosshair size={18} /></button>
                  {!isFullscreen && (
                    <button 
                      onClick={() => setIsFullscreen(true)} 
                      title="크게 보기" 
                      className="bg-white dark:bg-gray-800 p-2 rounded-lg shadow border hover:text-primary"
                    >
                      <Maximize size={18} />
                    </button>
                  )}
                </div>
                <div
                  ref={graphContainerRef} 
                  className="flex-grow w-full h-full relative bg-gray-50 dark:bg-[#0a1513] overflow-hidden cursor-grab active:cursor-grabbing"
                  style={{
                    backgroundImage: `
    linear-gradient(to right, rgba(16, 139, 119, 0.05) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(16, 139, 119, 0.05) 1px, transparent 1px)
  `,
  backgroundSize: '40px 40px', 
  backgroundPosition: 'center'
                  }}
                  onMouseDown={handleMouseDown} 
                  onMouseMove={handleMouseMove} 
                  onMouseUp={handleMouseUp} 
                  onMouseLeave={handleMouseUp}
                >
                  <div style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`, transformOrigin: 'center', transition: isDragging ? 'none' : 'transform 0.1s' }} className="w-full h-full relative">
                    <svg className="absolute inset-0 w-full h-full pointer-events-none z-10 overflow-visible">
                      {graphData.links.map((link, idx) => {
                        const sIdx = graphData.nodes.findIndex(n => (n as any).id === link.source);
                        const tIdx = graphData.nodes.findIndex(n => (n as any).id === link.target);
                        if (sIdx === -1 || tIdx === -1) return null;
                        const sP = getOrganicPos(sIdx); const tP = getOrganicPos(tIdx);
                        return <line key={idx} x1={`${sP.x}%`} y1={`${sP.y}%`} x2={`${tP.x}%`} y2={`${tP.y}%`} stroke="#108b77" strokeWidth={1.2/zoom} strokeOpacity="0.3" />;
                      })}
                    </svg>

                    {graphData.nodes.map((node: any, idx) => {
                      const pos = getOrganicPos(idx);
                      const ishighlighted = graphData.related_ids?.includes(node.node_id) || graphData.related_ids?.includes(node.id) ; // 검색 결과에 포함된 노드인지 확인
                      return (
                        <div 
                          key={node.id} 
                          className="absolute flex flex-col items-center group cursor-pointer" 
                          style={{ left: `${pos.x}%`, top: `${pos.y}%`, transform: 'translate(-50%, -50%)', zIndex: 10 }}
                          onMouseEnter={(e) => e.currentTarget.style.zIndex = "100"}
                          onMouseLeave={(e) => e.currentTarget.style.zIndex = "10"}
                          onClick={() => setSelectedNode(node)} 
                        >
                          <style>{auraStyle}</style>
                          <div className={`rounded-full flex items-center justify-center border-2 bg-white dark:bg-gray-800 shadow-md transition-all group-hover:scale-125 group-hover:border-primary ${ishighlighted ? 'w-12 h-12 border-primary animate-aura' : 'w-9 h-9 border-gray-300 dark:border-gray-600'}`}>
                            <Shield className={ishighlighted ? "text-primary" : "text-gray-400 dark:text-gray-500"} size={ishighlighted ? 20 : 16} />
                          </div>
                          <span className="mt-1 bg-white/80 dark:bg-gray-800/80 dark:text-gray-200 px-2 py-0.5 rounded text-[9px] font-bold truncate max-w-[80px] shadow-sm">
                            {node.title.length > 10 ? node.title.slice(0, 10) + "..." : node.title}
                          </span>
                          
                          {/* 툴팁 (개별 노드에 호버시에만 등장) */}
                          <div className="absolute bottom-full mb-3 scale-0 group-hover:scale-100 transition-all origin-bottom z-[200] pointer-events-none">
                            <div className="bg-gray-900/95 text-white p-3 rounded-lg shadow-2xl w-64 border border-gray-700 backdrop-blur-sm relative">
                              <p className="font-bold text-primary text-[11px] mb-1">{node.title}</p>
                              <div className="flex flex-wrap gap-1 mb-2">
                                {node.tags && node.tags.map((tag: string) => <span key={tag} className="bg-primary/20 text-primary px-1.5 py-0.5 rounded text-[8px]">#{tag}</span>)}
                              </div>
                              <p className="text-[10px] text-gray-300 border-t border-gray-700 pt-2 leading-relaxed">
                                ID: {node.policy_id}<br/>클릭하여 상세 내용을 확인하세요.
                              </p>
                            </div>
                            <div className="absolute left-1/2 -bottom-1 -translate-x-1/2 w-2 h-2 bg-gray-900 rotate-45 mx-auto -mt-1 border-r border-b border-gray-700"></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              {/* [Right] AI Answer */}
              {!isFullscreen && (
              <div className="lg:col-span-5 bg-card-light dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm flex flex-col overflow-hidden">
                <div className="p-5 border-b flex justify-between items-center bg-gray-50/50 dark:bg-gray-800/20">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full bg-primary ${isSearching ? 'animate-pulse' : ''}`}></span>
                    <h3 className="font-semibold text-gray-900 dark:text-white">컨텍스트 답변</h3>
                  </div>
                  <span className="text-xs text-gray-400 font-mono">ID: #RAG-LIVE</span>
                </div>
                <div className="p-6 flex-grow overflow-y-auto custom-scrollbar min-h-0">
                  <style>{contentStyle}</style>
                  <div className="prose prose-sm dark:prose-invert max-w-none ai-content">
                    <div className="text-gray-600 dark:text-gray-300 leading-relaxed">
                      {renderFormattedAnswer(aiAnswer)}
                    </div>
                  </div>
                </div>
                <div className="p-4 border-t bg-gray-50/50 dark:bg-gray-800/20 flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-500">도움이 되었나요?</span>
                  <div className="flex gap-2">
                    <button className="p-2 rounded-lg text-gray-400 hover:text-green-500 transition-colors"><ThumbsUp size={18} /></button>
                    <button className="p-2 rounded-lg text-gray-400 hover:text-red-500 transition-colors"><ThumbsDown size={18} /></button>
                  </div>
                </div>
              </div>
              )}
            </div>
          </section>

          {/* Recent Updates Table */}
          <section className="pb-12">
            <h2 className="text-lg font-bold mb-4">최근 지식 업데이트</h2>
            <div className="bg-card-light dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden shadow-sm overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 dark:bg-gray-800/50 text-xs font-medium text-gray-500 uppercase">
                  <tr>
                    <th className="px-6 py-3 text-left">소스 유형</th>
                    <th className="px-6 py-3 text-left">문서명</th>
                    <th className="px-6 py-3 text-left">처리 일시</th>
                    <th className="px-6 py-3 text-left">상태</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 text-sm">
                  {recentUpdates.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          {item.source_type === 'DOCUMENT' ? <FileText className="text-red-400 mr-2" size={16} /> : <Video className="text-blue-500 mr-2" size={16} />}
                          <span className="font-medium">{item.source_type === 'DOCUMENT' ? 'PDF 문서' : 'Teams 회의'}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex flex-col">
                          <span className="font-medium">{item.title}</span>
                          <span className="text-xs text-gray-400">{item.policy_id}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-gray-500">{item.created_at ? new Date(item.created_at).toLocaleString() : '-'}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-0.5 text-xs font-semibold rounded-full ${item.status === 'PROPOSED' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                          {/* {item.status === 'ACTIVE' ? '승인 완료' : '검토 중'} */}
                          
                          {/* 개발 테스트 환경에서 일단 PROPSED를 승인으로 임시로 설정. */}
                          {item.status === 'PROPOSED' ? '승인 완료' : '검토 중'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <TeamsIntegrationModal isOpen={isTeamsIntegrationModalOpen} onClose={() => setIsTeamsIntegrationModalOpen(false)} />
        </div>
      </main>
      {/* 지식 상세 정보 팝업 모달 */}
        {selectedNode && (
          <div className="fixed inset-0 z-[1000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setSelectedNode(null)}>
            <div 
              className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-lg w-full overflow-hidden border border-gray-200 dark:border-gray-700 animate-in fade-in zoom-in duration-200"
              onClick={(e) => e.stopPropagation()} 
            >
              <div className="p-6 space-y-4">
                <div className="flex justify-between items-start">
                  <div className="space-y-1">
                    <h3 className="text-xl font-bold text-primary dark:text-white leading-tight">{selectedNode.title}</h3>
                    <p className="text-xs font-mono text-gray-500">ID: {selectedNode.policy_id}</p>
                  </div>
                  <button onClick={() => setSelectedNode(null)} className="p-1 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors text-gray-400">
                    <Plus size={24} className="rotate-45" /> {/* 닫기 아이콘 대용 */}
                  </button>
                </div>

                <div className="flex flex-wrap gap-2">
                  {selectedNode.tags?.map((tag: string) => (
                    <span key={tag} className="bg-primary/10 text-primary text-[10px] font-bold px-2 py-1 rounded-md">#{tag}</span>
                  ))}
                </div>

                <div className="border-t border-gray-100 dark:border-gray-800 pt-4">
                  <h4 className="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">상세 가이드라인</h4>
                  <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 max-h-64 overflow-y-auto custom-scrollbar">
                    <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
                      {selectedNode.content || "해당 노드의 상세 정책 본문 내용을 데이터베이스에서 불러오는 중입니다. 잠시만 기다려 주세요."}
                    </p>
                  </div>
                </div>
                <div className="flex justify-end pt-2">
                  <button onClick={() => setSelectedNode(null)} className="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 rounded-lg text-sm font-bold hover:bg-gray-200 transition-colors">닫기</button>
                </div>
              </div>
            </div>
          </div>
        )}
        {/* 지식 데이터 업로드 모달 */}
        <KnowledgeUploadModal 
        isOpen={isUploadModalOpen} 
        onClose={() => setIsUploadModalOpen(false)} 
      />
    </div>
  );
};