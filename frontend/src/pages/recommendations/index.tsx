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
import Taro from '@tarojs/taro'
import { getPapers } from '../../services/paperService'
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

  const fetchRecommendations = async (pageNum: number) => {
    try {
      dispatch(fetchRecommendationsStart())
      
      // 通过服务获取论文数据
      const response = await getPapers()
      
      if (response.statusCode === 200 && response.data) {
        dispatch(fetchRecommendationsSuccess({
          papers: response.data,
          hasMore: pageNum < 3 // 模拟只有3页数据
        }))
      } else {
        throw new Error('获取论文数据失败')
      }
    } catch (err) {
      dispatch(fetchRecommendationsFailure(err instanceof Error ? err.message : '获取推荐失败'))
    }
  }

  const handleLoadMore = () => {
    if (!loading && hasMore) {
      fetchRecommendations(page)
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
    fetchRecommendations(1)
  }, [])

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

      {!loading && recommendations.length === 0 && (
        <View className='empty'>
          <Text>暂无推荐论文</Text>
        </View>
      )}
    </View>
  )
}

export default Recommendations 