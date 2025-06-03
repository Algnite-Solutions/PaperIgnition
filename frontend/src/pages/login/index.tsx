import { View, Text, Input } from '@tarojs/components'
import { useState, useEffect } from 'react'
import Taro from '@tarojs/taro'
import Form, { FormItem } from '../../components/ui/Form'
import CustomButton from '../../components/ui/Button'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { loginStart, loginSuccess, loginFailure } from '../../store/slices/userSlice'
import { API_BASE_URL } from '../../config/api'
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
    
    console.log('[Login Page] handleEmailLogin: dispatching loginStart');
    dispatch(loginStart());
    try {
      const response = await fetch(`http://localhost:8000/api/auth/login-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      const data = await response.json();
      console.log('[Login Page] handleEmailLogin: API response data:', data);
      if (response.ok) {
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('userEmail', email);
        
        console.log('[Login Page] handleEmailLogin: dispatching loginSuccess');
        dispatch(loginSuccess());
        console.log('[Login Page] handleEmailLogin: loginSuccess dispatched. Current loading state should be false.');
        
        if (data.needs_interest_setup) {
          showMessage('请先设置您的订阅频率和研究兴趣');
          console.log('[Login Page] handleEmailLogin: Navigating to interests page soon...');
          setTimeout(() => {
            Taro.redirectTo({ url: '/pages/interests/index' });
          }, 200); // Small delay
        } else {
          showMessage('登录成功!', 'success');
          console.log('[Login Page] handleEmailLogin: Navigating to recommendations page soon...');
          setTimeout(() => {
            Taro.redirectTo({ url: '/pages/recommendations/index' });
          }, 200); // Small delay
        }
      } else {
        const errorDetail = data?.detail || '登录失败';
        setLoginError(errorDetail);
        console.log('[Login Page] handleEmailLogin: dispatching loginFailure with error:', errorDetail);
        dispatch(loginFailure(errorDetail));
        console.log('[Login Page] handleEmailLogin: loginFailure dispatched. Current loading state should be false.');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '网络请求错误，登录失败';
      setLoginError(errorMsg);
      console.log('[Login Page] handleEmailLogin: CATCH block - dispatching loginFailure with error:', errorMsg);
      dispatch(loginFailure(errorMsg));
      console.log('[Login Page] handleEmailLogin: CATCH block - loginFailure dispatched. Current loading state should be false.');
    }
  };

  const handleWechatLogin = async () => {
    console.log('[Login Page] handleWechatLogin: dispatching loginStart');
    dispatch(loginStart());
    try {
      const loginRes = await Taro.login();
      const code = loginRes.code;
      if (!code) throw new Error('Failed to get WeChat login code.');

      const response = await fetch(`${API_BASE_URL}/auth/wechat_login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code })
      });

      const data = await response.json();
      console.log('[Login Page] handleWechatLogin: API response data:', data);
      
      if (response.ok && data.access_token) {
        localStorage.setItem('token', data.access_token);
        if (data.user_info && data.user_info.email) {
          localStorage.setItem('userEmail', data.user_info.email);
        } else {
          localStorage.setItem('userEmail', '微信用户');
        }
        
        console.log('[Login Page] handleWechatLogin: dispatching loginSuccess');
        dispatch(loginSuccess());
        console.log('[Login Page] handleWechatLogin: loginSuccess dispatched. Current loading state should be false.');
        
        if (data.needs_interest_setup) {
          showMessage('请先设置您的订阅频率和研究兴趣');
          console.log('[Login Page] handleWechatLogin: Navigating to interests page soon...');
          setTimeout(() => {
            Taro.redirectTo({ url: '/pages/interests/index' });
          }, 200); // Small delay
        } else {
          showMessage('登录成功!', 'success');
          console.log('[Login Page] handleWechatLogin: Navigating to recommendations page soon...');
          setTimeout(() => {
            Taro.redirectTo({ url: '/pages/recommendations/index' });
          }, 200); // Small delay
        }
      } else {
        const errorDetail = data.detail || '微信登录失败';
        console.error('[Login Page] handleWechatLogin: Error condition met. Error:', errorDetail);
        dispatch(loginFailure(errorDetail));
        console.log('[Login Page] handleWechatLogin: loginFailure dispatched. Current loading state should be false.');
        showMessage(errorDetail, 'error');
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '微信登录失败';
      console.error('[Login Page] handleWechatLogin: CATCH block - dispatching loginFailure with error:', errorMsg);
      dispatch(loginFailure(errorMsg));
      console.log('[Login Page] handleWechatLogin: CATCH block - loginFailure dispatched. Current loading state should be false.');
      showMessage(errorMsg, 'error');
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
      {/* </View> */}
      
      {error && <Text className='error-message global-error'>{error}</Text>}
    </View>
  )
}

export default Login 