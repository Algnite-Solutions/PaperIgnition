import Taro from '@tarojs/taro'
// import { useRouter } from '@tarojs/taro' // useRouter might not be needed if navigation is simple

const handleSaveSettings = () => {
  console.log('H5环境: 保存按钮被点击');
  
  try {
    // 1. API call for saving user interests -  Currently Commented Out
    /* 
    const response = await api.updateUserInterests({
      research_domain_ids: selectedDomains, // Ensure selectedDomains is defined in your component
      interests_description: interestKeywords // Ensure interestKeywords is defined in your component
    });
    console.log('API调用结果:', response);
    */
    
    // 2. Vibration - Completely Removed for H5 as it's not supported
    // console.log('振动逻辑已为H5环境跳过');
    
    // 3. Show Success Toast
    Taro.showToast({
      title: '设置已保存',
      icon: 'success',
      duration: 1500
    });
    
    console.log('准备导航到个人主页 - H5环境');
    
    // 4. Navigate to Profile Page (H5 environment)
    setTimeout(() => {
      const profilePath = '/pages/profile/index'; // Define path clearly
      console.log(`H5导航目标: ${profilePath}`);
      try {
        Taro.redirectTo({
          url: profilePath,
          success: () => {
            console.log(`H5: redirectTo ${profilePath} 成功`);
          },
          fail: (err) => {
            console.error(`H5: redirectTo ${profilePath} 失败:`, err);
            // Fallback to navigateTo
            Taro.navigateTo({
              url: profilePath,
              success: () => {
                console.log(`H5: navigateTo ${profilePath} 成功`);
              },
              fail: (err2) => {
                console.error(`H5: navigateTo ${profilePath} 失败:`, err2);
                // Final fallback: browser navigation for H5
                if (Taro.getEnv() === Taro.ENV_TYPE.WEB) {
                  console.log('H5: 尝试使用 window.location.href');
                  const basePath = process.env.PUBLIC_URL || '';
                  // 确保路径拼接正确
                  const navigateUrl = `${basePath}${profilePath.startsWith('/') ? profilePath : '/' + profilePath}`;
                  window.location.href = navigateUrl;
                }
              }
            });
          }
        });
      } catch (navError) {
        console.error('H5: 导航调度错误:', navError);
        // 导航尝试的最终捕获
        if (Taro.getEnv() === Taro.ENV_TYPE.WEB) {
            console.log('H5: 导航调度错误后，尝试 window.location.href');
            const profilePath = '/pages/profile/index';
            const basePath = process.env.PUBLIC_URL || '';
            const navigateUrl = `${basePath}${profilePath.startsWith('/') ? profilePath : '/' + profilePath}`;
            window.location.href = navigateUrl;
        }
      }
    }, 1500); // Delay to allow toast to be seen
    
  } catch (error) {
    console.error('H5: 操作失败', error);
    Taro.showToast({
      title: '操作失败，请重试',
      icon: 'none',
      duration: 2000
    });
  }
};

// Ensure the function is exported if it's in a separate module
export { handleSaveSettings }; 