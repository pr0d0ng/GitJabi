import React, { useState, useEffect, createContext } from 'react';
import { Sidebar } from './components/Sidebar';
import { Dashboard } from './components/Dashboard';
// import { ReviewStage } from './components/ReviewStage';
import { ComplianceControlPage } from './components/ComplianceControl';
import { PolicyManagementPage } from './components/PolicyManagement';
import { KnowledgeCloud } from './components/KnowledgeCloud';
import { PowerBI } from './components/PowerBI';
import { AuditManagement } from './components/AuditManagement';
import { ViewType } from './types';
import { Toaster } from 'react-hot-toast';

import api from './api/api'
import LoginPage from './pages/LoginPage';

export const AuthContext = createContext({
  user: null,
  setUser: (user: any) => {},
  handleLogout: () => {}
});

function App() {
  const [isDark, setIsDark] = useState(false);
  const [currentView, setCurrentView] = useState<ViewType>('dashboard');

  const [user, setUser] = useState(() => {
    const token = localStorage.getItem('accessToken');
    const savedUser = localStorage.getItem('userInfo');
    
    if (token && savedUser) {
      try {
        return JSON.parse(savedUser);
      } catch {
        return null;
      }
    }
    return null;
  });
  const isLoggedIn = !!user;

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const handleLoginSuccess = (userData) => {
    setUser(userData); 
    localStorage.setItem('userInfo', JSON.stringify(userData));
  };

  const handleLogout = async () => {
    try {
      await api.post('/api/auth/logout');
    } catch (err) {
      console.error("서버 로그아웃 처리 중 오류:", err);
    } finally {
      localStorage.removeItem('accessToken');
      localStorage.removeItem('userInfo');
      
      setUser(null);
      
    }
  };

  if (!isLoggedIn) {
    return <LoginPage onLoginSuccess={handleLoginSuccess} />;
  }
  
  return (
    <AuthContext.Provider value={{ user, setUser, handleLogout }}>
    <div className="flex h-screen overflow-hidden bg-background-light dark:bg-background-dark font-sans text-gray-900 dark:text-gray-100">
      <Toaster position="bottom-right" />
      <Sidebar 
        currentView={currentView} 
        setCurrentView={setCurrentView} 
        // onLogout={handleLogout}
        // user={user}
      />
      
      {/* <main className={`flex-1 overflow-y-auto relative ml-0 md:ml-64 ${currentView === 'dashboard' ? 'p-4 md:p-8' : ''}`}> */}
      <main className={`flex-1 overflow-y-auto relative ml-0 ${currentView === 'dashboard' ? 'p-4 md:p-8' : ''}`}>
        {currentView === 'dashboard' && (
          <Dashboard isDark={isDark} setIsDark={setIsDark} />
        )}

        {currentView === 'compliance-control' && (
          <ComplianceControlPage
            userInfo={user}
          />
        )}
        
        {currentView === 'policy-manage' && (
          <PolicyManagementPage />
        )}

        {currentView === 'context-hub' && (
          <KnowledgeCloud />
        )}

        {currentView === 'power-bi' && (
          <PowerBI />
        )}

        {currentView === 'audit' && (
          <AuditManagement />
        )}
      </main>
    </div>
    </AuthContext.Provider>
  );
}

export default App;