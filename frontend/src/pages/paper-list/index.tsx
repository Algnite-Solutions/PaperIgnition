import { View, Text } from '@tarojs/components'
import { useEffect, useState } from 'react'
import Taro from '@tarojs/taro'
import { getPapers } from '../../services/paperService'
import './index.scss'

interface Paper {
  id: string
  title: string
  authors: string
  abstract: string
  tags: string[]
  publishDate: string
}

export default function PaperList() {
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPapers()
  }, [])

  const fetchPapers = async () => {
    try {
      setLoading(true)
      const response = await getPapers()
      if (response.statusCode === 200) {
        setPapers(response.data)
      }
    } catch (error) {
      console.error('获取论文列表失败', error)
      Taro.showToast({
        title: '获取论文列表失败',
        icon: 'none',
        duration: 2000
      })
    } finally {
      setLoading(false)
    }
  }

  const handlePaperClick = (paperId: string) => {
    Taro.navigateTo({
      url: `/pages/paper-detail/index?id=${paperId}`
    })
  }

  const handleBack = () => {
    Taro.navigateBack()
  }

  return (
    <View className='paper-list-page'>
      <View className='header'>
        <Text className='back' onClick={handleBack}>返回</Text>
        <Text className='title'>论文列表</Text>
      </View>
      
      {loading ? (
        <View className='loading'>加载中...</View>
      ) : (
        <View className='paper-list'>
          {papers.map(paper => (
            <View 
              key={paper.id} 
              className='paper-item'
              onClick={() => handlePaperClick(paper.id)}
            >
              <Text className='paper-title'>{paper.title}</Text>
              <Text className='paper-authors'>{paper.authors}</Text>
              <Text className='paper-abstract'>{paper.abstract}</Text>
              <View className='paper-tags'>
                {paper.tags.map(tag => (
                  <Text key={tag} className='paper-tag'>{tag}</Text>
                ))}
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  )
} 