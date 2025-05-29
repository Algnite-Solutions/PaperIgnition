import { View, Text, Input } from '@tarojs/components'
import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import Form, { FormItem } from '../../components/ui/Form'
import CustomButton from '../../components/ui/Button'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { loginStart, loginSuccess, loginFailure } from '../../store/slices/userSlice'
import './index.scss'

const Login = () => {
  const dispatch = useAppDispatch()
  const { loading, error } = useAppSelector(state => state.user)
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState('');

  // 通用显示消息的函数，兼容不同环境
  const showMessage = (message, type: 'none' | 'success' | 'error' | 'loading' = 'none') => {
    try {
      // 尝试使用Taro的API
      Taro.showToast({
        title: message,
        icon: type,
        duration: 2000
      });
    } catch (e) {
      // 降级到alert
      alert(message);
    }
  };

  const handleEmailLogin = async () => {
    setLoginError('');
    if (!email || !password) {
      setLoginError('邮箱和密码不能为空');
      return;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
      setLoginError('请输入有效的邮箱地址');
      return;
    }
    
    dispatch(loginStart());
    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/login-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        // 保存token
        localStorage.setItem('token', data.access_token);
        
        // 保存用户邮箱到本地存储
        localStorage.setItem('userEmail', email);
        
        dispatch(loginSuccess());
        
        // 根据用户是否设置了研究兴趣决定跳转路径
        if (data.needs_interest_setup) {
          // 如果用户未设置研究兴趣，跳转到兴趣配置页面
          showMessage('请先设置您的订阅频率和研究兴趣');
          
          if (process.env.TARO_ENV === 'h5') {
            window.location.hash = '#/pages/interests/index';
          } else {
            Taro.navigateTo({ url: '/pages/interests/index' });
          }
        } else {
          // 如果已设置研究兴趣，跳转到首页
          showMessage('登录成功!', 'success');
          
          if (process.env.TARO_ENV === 'h5') {
            window.location.hash = '#/pages/index/index';
          } else {
            Taro.switchTab({ url: '/pages/index/index' });
          }
        }
      } else {
        const errorDetail = data?.detail || '登录失败';
        setLoginError(errorDetail);
        dispatch(loginFailure(errorDetail));
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '网络请求错误，登录失败';
      setLoginError(errorMsg);
      dispatch(loginFailure(errorMsg));
    }
  };

  const handleWechatLogin = async () => {
    dispatch(loginStart());
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
        
        // 保存微信用户信息到本地存储
        if (data.user_info && data.user_info.email) {
          localStorage.setItem('userEmail', data.user_info.email);
        } else {
          localStorage.setItem('userEmail', '微信用户');
        }
        
        dispatch(loginSuccess());
        
        // 根据用户是否设置了研究兴趣决定跳转路径
        if (data.needs_interest_setup) {
          // 如果用户未设置研究兴趣，跳转到兴趣配置页面
          showMessage('请先设置您的订阅频率和研究兴趣');
          
          if (process.env.TARO_ENV === 'h5') {
            window.location.hash = '#/pages/interests/index';
          } else {
            Taro.navigateTo({ url: '/pages/interests/index' });
          }
        } else {
          // 如果已设置研究兴趣，跳转到首页
          showMessage('登录成功!', 'success');
          
          if (process.env.TARO_ENV === 'h5') {
            window.location.hash = '#/pages/index/index';
          } else {
            Taro.switchTab({ url: '/pages/index/index' });
          }
        }
      } else {
        throw new Error(data.detail || '微信登录失败');
      }
    } catch (err) {
      dispatch(loginFailure(err instanceof Error ? err.message : '微信登录失败'));
      showMessage(err instanceof Error ? err.message : '微信登录失败', 'error');
    }
  };

  // 跳转到注册页面
  const goToRegister = () => {
    if (process.env.TARO_ENV === 'h5') {
      window.location.hash = '#/pages/register/index';
    } else {
      Taro.navigateTo({ url: '/pages/register/index' });
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

      <View className='registration-section email-section'>
        <Form className='email-form'>
          <FormItem label='邮箱'>
            <Input
              type='text'
              placeholder='请输入邮箱地址'
              value={email}
              onInput={(e) => setEmail(e.detail.value)}
              className='input-field'
              placeholderClass='register-input-placeholder'
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
            />
          </FormItem>
          {loginError && <Text className='error-message'>{loginError}</Text>}
          <View className='button-group'>
            <CustomButton onClick={handleEmailLogin} loading={loading} type='primary' className='email-button'>邮箱登录</CustomButton>
            <CustomButton onClick={handleWechatLogin} loading={loading} type='default' className='email-button'>微信授权登录</CustomButton>
          </View>
          <View className='register-link'>
            <Text>还没有账号？</Text>
            <Text className='link' onClick={goToRegister}>立即注册</Text>
          </View>
        </Form>
      </View>
      
      {error && <Text className='error-message global-error'>{error}</Text>}
    </View>
  )
}

export default Login 