import { View, Text, Input, CheckboxGroup, Checkbox } from '@tarojs/components'
import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { AtIcon } from 'taro-ui'
import { setInterestDescription, saveInterestsWithDescription } from '../../store/slices/userSlice'
import CustomButton from '../../components/ui/Button'
import './index.scss'

// 定义研究领域接口
interface ResearchDomain {
  id: number
  name: string
  description?: string
}

// 获取所有研究领域接口
const fetchResearchDomains = async (): Promise<ResearchDomain[]> => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/research-domains', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    })
    
    if (!response.ok) {
      throw new Error('获取研究领域失败')
    }
    
    return await response.json()
  } catch (error) {
    console.error('获取研究领域失败:', error)
    return []
  }
}

// 定义用户兴趣接口
interface UserInterests {
  description: string
  domain_ids: number[]
}

// 获取用户研究兴趣接口
const fetchUserInterests = async (): Promise<UserInterests | null> => {
  try {
    const token = localStorage.getItem('token')
    if (!token) throw new Error('未登录')
    
    // 获取用户邮箱
    const userEmail = localStorage.getItem('userEmail')
    if (!userEmail) throw new Error('未找到用户邮箱')
    
    const response = await fetch('http://127.0.0.1:8000/api/users/interests', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-User-Email': userEmail // 将邮箱作为请求头发送给后端
      }
    })
    
    if (!response.ok) {
      throw new Error('获取用户研究兴趣失败')
    }
    
    return await response.json()
  } catch (error) {
    console.error('获取用户研究兴趣失败:', error)
    return null
  }
}

// 更新用户研究兴趣接口
const updateUserInterests = async (interests: UserInterests): Promise<any> => {
  try {
    const token = localStorage.getItem('token')
    if (!token) throw new Error('未登录')
    
    // 获取用户邮箱
    const userEmail = localStorage.getItem('userEmail')
    if (!userEmail) throw new Error('未找到用户邮箱')
    
    const response = await fetch('http://127.0.0.1:8000/api/users/interests', {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-User-Email': userEmail // 将邮箱作为请求头发送给后端
      },
      body: JSON.stringify(interests)
    })
    
    if (!response.ok) {
      throw new Error('更新研究兴趣失败')
    }
    
    return await response.json()
  } catch (error) {
    console.error('更新研究兴趣失败:', error)
    return null
  }
}

