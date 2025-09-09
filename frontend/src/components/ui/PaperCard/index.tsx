import { View, Text, Image } from '@tarojs/components'
import { useAppDispatch, useAppSelector } from '../../../store/hooks'
import { setPaperFeedback, clearPaperFeedback } from '../../../store/slices/paperSlice'
import { addFavorite, removeFavorite } from '../../../store/slices/favoritesSlice'
import { AtIcon } from 'taro-ui'
import Taro from '@tarojs/taro'
import { addPaperToFavorites, removePaperFromFavorites } from '../../../services/favoriteService'
import likeIcon from '../../../assets/icons/like.png'
import dislikeIcon from '../../../assets/icons/dislike.png'
import heartIcon from '../../../assets/icons/heart.png'
import { useState } from 'react'
import './index.scss'

export interface Paper {
  id: string
  title: string
  authors: string
  abstract: string
  url?: string
  publishDate?: string
  submittedDate?: string
  comments?: string
  showMore?: boolean
}

interface PaperCardProps {
  paper: Paper
  onClick?: () => void
}

const PaperCard: React.FC<PaperCardProps> = ({ paper, onClick }) => {
  const dispatch = useAppDispatch()
  const feedback = useAppSelector((state: any) => state.paper.feedbacks[paper.id])
  const favoritePapers = useAppSelector((state: any) => state.favorites.papers)
  const [expanded, setExpanded] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  
  // 检查是否已收藏
  const isFavorited = favoritePapers.some((favPaper: any) => favPaper.id === paper.id)

  const handleFeedback = (isPositive: boolean, e) => {
    e.stopPropagation()
    if (feedback === isPositive) {
      dispatch(clearPaperFeedback(paper.id))
    } else {
      dispatch(setPaperFeedback({ paperId: paper.id, isPositive }))
    }
  }

  const handleFavorite = async (e) => {
    e.stopPropagation()
    setIsUploading(true)
    
    try {
      const token = localStorage.getItem('token')
      if (!token) {
        Taro.showToast({
          title: '请先登录',
          icon: 'none'
        })
        return
      }

      if (isFavorited) {
        // 取消收藏
        await removePaperFromFavorites(paper.id)
        dispatch(removeFavorite(paper.id))
        Taro.showToast({
          title: '已取消收藏',
          icon: 'none'
        })
      } else {
        // 添加收藏
        await addPaperToFavorites({
          paper_id: paper.id,
          title: paper.title,
          authors: Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors,
          abstract: paper.abstract,
          url: paper.url
        })
        dispatch(addFavorite(paper))
        Taro.showToast({
          title: '已添加收藏',
          icon: 'success'
        })
      }
    } catch (error) {
      console.error('收藏操作失败:', error)
      Taro.showToast({
        title: error.message || '操作失败',
        icon: 'none'
      })
    } finally {
      setIsUploading(false)
    }
  }

  const handleClick = () => {
    if (onClick) {
      onClick()
    } else {
      Taro.navigateTo({
        url: `/pages/paper-detail/index?id=${paper.id}`
      })
    }
  }

  const toggleExpand = (e) => {
    e.stopPropagation()
    setExpanded(!expanded)
  }

  // 生成随机提交日期
  const getSubmittedDate = () => {
    if (paper.submittedDate) return paper.submittedDate;
    
    const currentYear = new Date().getFullYear();
    const randomDay = 1 + Math.floor(Math.random() * 28);
    const randomMonth = new Date().getMonth() + 1;
    
    return `${randomDay} ${getMonthName(randomMonth)}, ${currentYear}`;
  };

  // 生成随机发布日期
  const getAnnouncedDate = () => {
    if (paper.publishDate) return paper.publishDate;
    
    const currentYear = new Date().getFullYear();
    const randomMonth = getMonthName(new Date().getMonth() + 1);
    
    return `${randomMonth} ${currentYear}`;
  };

  // 获取月份名称
  const getMonthName = (month) => {
    const monthNames = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'
    ];
    return monthNames[month - 1];
  };

  // 生成随机评论
  const getComments = () => {
    if (paper.comments) return paper.comments;
    
    const comments = [
      "Accepted at International Conference on Machine Learning 2025",
      "Published in: IEEE Transactions on Pattern Analysis and Machine Intelligence",
      "Accepted at CVPR 2025",
      "To appear in Advances in Neural Information Processing Systems 35",
      "Accepted at International Conference on Robotics and Automation 2025",
      "Published in: Nature Machine Intelligence"
    ];
    
    return comments[Math.floor(Math.random() * comments.length)];
  };

  return (
    <View className='paper-card' onClick={handleClick}>
      <View className='paper-title'>{paper.title}</View>
      
      <View className='paper-authors'>
        <Text>Authors: {paper.authors}</Text>
      </View>
      
      <View className={`paper-abstract ${expanded ? 'expanded' : ''}`}>
        <Text className='abstract-heading'>Abstract: </Text>
        <Text className='abstract-content'>{paper.abstract}</Text>
        
        {paper.showMore !== false && (
          <View className='show-more-container' onClick={toggleExpand}>
            <AtIcon value={expanded ? 'chevron-up' : 'chevron-down'} size='16' color='#4A89DC' />
            <Text className='show-more-text'>{expanded ? 'Less' : 'More'}</Text>
          </View>
        )}
      </View>
      
      <View className='paper-actions'>
        <View className='meta-info'>
          <View className='submission-info'>
            <AtIcon value='calendar' size='14' color='#999' />
            <Text>Submitted {getSubmittedDate()}</Text>
          </View>
          
          {getComments() && (
            <View className='comments-info'>
              <Text className='comments-content'>{getComments()}</Text>
            </View>
          )}
        </View>
        
        <View className='feedback-buttons'>
          <View 
            className={`action-button like-button ${feedback === true ? 'active' : ''}`}
            onClick={(e) => handleFeedback(true, e)}
          >
            {feedback === true ? (
              <Text className='emoji-icon'>👍</Text>
            ) : (
              <Image className='feedback-icon' src={likeIcon} />
            )}
            <Text className='action-text'>有用</Text>
          </View>
          
          <View 
            className={`action-button dislike-button ${feedback === false ? 'active' : ''}`}
            onClick={(e) => handleFeedback(false, e)}
          >
            {feedback === false ? (
              <Text className='emoji-icon'>👎</Text>
            ) : (
              <Image className='feedback-icon' src={dislikeIcon} />
            )}
            <Text className='action-text'>无用</Text>
          </View>
          
          <View 
            className={`action-button favorite-button ${isFavorited ? 'active' : ''} ${isUploading ? 'uploading' : ''}`}
            onClick={handleFavorite}
          >
            {isFavorited ? (
              <Text className='emoji-icon' style={{ color: '#ff4757' }}>❤️</Text>
            ) : (
              <Image className='feedback-icon' src={heartIcon} />
            )}
            <Text className='action-text'>收藏</Text>
          </View>
        </View>
      </View>
    </View>
  )
}

export default PaperCard 