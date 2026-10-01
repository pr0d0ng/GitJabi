import React, {useState, useEffect, useContext} from 'react';
import { 
  LayoutDashboard, 
  FileText, 
  ShieldCheck, 
  Share2, 
  BarChart2, 
  FileCheck, 
  Settings, 
  Hexagon,
  Scale,
  LogOut,
  Menu, X
} from 'lucide-react';
import { ViewType } from '../types';
import Logo from '../assets/logo.png';
import { AuthContext } from '../App';

interface SidebarProps {
  currentView: ViewType;
  setCurrentView: (view: ViewType) => void;
  // onLogout: () => void; 
  // user: { name: string; role: string; } | null;
}


export const Sidebar: React.FC<SidebarProps> = ({ currentView, setCurrentView }) => {
  const { user, handleLogout } = useContext(AuthContext);

  const [isOpen, setIsOpen] = useState(false); // 모바일 사이드바 열림 상태
  const toggleSidebar = () => setIsOpen(!isOpen);

  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // 리사이즈 감지하여 모바일 여부 실시간 업데이트
  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const desktopClasses = "w-64 flex-shrink-0 relative translate-x-0 flex";
  const mobileClasses = `fixed inset-y-0 left-0 z-[60] shadow-2xl transform transition-transform duration-300 ${
    isOpen ? "translate-x-0" : "-translate-x-full"
  }`;

  const menuItems = [
    { id: 'dashboard', icon: <LayoutDashboard size={20} />, label: '대시보드', view: 'dashboard' as ViewType },
    // { id: 'review', icon: <FileText size={20} />, label: '리뷰 스테이지', view: 'review-stage' as ViewType },
    { id: 'review', icon: <Scale size={20} />, label: '컴플라이언스 통제', view: 'compliance-control' as ViewType },
    { id: 'compliance', icon: <ShieldCheck size={20} />, label: '정책 관리', view: 'policy-manage' as ViewType },
    { id: 'context', icon: <Share2 size={20} />, label: '지식 클라우드', view: 'context-hub' as ViewType },
    { id: 'bi', icon: <BarChart2 size={20} />, label: '비즈니스 인텔리전스', view: 'power-bi' as ViewType }, 
    { id: 'audit', icon: <FileCheck size={20} />, label: '감사 및 보고서 관리', view: 'audit' as ViewType },
  ];

  return (
    <>
      {/* --- 모바일용 상단 바 (햄버거 버튼) --- */}
      <div className="md:hidden flex items-center justify-between p-4 bg-card-light dark:bg-card-dark border-b border-gray-200 dark:border-gray-700 fixed top-0 left-0 right-0 z-40">
        <img src={Logo} alt="Logo" className="h-8 w-auto" />
        <button onClick={toggleSidebar} className="p-2 text-gray-600 dark:text-gray-400">
          <Menu size={24} />
        </button>
      </div>

      {/* --- 모바일용 배경 오버레이 (사이드바 열렸을 때) --- */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-[55] md:hidden backdrop-blur-sm"
          onClick={toggleSidebar}
        />
      )}

    {/* <aside 
      className="w-64 flex-shrink-0 bg-card-light dark:bg-card-dark border-r border-gray-200 dark:border-gray-700 flex flex-col justify-between 
                 hidden md:flex transition-colors duration-200 h-screen md:fixed left-0 top-0 overflow-y-auto z-50"
    > */}
    <aside
      className={`
        w-64
        bg-card-light dark:bg-card-dark
        border-r border-gray-200 dark:border-gray-700
        flex flex-col justify-between
        overflow-y-auto
        transition-transform duration-300
        z-[60]

        /* 모바일 */
        fixed inset-y-0 left-0
        ${isOpen ? 'translate-x-0' : '-translate-x-full'}

        /* PC */
        md:static
        md:translate-x-0
        md:h-screen
      `}
    >
      {/* 모바일 전용 닫기 버튼 (사이드바 내부) */}
      <div className="md:hidden absolute top-4 right-4">
        <button onClick={toggleSidebar} className="p-2 text-gray-500">
          <X size={20} />
        </button>
      </div>

      <div>
        <div className="h-20 flex items-center px-8 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-4 text-primary font-bold text-2xl">
            <img src={Logo} alt="Logo" className="h-[60px] w-auto object-contain" />
          </div>
        </div>
        
        <div className="px-4 py-6">
          <h3 className="px-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">메인 메뉴</h3>
          <nav className="space-y-1">
            {menuItems.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setCurrentView(item.view);
                  if(window.innerWidth < 768) setIsOpen(false);
                }}
                className={`w-full flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                  currentView === item.view
                    ? 'bg-primary/10 text-primary'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                <span className="mr-3">{item.icon}</span>
                {item.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      <div className="px-4 py-6">
        <h3 className="px-4 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">기타 기능</h3>
        <nav className="space-y-1">
          <a href="#" className="flex items-center px-4 py-3 text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700 hover:text-gray-900 dark:hover:text-white rounded-lg transition-colors">
            <span className="mr-3"><Settings size={20} /></span>
            설정
          </a>

          {/* 3. 로그아웃 버튼 추가 */}
          <button 
            onClick={handleLogout}
            className="w-full flex items-center px-4 py-3 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors mt-1"
          >
            <span className="mr-3"><LogOut size={20} /></span>
            로그아웃
          </button>
        </nav>
        
        <div className="mt-6 border-t border-gray-100 dark:border-gray-700 pt-6 px-2">
          <div className="flex items-center px-2 py-2 bg-gray-50 dark:bg-gray-800 rounded-lg cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors">
            <div className="flex-shrink-0">
              <img 
                alt="User Profile" 
                className="h-10 w-10 rounded-full object-cover" 
                src={user?.profileImage || `https://ui-avatars.com/api/?name=${user?.username || 'User'}&background=0D8ABC&color=fff`} 
              />
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {user?.username || '방문자'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {user?.position || 'Guest'}
              </p>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <div className="h-16 md:hidden" />
  </>
  );
};