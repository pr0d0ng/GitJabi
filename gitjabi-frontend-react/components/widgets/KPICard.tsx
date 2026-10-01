import React from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { KPIProps } from '../../types';

export const KPICard: React.FC<KPIProps> = ({ title, value, change, changeType, changeText, icon, chart }) => {
  return (
    <div className="bg-card-light dark:bg-card-dark p-6 rounded-xl shadow-[0_4px_6px_-1px_rgba(0,0,0,0.05)] border border-gray-100 dark:border-gray-700 flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
        <h2 className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{value}</h2>
        <div className="flex items-center mt-2">
          <span 
            className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 font-medium ${
              changeType === 'positive' 
                ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400' 
                : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400'
            } ${title === 'Context Nodes' ? '!bg-primary/10 !text-primary' : ''}`}
          >
            {changeType === 'positive' && title !== 'Context Nodes' ? <TrendingUp size={14} /> : null}
            {changeType === 'negative' ? <TrendingDown size={14} /> : null}
            {title === 'Context Nodes' ? <span className="material-icons text-[14px]">memory</span> : null}
            {change}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">{changeText}</span>
        </div>
      </div>
      
      {chart ? (
        <div className="h-16 w-16 relative">
             {chart}
        </div>
      ) : (
        <div className={`p-3 rounded-lg ${
            title === 'Risk Index' ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-500' : 'bg-purple-50 dark:bg-purple-900/20 text-purple-500'
        }`}>
            {icon}
        </div>
      )}
    </div>
  );
};

export const CircularProgress: React.FC<{ radius: number; percentage: number; color: string; iconDisable: boolean }> = ({ radius=16, percentage, color, iconDisable=false }) => {
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;
  
    return (
      <div className="flex items-center justify-center relative w-full h-full">
        <svg className="transform -rotate-90 w-full h-full" viewBox="0 0 36 36">
          {/* Background Circle */}
          <path
            className="text-gray-200 dark:text-gray-700"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
          />
          {/* Progress Circle */}
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke={color}
            strokeWidth="3"
            strokeDasharray={`${circumference}, ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>
        { iconDisable ? '' : 
        <div className="absolute inset-0 flex items-center justify-center text-primary">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 12 2 2 4-4"></path></svg>
        </div>
        
        }
      </div>
    );
  };