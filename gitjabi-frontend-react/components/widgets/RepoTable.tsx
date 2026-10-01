import React from 'react';
import { Folder, MoreHorizontal } from 'lucide-react';
import { RepoMetric } from '../../types';

const repos: RepoMetric[] = [
  {
    id: '1',
    name: 'backend-core-service',
    branch: 'main branch',
    language: 'Go',
    healthScore: 92,
    openIssues: 14,
    lastAudit: '2023-10-24',
  },
  {
    id: '2',
    name: 'frontend-dashboard',
    branch: 'dev branch',
    language: 'TypeScript',
    healthScore: 85,
    openIssues: 23,
    lastAudit: '2023-10-23',
  },
  {
    id: '3',
    name: 'legacy-auth-module',
    branch: 'v1.2 branch',
    language: 'Java',
    healthScore: 64,
    openIssues: 5,
    lastAudit: '2023-10-20',
  },
];

const LanguageDot: React.FC<{ lang: string }> = ({ lang }) => {
  let color = 'bg-gray-400';
  if (lang === 'Go') color = 'bg-blue-500';
  if (lang === 'TypeScript') color = 'bg-yellow-400';
  if (lang === 'Java') color = 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <span className={`h-2 w-2 rounded-full ${color}`}></span>
      {lang}
    </div>
  );
};

const HealthBar: React.FC<{ score: number }> = ({ score }) => {
  let color = 'bg-green-500';
  if (score < 80) color = 'bg-primary';
  if (score < 70) color = 'bg-orange-500';
  if (score < 50) color = 'bg-red-500';

  return (
    <div>
      <div className="w-24 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          className={`${color} h-2 rounded-full transition-all duration-500`}
          style={{ width: `${score}%` }}
        ></div>
      </div>
      <span className="text-xs font-medium mt-1 inline-block text-gray-600 dark:text-gray-400">
        {score}/100
      </span>
    </div>
  );
};

export const RepoTable: React.FC = () => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="text-xs text-gray-500 dark:text-gray-400 uppercase border-b border-gray-100 dark:border-gray-700">
            <th className="font-semibold py-3 pl-2">Repository</th>
            <th className="font-semibold py-3">Language</th>
            <th className="font-semibold py-3">Health Score</th>
            <th className="font-semibold py-3">Open Issues</th>
            <th className="font-semibold py-3">Last Audit</th>
            <th className="font-semibold py-3 text-right pr-2">Actions</th>
          </tr>
        </thead>
        <tbody className="text-sm text-gray-700 dark:text-gray-300">
          {repos.map((repo) => (
            <tr
              key={repo.id}
              className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors border-b border-gray-50 dark:border-gray-800 last:border-0"
            >
              <td className="py-4 pl-2 flex items-center gap-3">
                <div className="p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
                  <Folder className="text-gray-600 dark:text-gray-400" size={18} />
                </div>
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{repo.name}</p>
                  <p className="text-xs text-gray-500">{repo.branch}</p>
                </div>
              </td>
              <td className="py-4">
                <LanguageDot lang={repo.language} />
              </td>
              <td className="py-4">
                <HealthBar score={repo.healthScore} />
              </td>
              <td className="py-4">{repo.openIssues}</td>
              <td className="py-4 text-gray-500">{repo.lastAudit}</td>
              <td className="py-4 text-right pr-2">
                <button className="text-gray-400 hover:text-primary transition-colors p-1 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700">
                  <MoreHorizontal size={20} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};