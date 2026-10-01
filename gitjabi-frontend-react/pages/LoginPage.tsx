// src/pages/LoginPage.jsx
import React, { useState } from 'react';
import api from '../api/api';
import { Lock, Loader2, User2 } from 'lucide-react';
import Logo from '../assets/logo.png';

export default function LoginPage({ onLoginSuccess }) {
  const [id, setId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    if (isLoading) return;

    setIsLoading(true);
    setError('');

    const formData = new URLSearchParams();
    formData.append('username', id); 
    formData.append('password', password); 

    try {
      const response = await api.post('/api/auth/token', formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );
      const { access_token, user, _t } = response.data;
      
      localStorage.setItem('accessToken', access_token);
      localStorage.setItem('userInfo', JSON.stringify(user));
      onLoginSuccess(user);
      
    } catch (err) {
      if (err.response) {
        const status = err.response.status;
        const detail = err.response.data?.detail; 

        switch (status) {
          case 401:
            setError('아이디 또는 비밀번호가 일치하지 않습니다.');
            break;
          case 403:
            setError('접근 권한이 없습니다. 관리자에게 문의하세요.');
            break;
          case 422:
            setError('입력 형식이 올바르지 않습니다.');
            break;
          case 500:
            setError('서버 내부 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
            break;
          default:
            setError(detail || '로그인 중 알 수 없는 오류가 발생했습니다.');
        }
      } 
      else if (err.request) {
        setError('서버와 통신할 수 없습니다. 네트워크 연결을 확인해주세요.');
      } 
      else {
        setError('로그인 요청 중 오류가 발생했습니다.');
      }
      
      console.error('Login Error:', err); 
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-200 dark:from-gray-900 dark:to-black px-4">

      <div className="w-full max-w-md backdrop-blur-xl bg-white/80 dark:bg-gray-800/70 border border-gray-200 dark:border-gray-700 rounded-3xl shadow-2xl p-10">

        {/* Brand */}
        <div className="text-center mb-10">
          <div className="mx-auto w-48 h-24 flex items-center justify-center">
            <img
              src={Logo}
              alt="Logo"
              className="object-contain"
            />
          </div>

          {/* <h1 className="text-2xl font-semibold text-gray-900 dark:text-white">
            대시보드 로그인
          </h1> */}
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
            계정으로 로그인하여 서비스를 이용하세요.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-6">

          {error && (
            <div className="text-sm text-red-500 bg-red-50 dark:bg-red-900/30 dark:text-red-400 p-3 rounded-lg text-center">
              {error}
            </div>
          )}

          {/* ID */}
          <div className="relative group">
            <User2 size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-teal-500 transition" />
            <input
              type="text"
              required
              value={id}
              onChange={(e) => setId(e.target.value)}
              className="w-full pl-11 pr-4 py-3 rounded-xl bg-gray-100 dark:bg-gray-900 border border-transparent focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 outline-none transition-all text-gray-900 dark:text-white"
              placeholder="아이디"
            />
          </div>

          {/* Password */}
          <div className="relative group">
            <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-teal-500 transition" />
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full pl-11 pr-4 py-3 rounded-xl bg-gray-100 dark:bg-gray-900 border border-transparent focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 outline-none transition-all text-gray-900 dark:text-white"
              placeholder="비밀번호"
            />
          </div>

          {/* Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 rounded-xl font-semibold text-white bg-gradient-to-r from-teal-500 to-emerald-500 hover:from-teal-600 hover:to-emerald-600 transition-all duration-200 shadow-lg flex items-center justify-center disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="animate-spin" size={20} />
            ) : (
              '로그인'
            )}
          </button>
        </form>

      </div>
    </div>
  );
}