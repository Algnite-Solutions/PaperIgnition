// API 基础配置
export const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:3000/api'  // 开发环境
  : 'https://your-production-api.com/api'  // 生产环境

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