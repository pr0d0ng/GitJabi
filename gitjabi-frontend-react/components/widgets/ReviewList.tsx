import React from 'react';
import { PRItem } from '../../types';

const prs: PRItem[] = [
  {
    id: '1',
    prId: 'PR #4829',
    title: 'Update authentication middleware',
    timeAgo: '2시간 전',
    status: 'Pending Review',
    statusColor: 'yellow',
  },
  {
    id: '2',
    prId: 'PR #4825',
    title: 'Fix CSS grid layout for dashboard',
    timeAgo: '5시간 전',
    status: 'Approved',
    statusColor: 'green',
  },
  {
    id: '3',
    prId: 'PR #4822',
    title: 'Legacy database migration script',
    timeAgo: '1일 전',
    status: 'Policy Flagged',
    statusColor: 'red',
  },
  {
    id: '4',
    prId: 'PR #4830',
    title: 'API rate limiting logic',
    timeAgo: '방금 전',
    status: 'Analysis Running',
    statusColor: 'blue',
  },
];

const StatusIndicator: React.FC<{ status: string; color: string }> = ({ status, color }) => {
  let bgColor = 'bg-gray-400';
  if (color === 'yellow') bgColor = 'bg-yellow-400';
  if (color === 'green') bgColor = 'bg-green-500';
  if (color === 'red') bgColor = 'bg-red-500';
  if (color === 'blue') bgColor = 'bg-blue-400'; // Actually using blue for running typically means progress or info

  return (
    <div className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full ${bgColor}`}></span>
      <span className="text-xs text-gray-500 dark:text-gray-400">
        {color === 'blue' && status === 'Analysis Running' ? 'Analysis Running...' : status}
      </span>
    </div>
  );
};

const Tag: React.FC<{ text: string; color: string }> = ({ text, color }) => {
  let classes = 'text-gray-600 bg-gray-100 dark:bg-gray-800';
  if (color === 'blue') classes = 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30';
  if (color === 'green') classes = 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30';
  if (color === 'red') classes = 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30';
  
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded ${classes}`}>
      {text}
    </span>
  );
};

export const ReviewList: React.FC = () => {
  return (
    <div className="space-y-4 overflow-y-auto flex-1 max-h-[300px] pr-2 custom-scrollbar">
      {prs.map((pr) => (
        <div
          key={pr.id}
          className="group p-3 rounded-lg bg-gray-50 dark:bg-gray-800/50 hover:bg-white dark:hover:bg-gray-800 border border-transparent hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm transition-all cursor-pointer"
        >
          <div className="flex justify-between items-start mb-1">
            <Tag text={pr.prId} color={pr.statusColor === 'yellow' ? 'blue' : pr.statusColor} />
            <span className="text-[10px] text-gray-400">{pr.timeAgo}</span>
          </div>
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200 mb-1">{pr.title}</p>
          <StatusIndicator status={pr.status} color={pr.statusColor} />
        </div>
      ))}
    </div>
  );
};