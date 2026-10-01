import React from 'react';
import { 
  ScrollText, 
  TrendingUp, 
  ShieldAlert, 
  Activity, 
  ArrowRight, 
  FileText, 
  Download, 
  Sparkles, 
  Search, 
  Filter, 
  Share, 
  Bot, 
  Users, 
  BrainCircuit, 
  GitPullRequest
} from 'lucide-react';

export const AuditManagement: React.FC = () => {
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
                        <li><span className="text-gray-900 dark:text-white font-medium">감사 및 보고서 관리</span></li>
                    </ol>
                </nav>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white tracking-tight">감사 및 보고서 관리</h1>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Card 1 */}
                <div className="bg-card-light dark:bg-card-dark p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow flex items-center gap-5">
                    <div className="p-3 bg-primary/10 rounded-xl text-primary">
                        <ScrollText size={24} />
                    </div>
                    <div className="flex-1">
                        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Total Audit Logs (24h)</h3>
                        <div className="flex items-baseline gap-2">
                            <p className="text-3xl font-bold text-gray-900 dark:text-white">14,203</p>
                            <span className="inline-flex items-center text-xs font-medium text-green-600">
                                <TrendingUp size={14} className="mr-0.5" /> +12%
                            </span>
                        </div>
                    </div>
                </div>

                {/* Card 2 */}
                <div className="bg-card-light dark:bg-card-dark p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow flex items-center gap-5 relative overflow-hidden">
                     <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-xl text-red-500">
                        <ShieldAlert size={24} />
                    </div>
                    <div className="flex-1 z-10">
                        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Anomalies Detected</h3>
                        <div className="flex items-baseline gap-2">
                            <p className="text-3xl font-bold text-gray-900 dark:text-white">3</p>
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400 uppercase">
                                Action Needed
                            </span>
                        </div>
                    </div>
                </div>

                {/* Card 3 */}
                <div className="bg-card-light dark:bg-card-dark p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow flex items-center gap-5">
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl text-blue-500">
                        <Activity size={24} />
                    </div>
                    <div className="flex-1">
                        <h3 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">Report Status</h3>
                        <div className="flex items-center gap-2">
                            <span className="w-3 h-3 rounded-full bg-primary animate-pulse"></span>
                            <p className="text-xl font-bold text-gray-900 dark:text-white">System Up to date</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Report Management */}
            <div className="bg-card-light dark:bg-card-dark p-6 rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                    <div>
                        <h2 className="text-lg font-bold text-gray-900 dark:text-white">Report Management</h2>
                        <p className="text-sm text-gray-500 dark:text-gray-400">Download automated compliance reports or trigger a new generation.</p>
                    </div>
                    <button className="text-sm text-primary font-semibold hover:text-emerald-500 transition-colors flex items-center gap-1">
                        View All Archives <ArrowRight size={14} />
                    </button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Report 1 */}
                    <div className="flex items-center justify-between p-4 rounded-xl bg-background-light dark:bg-black/20 border border-gray-100 dark:border-gray-700/50 hover:border-primary/30 transition-colors">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 rounded-lg bg-white dark:bg-gray-800 flex items-center justify-center text-red-500 shadow-sm border border-gray-100 dark:border-gray-700">
                                <FileText size={20} />
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-gray-900 dark:text-white">Weekly Compliance Report</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">Week 42 • Oct 24, 2023</p>
                            </div>
                        </div>
                        <button className="p-2 text-gray-400 hover:text-primary transition-colors hover:bg-white dark:hover:bg-gray-800 rounded-lg">
                            <Download size={20} />
                        </button>
                    </div>

                    {/* Report 2 */}
                    <div className="flex items-center justify-between p-4 rounded-xl bg-background-light dark:bg-black/20 border border-gray-100 dark:border-gray-700/50 hover:border-primary/30 transition-colors">
                        <div className="flex items-center gap-4">
                            <div className="w-10 h-10 rounded-lg bg-white dark:bg-gray-800 flex items-center justify-center text-green-600 shadow-sm border border-gray-100 dark:border-gray-700">
                                <FileText size={20} />
                            </div>
                            <div>
                                <p className="text-sm font-semibold text-gray-900 dark:text-white">Monthly Security Summary</p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">Full October 2023</p>
                            </div>
                        </div>
                        <button className="p-2 text-gray-400 hover:text-primary transition-colors hover:bg-white dark:hover:bg-gray-800 rounded-lg">
                            <Download size={20} />
                        </button>
                    </div>

                    {/* Generate Button */}
                    <div className="flex items-center justify-center">
                        <button className="w-full h-full py-4 bg-primary hover:bg-emerald-400 text-white font-bold rounded-xl shadow-lg shadow-primary/20 transition-all active:scale-[0.98] flex items-center justify-center gap-3">
                            <Sparkles size={20} />
                            Generate New Audit Report
                        </button>
                    </div>
                </div>
            </div>

            {/* Audit Log Table */}
            <div className="bg-card-light dark:bg-card-dark rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden">
                <div className="p-6 border-b border-gray-100 dark:border-gray-700">
                    <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                        <div>
                            <h2 className="text-xl font-bold text-gray-900 dark:text-white">Audit Log & Event Collection</h2>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">Detailed real-time monitoring across all integrated tools.</p>
                        </div>
                        <div className="flex flex-wrap items-center gap-3">
                            <div className="relative flex-1 sm:flex-none">
                                <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-400">
                                    <Search size={20} />
                                </span>
                                <input className="pl-10 pr-4 py-2.5 text-sm border border-gray-200 dark:border-gray-700 rounded-xl bg-white dark:bg-gray-800/50 focus:ring-2 focus:ring-primary focus:border-primary outline-none transition-all w-full sm:w-80" placeholder="Search events, users, or details..." type="text"/>
                            </div>
                            <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors shadow-sm">
                                <Filter size={20} />
                                Filter
                            </button>
                             <button className="flex items-center gap-2 px-4 py-2.5 text-sm font-semibold text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors shadow-sm">
                                <Share size={20} />
                                Export CSV
                            </button>
                        </div>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse">
                        <thead>
                            <tr className="bg-background-light dark:bg-black/20 text-xs font-bold text-gray-500 dark:text-gray-400 uppercase tracking-widest border-b border-gray-100 dark:border-gray-700">
                                <th className="px-6 py-5 w-48">Timestamp</th>
                                <th className="px-6 py-5 w-64">User / System</th>
                                <th className="px-6 py-5 w-40">Category</th>
                                <th className="px-6 py-5">Action Detail</th>
                                <th className="px-6 py-5 w-32 text-right">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100 dark:divide-gray-700 text-sm">
                            {/* Row 1 */}
                            <tr className="hover:bg-gray-50 dark:hover:bg-white/5 transition-colors group">
                                <td className="px-6 py-5 font-mono text-gray-500 text-xs whitespace-nowrap">Oct 25, 2023 10:42 AM</td>
                                <td className="px-6 py-5">
                                    <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-full bg-gray-100 flex items-center justify-center border border-gray-200 text-gray-600">
                                            <Bot size={20} />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-gray-900 dark:text-white">DevTeam-Bot</p>
                                            <p className="text-[10px] text-gray-500 uppercase font-bold">System Process</p>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-5">
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gray-100 text-gray-700 border border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700">
                                        <img alt="GitHub" className="w-4 h-4" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAguydhGM0-CAyQJnz041SuttSc_dshBu5RhiyXYWw0MROoNnDXvqTI-KEUDM_2ixScPDPGfvM3uNxQtLVkw3s8_TZ4tUVa3Ty8q6ALKm9_Qt8axgGK5IZLfqnHFatjmIC5EOSwSgx2xxZz55zDTs_rysYZwW6xNYnuFe_3bK8XpmbREWoHSrTLqxYSjdDlcqR5M6RELIFmpwYn4GT4OfHY-sGdD6GiD1mIakECJjQZslqZt6fAll8AhwGY-SPfiGeMSdaIYpFr4kDD" />
                                        GitHub
                                    </span>
                                </td>
                                <td className="px-6 py-5 text-gray-600 dark:text-gray-300">
                                    Webhook Received: <span className="font-mono text-xs bg-gray-100 dark:bg-gray-800 px-1.5 py-1 rounded">Push to main branch</span>
                                </td>
                                <td className="px-6 py-5 text-right">
                                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-primary/10 text-primary border border-primary/20">
                                        Success
                                    </span>
                                </td>
                            </tr>
                            {/* Row 2 */}
                             <tr className="hover:bg-gray-50 dark:hover:bg-white/5 transition-colors group">
                                <td className="px-6 py-5 font-mono text-gray-500 text-xs whitespace-nowrap">Oct 25, 2023 10:40 AM</td>
                                <td className="px-6 py-5">
                                    <div className="flex items-center gap-3">
                                        <img className="w-9 h-9 rounded-full object-cover border border-gray-200" alt="Sarah Kim" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCw1TX-3yBxfVSGPSCF8IU_PsGlpveUwZ7Dyce_axqZX1CsYclEOTKZcnjLJ9enDk925fU_MutY8ouuEMdwSlakopJs4Y7oRsIUEc0A5SvCp46mD9TPCFOPoOlrH61R1eo-UOuH7uHoXAfc05uPihe_T5zhjRPwvr8gRusRrRxdsk3o_HsRM9JKfiKIKzjgmXaBRlSN64srXj3KXYrbyacvYFYMUrcuz5BNB-0pY8PAnT9U0HG-ztQOxo_GlSO185JQjbY2ImJ6RVNd"/>
                                        <div>
                                            <p className="font-semibold text-gray-900 dark:text-white">Sarah Kim</p>
                                            <p className="text-[10px] text-gray-500 uppercase font-bold">Lead Developer</p>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-5">
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100 dark:bg-indigo-900/20 dark:text-indigo-300 dark:border-indigo-800">
                                        <Users size={18} />
                                        Teams
                                    </span>
                                </td>
                                <td className="px-6 py-5 text-gray-600 dark:text-gray-300">
                                    Meeting Synced: "Code Architecture Review - Q4 Roadmap"
                                </td>
                                <td className="px-6 py-5 text-right">
                                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-600 border border-blue-100 dark:bg-blue-900/20 dark:text-blue-300 dark:border-blue-800">
                                        Info
                                    </span>
                                </td>
                            </tr>
                            {/* Row 3 */}
                            <tr className="hover:bg-gray-50 dark:hover:bg-white/5 transition-colors group bg-red-50/20 dark:bg-red-900/5">
                                <td className="px-6 py-5 font-mono text-gray-500 text-xs whitespace-nowrap">Oct 25, 2023 10:15 AM</td>
                                <td className="px-6 py-5">
                                    <div className="flex items-center gap-3">
                                        <div className="w-9 h-9 rounded-full bg-gradient-to-r from-purple-500 to-pink-500 flex items-center justify-center text-white shadow-sm">
                                            <Sparkles size={18} />
                                        </div>
                                        <div>
                                            <p className="font-semibold text-gray-900 dark:text-white">System AI</p>
                                            <p className="text-[10px] text-gray-500 uppercase font-bold">Automation</p>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-5">
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-50 text-purple-700 border border-purple-100 dark:bg-purple-900/20 dark:text-purple-300 dark:border-purple-800">
                                        <BrainCircuit size={18} />
                                        AI Analysis
                                    </span>
                                </td>
                                <td className="px-6 py-5 text-gray-600 dark:text-gray-300">
                                    Policy Search Triggered: <span className="text-red-500 font-bold">"Potential Access Keys Exposure"</span> detection
                                </td>
                                <td className="px-6 py-5 text-right">
                                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-amber-50 text-amber-600 border border-amber-100 dark:bg-amber-900/20 dark:text-amber-300 dark:border-amber-800">
                                        Warning
                                    </span>
                                </td>
                            </tr>
                            {/* Row 4 */}
                             <tr className="hover:bg-gray-50 dark:hover:bg-white/5 transition-colors group">
                                <td className="px-6 py-5 font-mono text-gray-500 text-xs whitespace-nowrap">Oct 25, 2023 09:55 AM</td>
                                <td className="px-6 py-5">
                                    <div className="flex items-center gap-3">
                                        <img className="w-9 h-9 rounded-full object-cover border border-gray-200" alt="Mike Ross" src="https://lh3.googleusercontent.com/aida-public/AB6AXuAot6HYJYhXKrTx-UxtNEAnV2L5TWogcX3MNGp1eAfxYgbcZTr6a2bN3YbBrv1uC4fYwt0gVIWnj9bkMmztBsbmqml2lB1uRfCKzyu9hE_gftpxUe3Xun6qU6cON5c2IUfHaH4X7tsMrFU6wl_GKZdR33_x_vxfMyJTR1QwcaQHZlSJKnWUmBT83OClN53RAwuQiIlb1-FZ2p7atQZCWIkBVhqRUkcsDBRSvpMSP9f103wZvRZs7seCfu1mKoWZQ9aGF5efEauBHNhN"/>
                                        <div>
                                            <p className="font-semibold text-gray-900 dark:text-white">Mike Ross</p>
                                            <p className="text-[10px] text-gray-500 uppercase font-bold">DevOps Engineer</p>
                                        </div>
                                    </div>
                                </td>
                                <td className="px-6 py-5">
                                    <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-300 dark:border-emerald-800">
                                        <GitPullRequest size={18} />
                                        PR Action
                                    </span>
                                </td>
                                <td className="px-6 py-5 text-gray-600 dark:text-gray-300">
                                    PR Rejected: "Incomplete Unit Test Coverage" on feature branch
                                </td>
                                <td className="px-6 py-5 text-right">
                                    <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-primary/10 text-primary border border-primary/20">
                                        Success
                                    </span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                 <div className="p-6 border-t border-gray-100 dark:border-gray-700 flex items-center justify-between bg-gray-50/50 dark:bg-black/10">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                        Showing <span className="font-bold text-gray-900 dark:text-white">1 to 4</span> of <span className="font-bold text-gray-900 dark:text-white">14,203</span> audit entries
                    </p>
                    <div className="flex gap-2">
                        <button className="px-4 py-2 text-sm font-semibold rounded-xl border border-gray-200 dark:border-gray-700 text-gray-400 bg-white dark:bg-gray-800 cursor-not-allowed" disabled>
                            Previous
                        </button>
                        <button className="px-4 py-2 text-sm font-semibold rounded-xl border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-white bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-primary transition-colors shadow-sm">
                            Next
                        </button>
                    </div>
                </div>
            </div>
             <div className="h-12"></div>
        </div>
      </div>
    </div>
  );
};