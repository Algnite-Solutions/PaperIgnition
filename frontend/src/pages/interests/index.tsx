import { View, Text, Input, Picker } from '@tarojs/components'
import { useState, useEffect } from 'react'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import {
  setFrequency,
  saveInterestsStart,
  saveInterestsSuccess,
  saveInterestsFailure,
  saveInterestsWithDescription,
  setInterestDescription,
  loginSuccess
} from '../../store/slices/userSlice'
import { addFavorite, removeFavorite } from '../../store/slices/favoritesSlice'
import { AtTabs, AtTabsPane, AtIcon, AtToast, AtTag } from 'taro-ui'
import CustomButton from '../../components/ui/Button'
import Card from '../../components/ui/Card'
import InterestPaperCard from '../../components/ui/InterestPaperCard'
import { Paper } from '../../components/ui/PaperCard'
import Taro from '@tarojs/taro'
import './index.scss'

// 模拟搜索论文API调用
const searchPapers = async (query: string): Promise<Paper[]> => {
  // 模拟API延时
  await new Promise(resolve => setTimeout(resolve, 500))
  
  // 模拟搜索结果
  return [
    {
      id: '1001',
      title: 'Attention Is All You Need',
      authors: ['Ashish Vaswani', 'Noam Shazeer', 'Niki Parmar', 'Jakob Uszkoreit', 'Llion Jones', 'Aidan N. Gomez', 'Łukasz Kaiser', 'Illia Polosukhin'],
      abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.',
      tags: ['Deep Learning', 'NLP', 'Transformer'],
      submittedDate: '12 June, 2017',
      comments: 'Published in: Advances in Neural Information Processing Systems 30'
    },
    {
      id: '1002',
      title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
      authors: ['Jacob Devlin', 'Ming-Wei Chang', 'Kenton Lee', 'Kristina Toutanova'],
      abstract: 'We introduce a new language representation model called BERT, which stands for Bidirectional Encoder Representations from Transformers. Unlike recent language representation models, BERT is designed to pre-train deep bidirectional representations from unlabeled text by jointly conditioning on both left and right context in all layers. As a result, the pre-trained BERT model can be fine-tuned with just one additional output layer to create state-of-the-art models for a wide range of tasks, such as question answering and language inference, without substantial task-specific architecture modifications.',
      tags: ['Deep Learning', 'NLP', 'BERT'],
      submittedDate: '11 October, 2018',
      comments: 'Published in: Proceedings of NAACL-HLT 2019'
    },
    {
      id: '1003',
      title: 'GPT-4 Technical Report',
      authors: ['OpenAI'],
      abstract: 'We report the development of GPT-4, a large-scale, multimodal model which can accept image and text inputs and produce text outputs. While less capable than humans in many real-world scenarios, GPT-4 exhibits human-level performance on various professional and academic benchmarks, including passing a simulated bar exam with a score around the top 10% of test takers. GPT-4 is a Transformer-based model pre-trained to predict the next token in a document, using both publicly available data and data licensed from third-party providers.',
      tags: ['GPT-4', 'Large Language Models', 'Multimodal'],
      submittedDate: '27 March, 2023',
      comments: 'Technical Report'
    }
  ].filter(paper => 
    !query || 
    paper.title.toLowerCase().includes(query.toLowerCase()) || 
    paper.authors.some(author => author.toLowerCase().includes(query.toLowerCase())) ||
    paper.abstract.toLowerCase().includes(query.toLowerCase())
  )
}

// AI领域选项
const AI_DOMAINS = [
  { name: '自然语言处理 (NLP)', active: false },
  { name: '计算机视觉 (CV)', active: false },
  { name: '大型语言模型 (LLM)', active: false },
  { name: '机器学习 (ML)', active: false },
  { name: '深度学习 (DL)', active: false },
  { name: '强化学习 (RL)', active: false },
  { name: '生成式AI (Generative AI)', active: false },
  { name: '多模态学习 (Multimodal)', active: false },
  { name: '语音识别 (ASR)', active: false },
  { name: '推荐系统 (Recommender)', active: false },
  { name: '图神经网络 (GNN)', active: false },
  { name: '联邦学习 (Federated)', active: false },
  { name: '知识图谱 (Knowledge Graph)', active: false },
]

