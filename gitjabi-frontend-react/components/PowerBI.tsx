import React from 'react';
import { 
  ScrollText
} from 'lucide-react';

export const PowerBI: React.FC = () => {
  return (
    <div className="flex flex-col h-full bg-background-light dark:bg-background-dark text-gray-900 dark:text-gray-100 font-sans">
      <div className="flex-1 overflow-y-auto p-6 md:p-8 custom-scrollbar">
        <div className="max-w-[1600px] mx-auto space-y-8">
            {/* Breadcrumb & Title */}
            <div>
                <nav className="flex text-xs text-gray-500 dark:text-gray-400 mb-2">
                    <ol className="flex items-center space-x-2">
                        <li><a className="hover:text-primary transition-colors" href="#">홈</a></li>
                        <li><span className="text-gray-300">/</span></li>
                        <li><span className="text-gray-900 dark:text-white font-medium">비즈니스 인텔리전스</span></li>
                    </ol>
                </nav>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">비즈니스 인텔리전스</h1>
            </div>
        </div>
      </div>
    </div>
  );
};