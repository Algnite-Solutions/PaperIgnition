import { View, Text, Image, Picker } from '@tarojs/components'
import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { AtIcon } from 'taro-ui'
import { logout, setFrequency } from '../../store/slices/userSlice'
import CustomButton from '../../components/ui/Button'
import { API_BASE_URL } from '../../config/api'
import './index.scss'

const defaultAvatar = 'https://img.icons8.com/pastel-glyph/64/000000/person-male--v1.png'

// 定义用户信息接口
interface UserInfo {
  email: string;
  username?: string;
}

// 获取用户信息接口 - 增加调试日志
const fetchUserInfo = async (): Promise<UserInfo | null> => {
  try {
    const token = localStorage.getItem('token')
    if (!token) {
      console.log('获取用户信息失败: 未找到token')
      throw new Error('未登录')
    }
    
    console.log('正在获取用户信息, token:', token.substring(0, 10) + '...')
    
    const response = await fetch(`${API_BASE_URL}/users/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      console.error('获取用户信息失败: 服务器响应错误', response.status)
      const errorData = await response.json().catch(() => ({ detail: '获取用户信息失败' }));
      throw new Error(errorData.detail || '获取用户信息失败')
    }
    
    const data = await response.json()
    console.log('获取用户信息成功:', data)
    return data
  } catch (error) {
    console.error('获取用户信息失败:', error)
    return null
  }
}

// 更新用户推送频率接口
const updateUserFrequency = async (frequency: 'daily' | 'weekly') => {
  try {
    const token = localStorage.getItem('token')
    if (!token) {
      console.error('更新推送频率失败: 未找到token')
      throw new Error('未登录')
    }

    console.log(`正在更新推送频率为: ${frequency}, token: ${token.substring(0,10)}...`);

    const response = await fetch(`${API_BASE_URL}/users/me/profile`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ push_frequency: frequency })
    });

    if (!response.ok) {
      console.error('更新推送频率失败: 服务器响应错误', response.status);
      const errorData = await response.json().catch(() => ({ detail: '更新推送频率失败' }));
      throw new Error(errorData.detail || '更新推送频率失败');
    }

    const responseData = await response.json();
    console.log('更新推送频率成功:', responseData);
    return responseData;

  } catch (error) {
    console.error('更新推送频率操作失败:', error);
    throw error;
  }
}

const ProfilePage = () => {
  const dispatch = useAppDispatch()
  const { 
    isLoggedIn, 
    interests, 
    frequency,
  } = useAppSelector(state => state.user)

  // 收藏的论文数量
  const favoritedPapersCount = useAppSelector(state => state.favorites.papers.length)
  
  // 推送频率选项
  const frequencyOptions = ['每日推送', '每周推送']
  
  // 用户数据
  const [userData, setUserData] = useState({
    username: '',
    email: '',
    avatar: defaultAvatar,
    level: 'Lv.初中',
    stats: {
      papers: favoritedPapersCount || 0,
      comments: 0,
      following: 0,
      points: 0,
      likes: 0
    }
  })

  // 加载用户数据
  useEffect(() => {
    const loadUserData = async () => {
      try {
        console.log('开始加载用户数据')
        const userInfo = await fetchUserInfo()
        console.log('获取到用户信息:', userInfo)
        
        if (userInfo) {
          console.log('设置用户数据:', {
            email: userInfo.email
          })
          
          setUserData(prev => ({
            ...prev,
            username: userInfo.username || '论文阅读者',
            email: userInfo.email || '',
          }))
        } else {
          console.log('未获取到用户信息，使用默认值')
        }
      } catch (error) {
        console.error('加载用户数据失败:', error)
        Taro.showToast({
          title: '加载用户数据失败',
          icon: 'none',
          duration: 2000
        })
      }
    }
    
    if (isLoggedIn) {
      loadUserData()
    }
  }, [isLoggedIn])

  // 跳转到兴趣设置页面
  const handleEditInterests = () => {
    Taro.navigateTo({
      url: '/pages/research-interests/index'
    })
  }
  
  // 处理频率选择
  const handleFrequencyChange = async (e) => {
    const value = parseInt(e.detail.value)
    const newFrequency = value === 0 ? 'daily' : 'weekly'
    
    try {
      console.log('Taro object in handleFrequencyChange (before updateUserFrequency):', Taro); 
      const result = await updateUserFrequency(newFrequency)
      if (result) {
        dispatch(setFrequency(newFrequency))
        console.log('Taro object in handleFrequencyChange (before success toast):', Taro); 
        Taro.showToast({
          title: `已设置为${newFrequency === 'daily' ? '每日' : '每周'}推送`,
          icon: 'success',
          duration: 2000
        })
      }
    } catch (error) {
      console.error('Error in handleFrequencyChange while updating frequency:', error); 
      console.log('Taro object in handleFrequencyChange (before error toast):', Taro); 
      Taro.showToast({
        title: error.message || '切换推送频率失败',
        icon: 'none',
        duration: 2000
      })
    }
  }

  // 处理退出登录
  const handleLogout = () => {
    Taro.showModal({
      title: '确认退出',
      content: '您确定要退出登录吗？',
      confirmText: '退出',
      confirmColor: '#FF4949',
      cancelText: '取消',
      success: function (res) {
        if (res.confirm) {
          localStorage.removeItem('token');
          localStorage.removeItem('userEmail');
          dispatch(logout());
          Taro.reLaunch({
            url: '/pages/index/index'
          })
        }
      }
    })
  }

  // 菜单项定义
  const menuItems = [
    // 我的资料暂时注释掉
    // {
    //   icon: 'user',
    //   color: '#4A89DC',
    //   title: '我的资料',
    //   onClick: () => Taro.showToast({ title: '功能开发中', icon: 'none' })
    // },
    {
      icon: 'bookmark',
      color: '#5EBD75',
      title: '研究兴趣',
      onClick: handleEditInterests,
    },
    {
      icon: 'calendar',
      color: '#F4B350',
      title: '推送频率',
      component: (
        <Picker 
          mode='selector' 
          range={frequencyOptions}
          onChange={handleFrequencyChange}
          value={frequency === 'daily' ? 0 : 1}
        >
          <View className='menu-title'>推送频率</View>
        </Picker>
      ),
    },
    {
      icon: 'star',
      color: '#4A89DC',
      title: '我的收藏',
      onClick: () => Taro.switchTab({ url: '/pages/favorites/index' }),
    },
    {
      icon: 'bell',
      color: '#FC6E51',
      title: '消息通知',
      onClick: () => Taro.showToast({ title: '功能开发中', icon: 'none' })
    }
  ]

  if (!isLoggedIn) {
    return (
      <View className='profile-not-login'>
        <Text className='login-prompt'>请先登录</Text>
        <CustomButton 
          type='primary' 
          onClick={() => Taro.navigateTo({ url: '/pages/login/index' })}
        >
          去登录
        </CustomButton>
      </View>
    )
  }

  return (
    <View className='profile-page'>
      {/* 顶部个人信息 */}
      <View className='profile-header'>
        <View className='header-actions'>
          <Text className='page-title'>个人中心</Text>
          <View className='header-buttons'>
            <View className='icon-button' onClick={() => Taro.showToast({ title: '设置功能开发中', icon: 'none' })}>
              <AtIcon value='settings' size='22' color='#666'></AtIcon>
            </View>
          </View>
        </View>
        
        <View className='user-info'>
          <Image className='avatar' src={userData.avatar} mode='aspectFill' />
          <View className='user-details'>
            <Text className='username'>{userData.email || '未登录'}</Text>
            <View className='user-meta'>
              <Text className='user-level'>{userData.level}</Text>
            </View>
          </View>
        </View>
      </View>

      {/* 用户统计信息 */}
      <View className='user-stats'>
        <View className='stat-item'>
          <Text className='stat-value'>{userData.stats.papers}</Text>
          <Text className='stat-label'>收藏</Text>
        </View>
        <View className='stat-item'>
          <Text className='stat-value'>{userData.stats.comments}</Text>
          <Text className='stat-label'>评论</Text>
        </View>
        <View className='stat-item'>
          <Text className='stat-value'>{userData.stats.following}</Text>
          <Text className='stat-label'>关注</Text>
        </View>
        <View className='stat-item'>
          <Text className='stat-value'>{userData.stats.likes}</Text>
          <Text className='stat-label'>获赞</Text>
        </View>
      </View>

      {/* 菜单列表 */}
      <View className='menu-list'>
        {menuItems.map((item, index) => (
          <View key={index} className='menu-item' onClick={item.onClick}>
            <View className='menu-icon' style={{ backgroundColor: item.color }}>
              <AtIcon value={item.icon} size='20' color='#FFF'></AtIcon>
            </View>
            <View className='menu-content'>
              {item.component || <Text className='menu-title'>{item.title}</Text>}
            </View>
            <AtIcon value='chevron-right' size='18' color='#CCC'></AtIcon>
          </View>
        ))}

        {/* 退出登录按钮 */}
        <View className='logout-button' onClick={handleLogout}>
          <Text>退出登录</Text>
        </View>
      </View>
    </View>
  )
}

export default ProfilePage 