const Interests = () => {
  const dispatch = useAppDispatch()
  const {
    frequency,
    interests,
    loading,
    error
  } = useAppSelector(state => state.user)

  // 获取收藏的论文
  const favoritedPapers = useAppSelector(state => state.favorites.papers)
  
  const [currentTab, setCurrentTab] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Paper[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [interestDescription, setLocalInterestDescription] = useState(interests.description || '')
  const [aiDomains, setLocalAiDomains] = useState(AI_DOMAINS.map(d => ({...d, active: false})))
  const [isFromRegistration, setIsFromRegistration] = useState(false)
  const [profileLoading, setProfileLoading] = useState(true)
  const [profileError, setProfileError] = useState<string | null>(null)

  const frequencyOptions = ['每日 (Daily)', '每周 (Weekly)']
  
  // Tab页内容
  const tabList = [
    { title: '订阅设置' },
    { title: '兴趣配置' }
  ]
  
  // 检查是否是从注册页面跳转过来
  useEffect(() => {
    // 检查localStorage中的标志
    const fromRegistration = localStorage.getItem('fromRegistration')
    if (fromRegistration) {
      setIsFromRegistration(true)
      // 清除标志，避免下次进入该页面时仍然被认为是从注册页面来的
      localStorage.removeItem('fromRegistration')
      // 如果是从注册页面跳转来的，默认显示欢迎提示
      if (Taro && typeof Taro.showModal === 'function') {
        Taro.showModal({
          title: '欢迎加入',
          content: '为了给您提供更精准的论文推荐，请设置您的研究兴趣领域',
          showCancel: false,
          confirmText: '开始设置'
        })
      } else {
        alert('欢迎加入! 为了给您提供更精准的论文推荐，请设置您的研究兴趣领域')
      }
    }
  }, [])

  // New Effect to fetch user profile data on mount
  useEffect(() => {
    const fetchCurrentUserProfile = async () => {
      setProfileLoading(true)
      setProfileError(null)
      console.log('[Interests Page] Fetching current user profile...')
      const token = localStorage.getItem('token') // Prefer localStorage directly for H5

      if (!token) {
        console.warn('[Interests Page] No token found, cannot fetch profile.')
        setProfileError('用户未登录，无法获取配置信息。')
        setProfileLoading(false)
        // Optionally redirect to login
        // Taro.redirectTo({ url: '/pages/login/index' })
        return
      }

      try {
        const response = await fetch('http://127.0.0.1:8000/api/users/me', {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        })

        if (response.ok) {
          const userData = await response.json()
          console.log('[Interests Page] Profile data fetched:', userData)

          // Update Redux store and local state
          // Assuming backend returns `push_frequency` and `interests_description` (as list)
          if (userData.push_frequency) {
            dispatch(setFrequency(userData.push_frequency))
          }
          
          const backendInterests: string[] = userData.interests_description || []
          const joinedInterests = backendInterests.join('、')
          dispatch(setInterestDescription(joinedInterests)) // Update Redux
          setLocalInterestDescription(joinedInterests) // Update local state for controlled input

          // Update AI domain tags based on fetched interests
          const updatedAiDomains = AI_DOMAINS.map(domain => {
            // Extract the Chinese part of the domain name for comparison
            const domainNameKey = domain.name.split(' ')[0]
            return {
              ...domain,
              active: backendInterests.some(userInterest => userInterest.trim() === domainNameKey)
            }
          })
          setLocalAiDomains(updatedAiDomains)
          
          // Potentially update entire user profile in Redux if GET /me returns more comprehensive data
          // For example, if loginSuccess action is suitable for this:
          // dispatch(loginSuccess(userData)) // This depends on loginSuccess payload and what GET /me returns

        } else {
          const errorData = await response.json().catch(() => ({ detail: '获取用户信息失败' }))
          console.error('[Interests Page] Failed to fetch profile:', response.status, errorData)
          setProfileError(errorData.detail || `获取配置失败 (HTTP ${response.status})`)
        }
      } catch (err) {
        console.error('[Interests Page] Network error fetching profile:', err)
        setProfileError(err instanceof Error ? err.message : '网络错误，获取配置失败')
      }
      setProfileLoading(false)
    }

    fetchCurrentUserProfile()
  }, [dispatch])

  // 处理订阅频率选择
  const handleFrequencyChange = (e) => {
    const value = parseInt(e.detail.value)
    dispatch(setFrequency(value === 0 ? 'daily' : 'weekly'))
  }
  
  // 处理论文选择 - 修改为收藏功能
  const handlePaperSelect = (paperId: string) => {
    // 查找要添加或移除的论文
    const paper = searchResults.find(p => p.id === paperId)
    if (!paper) return
    
    // 检查论文是否已在收藏中
    const isFavorited = favoritedPapers.some(p => p.id === paperId)
    
    let toastTitle = ''
    let toastIcon: 'success' | 'none' = 'none'

    if (isFavorited) {
      // 从收藏中移除
      dispatch(removeFavorite(paperId))
      toastTitle = '已从收藏移除'
      toastIcon = 'none'
    } else {
      // 添加到收藏
      dispatch(addFavorite(paper))
      toastTitle = '已添加到收藏'
      toastIcon = 'success'
    }

    if (Taro && typeof Taro.showToast === 'function') {
      Taro.showToast({
        title: toastTitle,
        icon: toastIcon,
        duration: 1500
      })
    } else {
      alert(toastTitle)
    }
    
    if (Taro.getEnv() !== Taro.ENV_TYPE.WEB) { // 仅在非H5环境尝试振动
      if (Taro && typeof Taro.vibrateShort === 'function') {
        try { Taro.vibrateShort({ type: 'medium' }) } catch (e) { console.warn('Vibrate failed', e) }
      } else {
        console.warn('Taro.vibrateShort is not a function in this non-H5 environment?')
      }
    } else {
      console.log('H5 environment, vibration skipped for paper select.')
    }
  }
  
  // 处理兴趣描述变更
  const handleDescriptionChange = (e) => {
    const value = e.detail.value
    setLocalInterestDescription(value)
  }
  
  // 处理搜索查询变更
  const handleSearchChange = (e) => {
    setSearchQuery(e.detail.value)
  }
  
  // 处理AI领域选择
  const handleDomainClick = (index: number) => {
    const updatedDomains = [...aiDomains]
    updatedDomains[index].active = !updatedDomains[index].active
    setLocalAiDomains(updatedDomains)

    const selectedDomains = updatedDomains
      .filter(domain => domain.active)
      .map(domain => domain.name.split(' ')[0])
    
    const newDescription = selectedDomains.join('、')
    setLocalInterestDescription(newDescription)
  }
  
  // 执行搜索
  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults([])
      return
    }
    
    setIsSearching(true)
    try {
      const results = await searchPapers(searchQuery)
      setSearchResults(results)
    } catch (error) {
      const errMsg = '搜索失败'
      if (Taro && typeof Taro.showToast === 'function') {
        Taro.showToast({
          title: errMsg,
          icon: 'none'
        })
      } else {
        alert(errMsg)
      }
    } finally {
      setIsSearching(false)
    }
  }
  
  // 保存兴趣设置
  const handleSave = async () => {
    console.log('[ Interests Page handleSave ] ==> Function Start');

    dispatch(saveInterestsStart());
    console.log('[ Interests Page handleSave ] ==> Dispatched saveInterestsStart (loading should be true)');

    let token: string | null = null;
    if (Taro && typeof Taro.getStorageSync === 'function') {
      try {
        token = Taro.getStorageSync('token');
      } catch (e) {
        if (typeof localStorage !== 'undefined') {
          token = localStorage.getItem('token');
        }
      }
    } else if (typeof localStorage !== 'undefined') {
      token = localStorage.getItem('token');
    } 

    if (!token) {
      const noTokenMsg = '用户未登录，无法保存设置。';
      dispatch(saveInterestsFailure(noTokenMsg));
      if (Taro && typeof Taro.showToast === 'function') {
        Taro.showToast({ title: '请先登录后操作', icon: 'none', duration: 2000 });
      } else {
        alert('请先登录后操作');
      }
      Taro.redirectTo({ url: '/pages/login/index' });
      return;
    }

    let updateData: { interests_description?: string[]; push_frequency?: 'daily' | 'weekly' } = {};

    try {
      let interestsList: string[] = [];
      if (interestDescription && interestDescription.trim()) {
        const standardizedDescription = interestDescription.replace(/,/g, '、');
        interestsList = standardizedDescription.split('、')
          .map(item => item.trim())
          .filter(item => item.length > 0);
      }
      
      if (interestsList.length === 0 && interestDescription && interestDescription.trim().length > 0) {
        interestsList = [interestDescription.trim()];
      }

      updateData = { 
        interests_description: interestsList,
        push_frequency: frequency
      };

      console.log('[ Interests Page handleSave ] ==> Constructed updateData (with push_frequency):', updateData);
      console.log('[ Interests Page handleSave ] ==> About to make network request. Current Taro object:', Taro, 'Type of Taro.request:', typeof Taro.request);

      let apiResponse;
      let responseData;
      let responseOk = false;
      let statusCode = 500; // Default to server error

      try {
        console.log('[ Interests Page handleSave ] ==> Attempting network request with fetch.');
        const fetchResponse = await fetch('http://127.0.0.1:8000/api/users/me/profile', {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(updateData)
        });
        
        console.log('[ Interests Page handleSave ] ==> fetch call completed. Status:', fetchResponse.status);
        statusCode = fetchResponse.status;
        responseOk = fetchResponse.ok;

        // Try to parse JSON regardless of status, as error details might be in the body
        try {
          responseData = await fetchResponse.json();
          console.log('[ Interests Page handleSave ] ==> fetch response JSON parsed:', responseData);
        } catch (jsonError) {
          console.warn('[ Interests Page handleSave ] ==> Error parsing fetch response as JSON:', jsonError);
          // If JSON parsing fails, try to get text, it might be a non-JSON error response
          try {
            responseData = { detail: await fetchResponse.text() }; // Store it in a way that later logic can access
             console.log('[ Interests Page handleSave ] ==> fetch response TEXT parsed:', responseData.detail);
          } catch (textError) {
            console.warn('[ Interests Page handleSave ] ==> Error parsing fetch response as TEXT:', textError);
            responseData = { detail: 'Failed to parse server response.' };
          }
        }
        apiResponse = { statusCode, data: responseData }; // Mimic Taro.request response structure for existing logic

      } catch (networkError) {
        // This catch block is for actual network errors (e.g., DNS resolution, server unreachable)
        console.error('[ Interests Page handleSave ] ==> Network error during fetch:', networkError);
        const errorMsg = networkError instanceof Error ? networkError.message : '网络请求失败，请检查网络连接';
        dispatch(saveInterestsFailure(errorMsg));
        // Ensure UI feedback for network error
        if (Taro && typeof Taro.showToast === 'function') {
          Taro.showToast({ title: errorMsg, icon: 'none', duration: 2000 });
        } else {
          alert(errorMsg + ' (Taro.showToast不可用)');
        }
        return; // Stop further execution in case of network failure
      }

      console.log('[ Interests Page handleSave ] ==> API Response (from fetch wrapper):', apiResponse);

      if (responseOk) { // Check was fetchResponse.ok
        dispatch(saveInterestsWithDescription(interestDescription))
        
        if (Taro && typeof Taro.showToast === 'function') {
          Taro.showToast({
            title: '设置已成功保存',
            icon: 'success',
            duration: 1500
          })
        } else {
          alert('设置已成功保存 (Taro.showToast 不可用)')
        }
        
        if (Taro.getEnv() !== Taro.ENV_TYPE.WEB) {
          if (Taro && typeof Taro.vibrateShort === 'function') {
            try { 
              console.log('Attempting vibration in non-H5 env')
              Taro.vibrateShort({ type: 'medium' }) 
            } catch (e) { 
              console.warn('Vibration failed in non-H5 env:', e) 
            }
          } else {
            console.warn('Taro.vibrateShort is not defined in non-H5 env?')
          }
        } else {
          console.log('H5 environment, vibration skipped for save action.')
        }
        
        // Navigation logic (existing)
        setTimeout(() => {
          const profilePath = '/pages/profile/index' // 目标个人主页 (保留以备将来可能需要)
          const recommendationsPath = '/pages/recommendations/index' // 目标推荐页

          if (isFromRegistration) {
            if (Taro && typeof Taro.showModal === 'function') {
              Taro.showModal({
                title: '设置完成',
                content: '您的研究兴趣已设置成功！接下来将为您推荐相关论文。',
                showCancel: false,
                confirmText: '开始探索',
                success: () => {
                  console.log('[ Interests Page handleSave ] ==> Navigating to recommendations (from registration).');
                  if (Taro && typeof Taro.switchTab === 'function') {
                    Taro.switchTab({ url: recommendationsPath }).catch(() => {
                      Taro.redirectTo({ url: recommendationsPath }); // Fallback for switchTab failure
                    });
                  } else if (Taro && typeof Taro.redirectTo === 'function') {
                    Taro.redirectTo({ url: recommendationsPath })
                  } else if (Taro.getEnv() === Taro.ENV_TYPE.WEB) {
                    window.location.href = recommendationsPath
                  }
                }
              })
            } else {
              alert('设置完成! 您的研究兴趣已设置成功！接下来将为您推荐相关论文。')
              if (Taro.getEnv() === Taro.ENV_TYPE.WEB) window.location.href = recommendationsPath
            }
          } else {
            // 常规保存后，也跳转到推荐页
            console.log('[ Interests Page handleSave ] ==> Navigating to recommendations (regular save).');
            if (Taro && typeof Taro.redirectTo === 'function') {
              Taro.redirectTo({ url: recommendationsPath });
            } else if (Taro.getEnv() === Taro.ENV_TYPE.WEB) {
              window.location.href = recommendationsPath;
            } else {
              // Fallback for non-H5 if redirectTo is not available (unlikely for core API)
              // This case might indicate a deeper issue with Taro environment.
              console.warn('[ Interests Page handleSave ] ==> Taro.redirectTo is not available in non-H5 env. Navigation might fail.');
              // As a last resort, try navigateTo, though it's not ideal for replacing the current page.
              if (Taro && typeof Taro.navigateTo === 'function') {
                Taro.navigateTo({ url: recommendationsPath });
              }
            }
          }
        }, 1500)
      } else {
        // Use responseData.detail or a generic message if detail is not available
        let errorDetailMsg = `保存失败 (HTTP ${statusCode})`; // Default error message
        if (responseData && responseData.detail) {
          if (typeof responseData.detail === 'string') {
            errorDetailMsg = responseData.detail;
          } else if (Array.isArray(responseData.detail)) {
            // Format FastAPI validation errors
            errorDetailMsg = responseData.detail.map(err => `${err.loc ? err.loc.join(' -> ') + ': ' : ''}${err.msg}`).join('\n');
          } else if (typeof responseData.detail === 'object') {
            errorDetailMsg = JSON.stringify(responseData.detail);
          }
        } else if (responseData) {
            // If no .detail, try to stringify the whole responseData if it's an object
            if (typeof responseData === 'object') errorDetailMsg = JSON.stringify(responseData);
            else if (typeof responseData === 'string') errorDetailMsg = responseData; 
        }

        const finalErrorMsg = errorDetailMsg;
        dispatch(saveInterestsFailure(finalErrorMsg))
        console.error('Error saving interests to backend (fetch):', responseData, 'Request body was:', updateData);
        if (Taro && typeof Taro.showToast === 'function') {
          Taro.showToast({
            title: finalErrorMsg,
            icon: 'none',
            duration: 2000 // Might need longer duration for detailed errors
          })
        } else {
          alert(finalErrorMsg + ' (Taro.showToast不可用)')
        }
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '网络请求失败，无法保存设置';
      dispatch(saveInterestsFailure(errorMsg))
      // updateData here will be the one from the outer scope, potentially empty if error happened before its assignment
      console.error('Error in handleSave, attempting to show toast. Taro.showToast type:', typeof Taro.showToast, err, 'Request body was:', updateData) 
      if (Taro && typeof Taro.showToast === 'function') {
        Taro.showToast({
          title: errorMsg,
          icon: 'none',
          duration: 2000
        })
      } else {
        console.error('Taro.showToast is not a function in handleSave catch block!', Taro)
        alert(errorMsg + ' (Taro.showToast不可用)')
      }
    }
    console.log('[ Interests Page handleSave ] ==> Function End (should be reached if no hangs before an await)');
  }

  // 检查论文是否已收藏
  const isPaperFavorited = (paperId: string): boolean => {
    return favoritedPapers.some(paper => paper.id === paperId)
  }

  // UI for loading and error states during initial profile fetch
  if (profileLoading) {
    return (
      <View className='interests-page-loading'>
        <Text>正在加载您的配置信息...</Text>
      </View>
    );
  }

  if (profileError) {
    return (
      <View className='interests-page-error'>
        <Text>加载配置失败: {profileError}</Text>
        {/* Optional: Add a retry button */}
      </View>
    );
  }

  return (
    <View className='interests-page'>
      <View className='page-header'>
        <Text className='page-title'>{isFromRegistration ? '设置研究兴趣' : '个人中心'}</Text>
      </View>

      {isFromRegistration && (
        <View className='welcome-message'>
          <View className='welcome-card'>
            <AtIcon value='check-circle' size='24' color='#4a89dc' />
            <View className='welcome-text'>
              <Text className='welcome-title'>注册成功!</Text>
              <Text className='welcome-subtitle'>请设置您的研究兴趣，以便我们推荐相关论文</Text>
            </View>
          </View>
        </View>
      )}

      {/* 订阅频率设置部分 */}
      <View className='section-header'>
        <Text className='section-header-title'>订阅设置</Text>
      </View>
      
      <Card className='frequency-card'>
        <View className='section-title'>
          <AtIcon value='calendar' size='18' color='#4A89DC' />
          <Text>选择您希望接收推荐论文的频率</Text>
        </View>
        
        <View className='frequency-picker'>
          <Text className='label'>推送频率</Text>
          <Picker 
            mode='selector' 
            range={frequencyOptions}
            onChange={handleFrequencyChange}
            value={frequency === 'daily' ? 0 : 1}
          >
            <View className='picker-value'>
              <Text>{frequency === 'daily' ? '每日 (Daily)' : '每周 (Weekly)'}</Text>
              <AtIcon value='chevron-right' size='16' color='#999' />
            </View>
          </Picker>
        </View>
        
        <View className='frequency-description'>
          {frequency === 'daily' && (
            <Text user-select className='description-text'>每天将为您精选推送最相关、最新的学术论文，帮助您紧跟研究前沿</Text>
          )}
          {frequency === 'weekly' && (
            <Text user-select className='description-text'>每周将为您整合推送本周最重要、最相关的学术论文，减少信息过载</Text>
          )}
        </View>
        
        <View className='frequency-tips'>
          <View className='tip-item'>
            <AtIcon value='alert-circle' size='14' color='#FFB443' />
            <Text>您可以随时在设置中修改推送频率</Text>
          </View>
        </View>
      </Card>

      {/* 兴趣配置部分 */}
      <View className='section-header'>
        <Text className='section-header-title'>兴趣配置</Text>
      </View>
      
      <Card className='interests-card'>
        <View className='ai-domains-container'>
          <View className='domains-title'>
            <AtIcon value='bookmark' size='16' color='#4A89DC' />
            <Text>{isFromRegistration ? '请选择您感兴趣的AI研究领域（可多选）' : '选择AI领域'}</Text>
          </View>
          {isFromRegistration && (
            <View className='domains-subtitle'>
              <Text>选择您感兴趣的领域将帮助我们为您筛选最相关的论文</Text>
            </View>
          )}
          <View className={`domains-tags ${isFromRegistration ? 'highlight' : ''}`}>
            {aiDomains.map((domain, index) => (
              <View 
                key={domain.name} 
                className={`domain-tag ${domain.active ? 'active' : ''} ${isFromRegistration ? 'larger' : ''}`}
                onClick={() => handleDomainClick(index)}
              >
                <Text>{domain.name}</Text>
              </View>
            ))}
          </View>
        </View>
        
        {/* 添加arXiv论文部分暂时注释掉
        <View className='section-title search-title'>
          <AtIcon value='search' size='16' color='#DC4A4A' />
          <Text>添加arXiv论文</Text>
        </View>

        <View className='search-container'>
          <View className='search-input'>
            <AtIcon value='search' size='16' color='#999' className='search-icon' />
            <Input
              className='description-input'
              type='text'
              placeholder='输入论文的arXiv地址，例如: 2201.12345 或论文标题...'
              value={searchQuery}
              onInput={handleSearchChange}
              onConfirm={handleSearch}
              confirmType='search'
            />
          </View>
          
          {isSearching && (
            <View className='loading-text'>
              <AtIcon value='loading-2' size='18' color='#999' className='loading-icon' />
              <Text user-select>正在搜索中...</Text>
            </View>
          )}
          
          {!isSearching && searchResults.length > 0 && (
            <View className='search-results-container'>
              <View className='results-count'>
                <Text user-select>搜索结果 ({searchResults.length})</Text>
              </View>
              <View className='search-results'>
                {searchResults.map(paper => (
                  <InterestPaperCard
              key={paper.id}
              paper={paper}
                    selected={isPaperFavorited(paper.id)}
                    onSelect={handlePaperSelect}
            />
          ))}
              </View>
            </View>
          )}
          
          {!isSearching && searchQuery && searchResults.length === 0 && (
            <View className='no-results'>
              <AtIcon value='alert-circle' size='18' color='#999' />
              <Text user-select>未找到相关论文</Text>
            </View>
          )}
        </View>
        */}
      </Card>

      {error && (
        <View className='error-message'>
          <AtIcon value='alert-circle' size='16' color='#DC4A4A' />
          <Text>{error}</Text>
        </View>
      )}

      <View className='save-button'>
          <CustomButton
            type='primary'
            size='large'
            block
            onClick={handleSave}
          disabled={loading}
          >
          {loading ? '保存中...' : '保存设置'}
          </CustomButton>
        </View>
    </View>
  )
}

export default Interests 