/**
 * 示例：前端 Axios 拦截器配置
 * 完美对接 Cosmic MVP 的统一响应格式 {success, data, message}
 */
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 10000,
});

// 请求拦截器：自动注入 Token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器：统一处理成功与失败逻辑
apiClient.interceptors.response.use(
  (response) => {
    const res = response.data;
    
    // 如果 success 为 false，说明是业务逻辑错误
    if (!res.success) {
      console.error('业务错误:', res.message);
      // 可以在这里弹出全局 Toast 提示
      return Promise.reject(new Error(res.message || 'Error'));
    }
    
    // 返回核心数据 data，组件内直接 const user = await login() 即可
    return res.data;
  },
  (error) => {
    // 处理 HTTP 状态码错误 (401, 403, 500 等)
    const message = error.response?.data?.message || '服务器连接失败';
    console.error('网络错误:', message);
    
    if (error.response?.status === 401) {
      // Token 过期，跳转登录
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
