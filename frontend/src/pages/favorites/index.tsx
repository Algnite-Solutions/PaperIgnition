import { View, Text, Image } from '@tarojs/components'
import { useState, useEffect } from 'react'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { loadFavoritesStart, loadFavoritesSuccess, loadFavoritesFailure, removeFavorite } from '../../store/slices/favoritesSlice'
import { AtIcon } from 'taro-ui'
import Taro, { useDidShow } from '@tarojs/taro'
import { fetchUserFavorites, FavoriteResponse } from '../../services/favoriteService'
import './index.scss'
import PaperCard, { Paper } from '../../components/ui/PaperCard'
import CustomButton from '../../components/ui/Button'

// 收藏页面的处理点击事件
const handlePaperClick = (paperId: string) => {
    Taro.navigateTo({
    url: `/pages/paper-detail/index?id=${paperId}`
  })
}

const Favorites = () => {
  const dispatch = useAppDispatch()
  const { papers, loading, error } = useAppSelector(state => state.favorites)
  const { isLoggedIn } = useAppSelector(state => state.user)

  // 从后端获取收藏列表
  const fetchFavorites = async () => {
    const token = localStorage.getItem('token')
    if (!token) return
    
    try {
      dispatch(loadFavoritesStart())
      
      const favorites = await fetchUserFavorites()
      // 转换为前端需要的格式
      const formattedPapers = favorites.map((fav: FavoriteResponse) => ({
        id: fav.paper_id,
        title: fav.title,
        authors: fav.authors,
        abstract: fav.abstract,
        url: fav.url
      }))
      
      dispatch(loadFavoritesSuccess(formattedPapers))
    } catch (error) {
      console.error('获取收藏列表失败:', error)
      dispatch(loadFavoritesFailure(error.message))
    }
  }

    // 页面加载时获取收藏列表
  useEffect(() => {
    if (isLoggedIn) {
      fetchFavorites()
    }
  }, [isLoggedIn])

  // 页面显示时重新获取收藏列表
  useDidShow(() => {
    if (isLoggedIn) {
      fetchFavorites()
  }
  })

 

  if (!isLoggedIn) {
    return (
      <View className='favorites-not-login'>
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
    <View className='favorites-page'>
      <View className='page-header'>
        <Text className='page-title'>我的收藏</Text>
      </View>

      {loading ? (
        <View className='loading-container'>
          <AtIcon value='loading-3' size='30' color='#1296db' className='loading-icon' />
          <Text className='loading-text'>加载中...</Text>
        </View>
      ) : papers.length > 0 ? (
        <View className='favorites-list'>
          {papers.map(paper => (
            <PaperCard
              key={paper.id}
              paper={paper}
              onClick={() => handlePaperClick(paper.id)}
            />
          ))}
        </View>
      ) : (
        <View className='empty-container'>
          <View className='empty-icon-container'>
            <AtIcon value='heart' size='48' color='#ddd' />
          </View>
          <Text className='empty-title'>暂无收藏</Text>
          <Text className='empty-desc'>您还没有收藏任何论文</Text>
        </View>
      )}
    </View>
  )
}

export default Favorites 