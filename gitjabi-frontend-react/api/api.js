// src/api/api.js
import axios from 'axios';

export const host = import.meta.env.VITE_API_HOST;


const api = axios.create({
  baseURL: host, 
  withCredentials: true,
  timeout: 15000,
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // 401 에러이고 재시도한 적이 없을 때
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Refresh Token으로 새 Access Token 요청
        const res = await axios.post(`${host}/api/auth/token/refresh`, 
          {}, 
          { withCredentials: true }
        );
        
        const { access_token, user } = res.data;
        localStorage.setItem('accessToken', access_token);
        localStorage.setItem('userInfo', user);
        
        // 새 토큰으로 기존 요청 재실행
        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh Token도 만료된 경우 로그아웃
        localStorage.removeItem('accessToken');
        // localStorage.removeItem('userInfo');
        console.log("Refresh tkn failed");
        window.location.href = '/';
        return Promise.reject(refreshError);
      }
    }
    return Promise.reject(error);
  }
);

export default api;
