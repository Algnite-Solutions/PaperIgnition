import { View, Text, Input, Radio, Button, CheckboxGroup, Checkbox } from '@tarojs/components'
import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import Form, { FormItem } from '../../components/ui/Form'
import CustomButton from '../../components/ui/Button'
import { fetchResearchDomains, fetchUserProfile, updateUserProfile } from '../../services/userService' // Import service functions

const ProfileSetup = () => {
  const [email, setEmail] = useState('')
  const [pushFrequency, setPushFrequency] = useState('daily') // Default to daily
  const [interestsDescription, setInterestsDescription] = useState('')
  const [selectedDomainIds, setSelectedDomainIds] = useState<number[]>([])
  const [researchDomains, setResearchDomains] = useState<any[]>([]) // State to hold available research domains
  const [loading, setLoading] = useState(true) // Set loading to true initially
  const [error, setError] = useState('')

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Call backend API to fetch available research domains
        const domains = await fetchResearchDomains(); // Call service function
        setResearchDomains(domains);

        // Call backend API to fetch current user profile
        const userProfile = await fetchUserProfile(); // Call service function
        setEmail(userProfile.email || '');
        setPushFrequency(userProfile.push_frequency || 'daily');
        setInterestsDescription(userProfile.interests_description || '');
        setSelectedDomainIds(userProfile.research_domain_ids || []);

      } catch (err) {
        console.error('Error fetching data:', err);
        setError('加载数据失败');
        Taro.showToast({
          title: '加载数据失败',
          icon: 'error',
          duration: 2000
        });
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []); // Empty dependency array means this effect runs once on mount

  const handleEmailChange = (e: any) => {
    setEmail(e.detail.value)
  }

  const handleFrequencyChange = (e: any) => {
    setPushFrequency(e.detail.value)
  }

  const handleInterestsDescriptionChange = (e: any) => {
    setInterestsDescription(e.detail.value)
  }

  const handleDomainSelect = (e: any) => {
    const selectedIds = e.detail.value.map(Number);
    setSelectedDomainIds(selectedIds);
  }

  const handleSubmit = async () => {
    // --- Form Validation ---
    setError(''); // Clear previous errors
    
    if (!email) {
        setError('邮箱不能为空');
        return;
    }
    
    // Basic email format validation
    const emailRegex = /^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$/i;
    if (!emailRegex.test(email)) {
        setError('请输入有效的邮箱格式');
        return;
    }
    // --- End Form Validation ---

    setLoading(true);

    try {
      // Call backend API to save profile data
      await updateUserProfile({
        email: email,
        push_frequency: pushFrequency,
        interests_description: interestsDescription,
        research_domain_ids: selectedDomainIds
      });

      Taro.showToast({
          title: '个人信息设置成功',
          icon: 'success',
          duration: 1500,
          mask: true,
          success: () => {
              // Navigate to the main page after successful submission
              Taro.switchTab({
                  url: '/pages/index/index' // Navigate to main page
              });
          }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
      Taro.showToast({
        title: err instanceof Error ? err.message : '保存失败',
        icon: 'error',
        duration: 2000
      });
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <View className='loading'>加载中...</View>; // Basic loading indicator
  }

  return (
    <View className='profile-setup-container'>
      <View className='header'>
        <Text className='title'>完善个人信息</Text>
        <Text className='subtitle'>请填写您的个人偏好</Text>
      </View>

      <Form>
        <FormItem label='邮箱'>
          <Input
            type='text'
            placeholder='请输入邮箱'
            value={email}
            onInput={handleEmailChange}
            className='input'
          />
        </FormItem>

        <FormItem label='接收频率'>
          <View>
            <Radio checked={pushFrequency === 'daily'} value='daily' onClick={handleFrequencyChange}>每日</Radio>
            <Radio checked={pushFrequency === 'weekly'} value='weekly' onClick={handleFrequencyChange}>每周</Radio>
          </View>
        </FormItem>

        <FormItem label='研究兴趣描述 (可选)'>
          <Input
            type='text'
            placeholder='例如：深度学习，自然语言处理'
            value={interestsDescription}
            onInput={handleInterestsDescriptionChange}
            className='input'
          />
        </FormItem>

        <FormItem label='研究领域'>
            <CheckboxGroup onChange={handleDomainSelect}>
                {researchDomains.map(domain => (
                    <View key={domain.id}>
                        <Checkbox value={String(domain.id)} checked={selectedDomainIds.includes(domain.id)}>{domain.name}</Checkbox>
                    </View>
                ))}
            </CheckboxGroup>
        </FormItem>

        {error && <Text className='error-message'>{error}</Text>}

        <CustomButton onClick={handleSubmit} loading={loading}>
          {loading ? '保存中...' : '保存'}
        </CustomButton>
      </Form>
    </View>
  )
}

export default ProfileSetup 