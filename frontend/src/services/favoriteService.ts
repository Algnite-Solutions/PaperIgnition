import { API_BASE_URL } from '../config/api'

export interface FavoriteData {
  paper_id: string
  title: string
  authors: string
  abstract: string
  url?: string
}

export interface FavoriteResponse {
  id: number
  paper_id: string
  title: string
  authors: string
  abstract: string
  url?: string
}

// 获取当前用户token
const getAuthToken = (): string | null => {
  return localStorage.getItem('token')
}

// 获取Authorization headers
const getAuthHeaders = () => {
  const token = getAuthToken()
  if (!token) {
    throw new Error('Authentication token not found')
  }
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  }
}

// 获取用户收藏列表
export const fetchUserFavorites = async (): Promise<FavoriteResponse[]> => {
  const response = await fetch(`${API_BASE_URL}/api/favorites/list`, {
    method: 'GET',
    headers: getAuthHeaders()
  })
  
  if (!response.ok) {
    throw new Error('获取收藏列表失败')
  }
  
  return response.json()
}

// 添加论文到收藏
export const addPaperToFavorites = async (favoriteData: FavoriteData): Promise<any> => {
  const response = await fetch(`${API_BASE_URL}/api/favorites/add`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(favoriteData)
  })
  
  if (!response.ok) {
    const errorData = await response.json()
    throw new Error(errorData.detail || '添加收藏失败')
  }
  
  return response.json()
}

// 从收藏中移除论文
export const removePaperFromFavorites = async (paperId: string): Promise<any> => {
  const response = await fetch(`${API_BASE_URL}/api/favorites/remove/${paperId}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  })
  
  if (!response.ok) {
    throw new Error('移除收藏失败')
  }
  
  return response.json()
}

// 检查论文是否已收藏
export const checkIfPaperFavorited = async (paperId: string): Promise<boolean> => {
  const response = await fetch(`${API_BASE_URL}/api/favorites/check/${paperId}`, {
    method: 'GET',
    headers: getAuthHeaders()
  })
  
  if (!response.ok) {
    throw new Error('检查收藏状态失败')
  }
  
  const result = await response.json()
  return result.is_favorited
} 