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
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailError, setEmailError] = useState('');

  const handleFrequencyChange = (e: any) => {
    dispatch(setFrequency(e.detail.value))
  }

  const handleWechatLogin = async () => {
    dispatch(registerStart());
    try {
      const loginRes = await Taro.login();
      const code = loginRes.code;
      if (!code) throw new Error('Failed to get WeChat login code.');

      const response = await fetch('http://127.0.0.1:8000/api/auth/wechat_login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });

      const data = await response.json();

      if (response.ok && data.access_token) {
        localStorage.setItem('token', data.access_token);
        dispatch(registerSuccess());
        alert('登录成功');
        
        if (data.needs_profile_completion) {
          if (process.env.TARO_ENV === 'h5') {
            window.location.hash = '#/pages/interests/index';
              } else {
            Taro.navigateTo({ url: '/pages/interests/index' });
          }
        } else {
          if (process.env.TARO_ENV === 'h5') {
            window.location.hash = '#/pages/profile/index';
          } else {
            Taro.switchTab({ url: '/pages/profile/index' });
              }
        }
      } else {
        throw new Error(data.detail || '微信登录失败');
      }
    } catch (err) {
      dispatch(registerFailure(err instanceof Error ? err.message : '微信登录失败'));
      alert(err instanceof Error ? err.message : '微信登录失败');
    }
  };

  const handleEmailRegister = async () => {
    setEmailError('');
    if (!email || !password) {
      setEmailError('邮箱和密码不能为空');
      return;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
        setEmailError('请输入有效的邮箱地址');
        return;
    }
    dispatch(registerStart());
    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/register-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        alert('邮箱注册成功! 请使用邮箱登录');
        setEmail('');
        setPassword('');
        dispatch(registerSuccess());
        
        if (process.env.TARO_ENV === 'h5') {
          window.location.hash = '#/pages/login/index';
        } else {
          Taro.navigateTo({ url: '/pages/login/index' });
        }
      } else {
        const errorDetail = data?.detail || '邮箱注册失败';
        setEmailError(errorDetail);
        dispatch(registerFailure(errorDetail));
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '网络请求错误，注册失败';
      setEmailError(errorMsg);
      dispatch(registerFailure(errorMsg));
    }
  };
  
  const goToLogin = () => {
    if (process.env.TARO_ENV === 'h5') {
      window.location.hash = '#/pages/login/index';
    } else {
      Taro.navigateTo({ url: '/pages/login/index' });
    }
  };

  return (
    <View className='register-container'>
      <View className='header'>
        <Text className='title'>AIgnite</Text>
        <Text className='subtitle'>智能论文推荐助手</Text>
      </View>

      <View className='content'>
        <Text className='description'>基于您的兴趣和阅读习惯，为您推荐最相关的学术论文</Text>
      </View>

      {/* <View className='registration-section email-section'> */}
        <Form className='email-form'>
          <FormItem label='邮箱'>
            <Input
              type='text'
              placeholder='请输入邮箱地址'
              value={email}
              onInput={(e) => setEmail(e.detail.value)}
              className='input-field'
              placeholderClass='register-input-placeholder'
              style={{ backgroundColor: 'transparent' }}
            />
          </FormItem>
          <FormItem label='密码'>
            <Input
              password={true}
              placeholder='请输入密码'
              value={password}
              onInput={(e) => setPassword(e.detail.value)}
              className='input-field'
              placeholderClass='register-input-placeholder'
              style={{ backgroundColor: 'transparent' }}
            />
          </FormItem>
          {emailError && <Text className='error-message'>{emailError}</Text>}
          <View className='button-group'>
            <CustomButton onClick={handleEmailRegister} loading={loading} type='default' className='email-button'>注册邮箱</CustomButton>
            <CustomButton onClick={handleWechatLogin} loading={loading} type='primary' className='email-button'>微信授权登录</CustomButton>
          </View>
          <View className='login-link'>
            <Text>已有账号？</Text>
            <Text className='link' onClick={goToLogin}>立即登录</Text>
          </View>
        </Form>
      {/* </View> */}
      
      {error && <Text className='error-message global-error'>{error}</Text>}
    </View>
  )
}

export default Register 