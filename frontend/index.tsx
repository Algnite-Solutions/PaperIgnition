import Taro from '@tarojs/taro';

const handleSave = async () => {
  console.log('handleSave function in index.tsx called');
  try {
    // ... 这里可能是您原有的保存逻辑，例如API调用 ...
    // 示例: await someApiCall();

    // 关键修复：确保 Taro.showToast 被正确调用
    if (Taro && typeof Taro.showToast === 'function') {
      Taro.showToast({
        title: '保存成功',
        icon: 'success',
        duration: 1500
      });
    } else {
      console.error('Taro.showToast is not available in this context. Taro object:', Taro);
      // 可以提供一个备选的浏览器原生提示，例如 alert
      alert('保存成功 (Taro.showToast不可用)');
    }

    // 导航逻辑 (如果需要)
    setTimeout(() => {
      const profilePath = '/pages/profile/index';
      console.log(`H5导航目标: ${profilePath}`);
      if (Taro && typeof Taro.redirectTo === 'function') {
        Taro.redirectTo({
          url: profilePath,
          fail: (err) => {
            console.error(`H5: redirectTo ${profilePath} 失败:`, err);
            if (Taro.getEnv() === Taro.ENV_TYPE.WEB) {
              window.location.href = profilePath; // 最后的备选方案
            }
          }
        });
      } else {
        console.error('Taro.redirectTo is not available. Navigating with window.location.');
        if (Taro.getEnv() === Taro.ENV_TYPE.WEB) {
            const basePath = process.env.PUBLIC_URL || '';
            const navigateUrl = `${basePath}${profilePath.startsWith('/') ? profilePath : '/' + profilePath}`;
            window.location.href = navigateUrl;
        }
      }
    }, 1500);

  } catch (error) {
    console.error('保存操作失败 (in index.tsx):', error);
    if (Taro && typeof Taro.showToast === 'function') {
      Taro.showToast({
        title: '保存失败，请重试',
        icon: 'none',
        duration: 2000
      });
    } else {
      console.error('Taro.showToast is not available for error message. Taro object:', Taro);
      alert('保存失败，请重试 (Taro.showToast不可用)');
    }
  }
}; 