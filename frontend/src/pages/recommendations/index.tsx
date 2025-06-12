import { View, Text } from '@tarojs/components'
import React, { useEffect } from 'react'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import {
  fetchRecommendationsStart,
  fetchRecommendationsSuccess,
  fetchRecommendationsFailure,
  clearRecommendations
} from '../../store/slices/paperSlice'
import PaperCard from '../../components/ui/PaperCard'
import CustomButton from '../../components/ui/Button'
import Taro from '@tarojs/taro'
import { API_BASE_URL } from '../../config/api'
import './index.scss'

const Recommendations = () => {
  const dispatch = useAppDispatch()
  const {
    recommendations,
    loading,
    error,
    hasMore,
    page
  } = useAppSelector((state: any) => state.paper)
  
  // 从用户状态中获取登录状态和邮箱
  const { isLoggedIn, email } = useAppSelector((state: any) => state.user)

  const fetchRecommendations = async () => {
    try {
      dispatch(fetchRecommendationsStart())
      
      // 检查用户是否已登录
      if (!isLoggedIn || !email) {
        throw new Error('用户未登录，请先登录')
      }
      
      // 调用后端推荐接口
      const response = await fetch(`${API_BASE_URL}/api/papers/recommendations/${email}`)
      
      if (response.ok) {
        const papers = await response.json()
        dispatch(fetchRecommendationsSuccess({
          papers: papers,
          hasMore: false // 暂时设为false，后续可根据分页需求调整
        }))
      } else {
        const errorData = await response.json()
        throw new Error(errorData.detail || '获取推荐论文失败')
      }
    } catch (err) {
      dispatch(fetchRecommendationsFailure(err instanceof Error ? err.message : '获取推荐失败'))
    }
  }

  const handleLoadMore = () => {
    if (!loading && hasMore) {
      fetchRecommendations()
    }
  }

  const handlePaperClick = (paperId: string) => {
    Taro.navigateTo({
      url: `/pages/paper-detail/index?id=${paperId}`
    })
  }

  // 初始加载
  useEffect(() => {
    dispatch(clearRecommendations())
    if (isLoggedIn && email) {
      fetchRecommendations()
    }
  }, [isLoggedIn, email]) // 当登录状态或邮箱变化时重新获取推荐

  if (!isLoggedIn) {
    return (
      <View className='recommendations-not-login'>
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
    <View className='recommendations-page'>
      <View className='header'>
        <Text className='title'>推荐论文</Text>
      </View>

      <View className='papers-list'>
        {recommendations.map(paper => (
          <PaperCard
            key={paper.id}
            paper={paper}
            onClick={() => handlePaperClick(paper.id)}
          />
        ))}
      </View>

      {error && <Text className='error-message'>{error}</Text>}

      {loading && (
        <View className='loading'>
          <Text>加载中...</Text>
        </View>
      )}

      {!loading && hasMore && (
        <View className='load-more' onClick={handleLoadMore}>
          <Text>加载更多</Text>
        </View>
      )}

      {!loading && !hasMore && recommendations.length > 0 && (
        <View className='no-more'>
          <Text>没有更多了</Text>
        </View>
      )}

      {!loading && recommendations.length === 0 && !error && (
        <View className='empty'>
          <Text>暂无推荐论文</Text>
        </View>
      )}
    </View>
  )
}

export default Recommendations 