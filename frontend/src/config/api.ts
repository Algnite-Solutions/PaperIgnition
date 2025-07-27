let apiBaseUrl: string;

// Standard way to check for production environment
if (process.env.NODE_ENV === 'production') {
  apiBaseUrl = process.env.REACT_APP_PROD_API_BASE_URL || 'http://127.0.0.1:8000'; // 生产环境API
} 
// Check for a specific custom environment variable for a staging/test API
else if (process.env.REACT_APP_USE_STAGING_API === 'true') {
  apiBaseUrl = process.env.REACT_APP_STAGING_API_BASE_URL || 'http://127.0.0.1:8000'; // 测试环境API
} 
// Default to development environment for all other cases
else {
  apiBaseUrl = process.env.REACT_APP_DEV_API_BASE_URL || 'http://127.0.0.1:8000'; // 开发环境API (你的FastAPI后端)
}

export const API_BASE_URL = apiBaseUrl;

// Example of how you might manage another distinct API, if needed:
// const anotherServiceApiBaseUrl = process.env.NODE_ENV === 'production' 
// ? process.env.REACT_APP_ANOTHER_SERVICE_PROD_URL 
// : process.env.REACT_APP_ANOTHER_SERVICE_DEV_URL;
// export const ANOTHER_SERVICE_API_URL = anotherServiceApiBaseUrl;

// console.log(`Current API Base URL: ${API_BASE_URL}`);

// 你还可以导出具体的端点，如果需要的话
// export const LOGIN_URL = `${API_BASE_URL}/auth/login-email`;
// export const USER_PROFILE_URL = `${API_BASE_URL}/users/me/profile`;

// 关于之前提到的 http://localhost:3000/api :
// 如果这个是Taro H5开发服务器自身提供的mock API或者完全不同的服务，可以单独管理
// 例如:
// export const MOCK_API_BASE_URL = 'http://localhost:3000/api';
// 但如果它只是另一个后端开发实例，也应该纳入上述的 baseURL 管理逻辑

// API 端点
export const API_ENDPOINTS = {
  // 论文相关
  PAPERS: {
    LIST: '/papers',
    DETAIL: (id: string) => `/papers/${id}`,
    CONTENT: (id: string) => `/papers/${id}/content`,
  },
  // 其他 API 端点...
} 