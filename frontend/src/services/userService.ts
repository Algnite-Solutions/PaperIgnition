import Taro from '@tarojs/taro';
import { API_BASE_URL } from '../config/api'; // Import the base URL

// Function to get current user profile
export const fetchUserProfile = async () => {
  try {
    // 统一使用localStorage获取token，确保跨平台兼容性
    let token: string | null = null;
    try {
      if (typeof localStorage !== 'undefined') {
        token = localStorage.getItem('token');
      }
    } catch (error) {
      console.error('Error accessing localStorage:', error);
    }
    
    if (!token) {
      throw new Error('Authentication token not found.');
    }

    const response = await Taro.request({
      url: `${API_BASE_URL}/users/me`,
      method: 'GET',
      header: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.statusCode === 200) {
      return response.data; // Assuming response.data contains user profile
    } else {
      throw new Error(response.data.detail || 'Failed to fetch user profile');
    }
  } catch (error) {
    console.error('Error fetching user profile:', error);
    throw error; // Re-throw for component to handle
  }
};

// Function to get all research domains
export const fetchResearchDomains = async () => {
  try {
    const response = await Taro.request({
      url: `${API_BASE_URL}/users/research_domains`,
      method: 'GET',
    });

    if (response.statusCode === 200) {
      return response.data; // Assuming response.data is an array of research domains
    } else {
      throw new Error(response.data.detail || 'Failed to fetch research domains');
    }
  } catch (error) {
    console.error('Error fetching research domains:', error);
    throw error; // Re-throw for component to handle
  }
};

// Function to update user profile
export const updateUserProfile = async (profileData: any) => {
  try {
    // 统一使用localStorage获取token，确保跨平台兼容性
    let token: string | null = null;
    try {
      if (typeof localStorage !== 'undefined') {
        token = localStorage.getItem('token');
      }
    } catch (error) {
      console.error('Error accessing localStorage:', error);
    }
    
    if (!token) {
      throw new Error('Authentication token not found.');
    }

    const response = await Taro.request({
      url: `${API_BASE_URL}/users/me/profile`,
      method: 'PUT',
      data: profileData,
      header: {
        'content-type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.statusCode === 200) {
      return response.data; // Assuming response.data is the updated user profile
    } else {
      throw new Error(response.data.detail || 'Failed to update user profile');
    }
  } catch (error) {
    console.error('Error updating user profile:', error);
    throw error; // Re-throw for component to handle
  }
}; 