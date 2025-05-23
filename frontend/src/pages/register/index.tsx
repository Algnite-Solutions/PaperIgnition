import { View, Text, Radio, Input, Button, Image } from '@tarojs/components'
import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import Form, { FormItem } from '../../components/ui/Form'
import CustomButton from '../../components/ui/Button'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { setFrequency, registerStart, registerSuccess, registerFailure } from '../../store/slices/userSlice'
import './index.scss'

const Register = () => {
  const dispatch = useAppDispatch()
  const { frequency, loading, error } = useAppSelector(state => state.user)
  const [validationError, setValidationError] = useState('')
  const [wxUserInfo, setWxUserInfo] = useState<any>(null)
  const [registrationType, setRegistrationType] = useState<'manual' | 'wechat'>('wechat')

  // 检查是否已经有缓存的微信用户信息
  useEffect(() => {
    const cachedUserInfo = Taro.getStorageSync('wxUserInfo')
    if (cachedUserInfo) {
      setWxUserInfo(cachedUserInfo)
    }
  }, [])

  const handleFrequencyChange = (e: any) => {
    dispatch(setFrequency(e.detail.value))
  }

  const validateForm = () => {
    if (!wxUserInfo) {
      setValidationError('请先授权微信信息')
      return false
    }
    setValidationError('')
    return true
  }

  // 获取微信用户信息
  const getUserProfile = () => {
    Taro.getUserProfile({
      desc: '用于完善用户资料',
      success: (res) => {
        // 将用户信息存储到本地缓存
        Taro.setStorageSync('wxUserInfo', res.userInfo)
        setWxUserInfo(res.userInfo)
      },
      fail: (err) => {
        console.error('获取用户信息失败', err)
        Taro.showToast({
          title: '获取用户信息失败',
          icon: 'none'
        })
      }
    })
  }

  // 获取用户手机号码 (Keep this as it might be needed later)
  const getPhoneNumber = (e: any) => {
    if (e.detail.errMsg.indexOf('ok') > -1) {
      // In a real environment, you need to send e.detail.code to the backend to exchange for the phone number
      console.log('Successfully obtained phone number, code:', e.detail.code)
      Taro.showToast({
        title: '手机号授权成功',
        icon: 'success'
      })
    } else {
      Taro.showToast({
        title: '手机号授权失败',
        icon: 'none'
      })
    }
  }

  const handleRegister = async () => {
    if (!validateForm()) {
      return
    }

    try {
      dispatch(registerStart())
      
      // Call Taro.login() to get the login code
      const loginRes = await Taro.login();
      const code = loginRes.code;

      if (!code) {
        throw new Error('Failed to get WeChat login code.');
      }

      // Prepare registration data
      const registerData = {
        code: code, // Use the obtained code
        // You might want to send userInfo and frequency here as well, depending on backend API
        // userInfo: wxUserInfo,
        // frequency: frequency
      };

      // Call backend WeChat login API
      const response = await Taro.request({
        url: 'http://127.0.0.1:8000/api/auth/wechat_login', // Use the new endpoint
        method: 'POST',
        data: registerData,
        header: {
          'content-type': 'application/json'
        }
      });

      console.log('微信登录响应:', response);

      if (response.statusCode === 200) {
        // Save token
        Taro.setStorageSync('token', response.data.access_token);
        
        dispatch(registerSuccess());
        Taro.showToast({
          title: '登录成功',
          icon: 'success',
          duration: 1500,
          mask: true,
          success: () => {
            setTimeout(() => {
              if (response.data.needs_profile_completion) {
                // Redirect to profile completion page
                Taro.redirectTo({
                  url: '/pages/profile/index' // Assuming profile completion page is here
                });
              } else {
                // Redirect to main page (e.g., paper list or index)
                Taro.switchTab({
                  url: '/pages/index/index' // Assuming index is the main page
                });
              }
            }, 1600);
          }
        });
      } else {
        throw new Error(response.data.detail || '微信登录失败'); // Changed error message
      }
    } catch (err) {
      dispatch(registerFailure(err instanceof Error ? err.message : '微信登录失败')); // Changed error message
      Taro.showToast({
        title: err instanceof Error ? err.message : '微信登录失败', // Changed error message
        icon: 'error',
        duration: 2000
      });
    }
  }

  return (
    <View className='register-container'>
      <View className='header'>
        <Text className='title'>欢迎使用</Text>
        <Text className='subtitle'>智能论文推荐助手</Text>
      </View>

      <View className='wechat-registration-section'>
        <Text className='section-title'>微信授权登录</Text>
        {!wxUserInfo ? (
          <CustomButton onClick={getUserProfile}>授权微信信息</CustomButton>
        ) : (
          <View>
            <Text>已授权微信信息: {wxUserInfo.nickName}</Text>
            <Form>
              <FormItem label='接收频率'>
                <View>
                  <Radio checked={frequency === 'daily'} value='daily' onClick={handleFrequencyChange}>每日</Radio>
                  <Radio checked={frequency === 'weekly'} value='weekly' onClick={handleFrequencyChange}>每周</Radio>
                </View>
              </FormItem>
            </Form>

            <CustomButton onClick={handleRegister} loading={loading}>
              {loading ? '登录中...' : '微信登录'}
            </CustomButton>
          </View>
        )}
        {validationError && <Text className='error-message'>{validationError}</Text>}
        {error && <Text className='error-message'>{error}</Text>}
      </View>
    </View>
  )
}

export default Register 