const ResearchInterestsPage = () => {
  const dispatch = useAppDispatch()
  const { interests } = useAppSelector(state => state.user)
  
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [isEditMode, setIsEditMode] = useState(false)
  const [description, setDescription] = useState(interests.description || '')
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([])
  const [domains, setDomains] = useState<ResearchDomain[]>([])
  const [selectedDomains, setSelectedDomains] = useState<number[]>([])
  
  // 热门关键词
  const [popularKeywords, setPopularKeywords] = useState([
    'AI', '机器学习', '深度学习', '自然语言处理', '计算机视觉',
    '区块链', '物联网', '云计算', '大数据', '神经网络',
    '量子计算', '人机交互', '生物信息学', '知识图谱', '强化学习',
    '图神经网络', '推荐系统', '语音识别', '多模态学习', '联邦学习'
  ])

  // 加载研究领域和用户兴趣
  useEffect(() => {
    const loadData = async () => {
      try {
        // 获取所有研究领域
        const domainsData = await fetchResearchDomains()
        if (domainsData && domainsData.length > 0) {
          setDomains(domainsData)
        }
        
        // 获取用户已选研究兴趣
        const userInterests = await fetchUserInterests()
        if (userInterests) {
          setDescription(userInterests.description || '')
          setSelectedDomains(userInterests.domain_ids || [])
          
          // 解析描述中的关键词
          if (userInterests.description) {
            const keywordsArray = userInterests.description
              .split(',')
              .map(keyword => keyword.trim())
              .filter(keyword => keyword.length > 0)
            setSelectedKeywords(keywordsArray)
          }
          
          dispatch(setInterestDescription(userInterests.description || ''))
        }
      } catch (error) {
        console.error('加载数据失败:', error)
        Taro.showToast({
          title: '加载数据失败',
          icon: 'none',
          duration: 2000
        })
      } finally {
        setLoading(false)
      }
    }
    
    loadData()
  }, [dispatch])

  // 切换编辑模式
  const toggleEditMode = () => {
    setIsEditMode(!isEditMode)
  }

  // 处理关键词选择
  const handleKeywordToggle = (keyword: string) => {
    if (selectedKeywords.includes(keyword)) {
      // 如果已选中，则移除
      setSelectedKeywords(selectedKeywords.filter(k => k !== keyword))
    } else {
      // 如果未选中，则添加
      setSelectedKeywords([...selectedKeywords, keyword])
    }
  }

  // 保存研究兴趣
  const handleSave = async () => {
    setSaving(true)
    try {
      // 将选择的关键词组合成描述
      const newDescription = selectedKeywords.join(', ')
      setDescription(newDescription)
      
      // 更新后端数据
      await updateUserInterests({
        description: newDescription,
        domain_ids: selectedDomains
      })
      
      // 更新Redux状态
      dispatch(saveInterestsWithDescription(newDescription))
      
      Taro.showToast({
        title: '保存成功',
        icon: 'success',
        duration: 2000
      })
      
      // 切换回查看模式
      setIsEditMode(false)
    } catch (error) {
      console.error('保存失败:', error)
      Taro.showToast({
        title: '保存失败',
        icon: 'none',
        duration: 2000
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <View className='research-interests-loading'>
        <Text>加载中...</Text>
      </View>
    )
  }

  return (
    <View className='research-interests-page'>
      <View className='header'>
        <View className='header-actions'>
          <View className='back-button' onClick={() => Taro.navigateBack()}>
            <AtIcon value='chevron-left' size='24' color='#333'></AtIcon>
          </View>
          <Text className='page-title'>研究兴趣</Text>
          <View className='placeholder'></View>
        </View>
      </View>

      <View className='content'>
        {!isEditMode ? (
          // 查看模式
          <View className='view-mode'>
            <View className='section'>
              <View className='section-header'>
                <Text className='section-title'>我的研究兴趣</Text>
                <View className='edit-button' onClick={toggleEditMode}>
                  <AtIcon value='edit' size='18' color='#4a89dc'></AtIcon>
                  <Text className='edit-text'>修改</Text>
                </View>
              </View>
              
              {selectedKeywords.length > 0 ? (
                <View className='keywords-container'>
                  {selectedKeywords.map((keyword, index) => (
                    <View key={index} className='keyword-tag keyword-selected'>
                      {keyword}
                    </View>
                  ))}
                </View>
              ) : (
                <View className='empty-state'>
                  <Text className='empty-text'>暂无研究兴趣，点击"修改"添加</Text>
                </View>
              )}
            </View>
            
            <View className='section'>
              <Text className='section-title'>热门研究领域</Text>
              <View className='keywords-container'>
                {popularKeywords.slice(0, 10).map((keyword, index) => (
                  <View key={index} className='keyword-tag'>
                    {keyword}
                  </View>
                ))}
              </View>
            </View>
          </View>
        ) : (
          // 编辑模式
          <View className='edit-mode'>
            <View className='section'>
              <Text className='section-title'>选择研究兴趣</Text>
              <Text className='section-subtitle'>点击关键词进行选择或取消</Text>
              
              <View className='keywords-container'>
                {popularKeywords.map((keyword, index) => (
                  <View 
                    key={index} 
                    className={`keyword-tag ${selectedKeywords.includes(keyword) ? 'keyword-selected' : ''}`}
                    onClick={() => handleKeywordToggle(keyword)}
                  >
                    {keyword}
                    {selectedKeywords.includes(keyword) && (
                      <AtIcon value='check' size='12' color='#fff'></AtIcon>
                    )}
                  </View>
                ))}
              </View>
            </View>
            
            <View className='button-container'>
              <CustomButton
                type='default'
                onClick={toggleEditMode}
                className='cancel-button'
              >
                取消
              </CustomButton>
              <CustomButton
                type='primary'
                loading={saving}
                onClick={handleSave}
                className='save-button'
              >
                保存
              </CustomButton>
            </View>
          </View>
        )}
      </View>
    </View>
  )
}

export default ResearchInterestsPage 