import { View, Text, Input, CheckboxGroup, Checkbox } from '@tarojs/components'
import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { AtIcon } from 'taro-ui'
import { setInterestDescription, saveInterestsWithDescription } from '../../store/slices/userSlice'
import CustomButton from '../../components/ui/Button'
import { API_BASE_URL } from '../../config/api'
import './index.scss'

// UserProfile interface based on what GET /api/users/me likely returns 
interface UserProfile {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  interests_description: string[]; // This is a list of strings
  research_domain_ids: number[]; // This is a list of domain IDs (still fetched, but not used for editing on this page)
  push_frequency?: string; 
}

const ResearchInterestsPage = () => {
  const dispatch = useAppDispatch();
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditMode, setIsEditMode] = useState(false);
  const [description, setDescription] = useState(''); 
  const [selectedKeywords, setSelectedKeywords] = useState<string[]>([]); 
  
  const [popularKeywords] = useState([
    'AI', '机器学习', '深度学习', '自然语言处理', '计算机视觉',
    '区块链', '物联网', '云计算', '大数据', '神经网络',
    '量子计算', '人机交互', '生物信息学', '知识图谱', '强化学习',
    '图神经网络', '推荐系统', '语音识别', '多模态学习', '联邦学习'
  ]);

  useEffect(() => {
    const loadInitialData = async () => {
      setLoading(true);
      try {
        // Fetch current user's profile (which includes interests)
        const token = localStorage.getItem('token');
        if (!token) {
          Taro.showToast({ title: '请先登录', icon: 'none' });
          setLoading(false);
          return;
        }

        const userProfileResponse = await fetch(`${API_BASE_URL}/users/me`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });

        if (!userProfileResponse.ok) {
          throw new Error('获取用户配置失败');
        }
        
        const userProfile: UserProfile = await userProfileResponse.json();
        console.log('User Profile for research interests page:', userProfile);

        const userInterestsDesc = (userProfile.interests_description || []).join(', ');
        setDescription(userInterestsDesc);
        
        if (userInterestsDesc) {
          const keywordsArray = userInterestsDesc
            .split(',')
            .map(keyword => keyword.trim())
            .filter(keyword => keyword.length > 0);
          setSelectedKeywords(keywordsArray);
        }
        
        dispatch(setInterestDescription(userInterestsDesc));

      } catch (error) {
        console.error('加载研究兴趣页面数据失败:', error);
        Taro.showToast({
          title: error instanceof Error ? error.message : '加载数据失败',
          icon: 'none',
          duration: 2000
        });
      } finally {
        setLoading(false);
      }
    };
    
    loadInitialData();
  }, [dispatch]);

  const toggleEditMode = () => {
    setIsEditMode(!isEditMode);
  };

  const handleKeywordToggle = (keyword: string) => {
    let newKeywords;
    if (selectedKeywords.includes(keyword)) {
      newKeywords = selectedKeywords.filter(k => k !== keyword);
    } else {
      newKeywords = [...selectedKeywords, keyword];
    }
    setSelectedKeywords(newKeywords);
    setDescription(newKeywords.join(', ')); 
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const newDescription = selectedKeywords.join(', '); 
      
      const token = localStorage.getItem('token');
      if (!token) throw new Error('未登录');

      const interestsListForBackend = newDescription
          .split(',')
          .map(item => item.trim())
          .filter(item => item.length > 0);

      // Only sending interests_description, as domain selection is removed from this page's UI
      const profileUpdateData = {
        interests_description: interestsListForBackend,
      };

      const response = await fetch(`${API_BASE_URL}/users/me/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profileUpdateData)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({detail: '保存失败'}));
        throw new Error(errorData.detail || '保存用户配置失败');
      }
      
      dispatch(saveInterestsWithDescription(newDescription));
      
      Taro.showToast({
        title: '保存成功',
        icon: 'success',
        duration: 2000
      });
      setIsEditMode(false);
    } catch (error) {
      console.error('保存失败:', error);
      Taro.showToast({
        title: error instanceof Error ? error.message : '保存失败',
        icon: 'none',
        duration: 2000
      });
    } finally {
      setSaving(false);
    }
  };

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
            
            {/* <View className='section'>
              <Text className='section-title'>热门研究领域</Text>
              <View className='keywords-container'>
                {popularKeywords.slice(0, 10).map((keyword, index) => (
                  <View key={index} className='keyword-tag'>
                    {keyword}
                  </View>
                ))}
              </View>
            </View> */}
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
              {/* <CustomButton
                type='default'
                onClick={toggleEditMode}
                className='cancel-button'
              >
                取消
              </CustomButton> */}
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