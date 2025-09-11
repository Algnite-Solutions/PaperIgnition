import { View, RichText, Text } from '@tarojs/components'
import React, { useEffect, useState } from 'react'
import { useAppDispatch, useAppSelector } from '../../store/hooks'
import { clearCurrentPaper } from '../../store/slices/paperSlice'
import Taro from '@tarojs/taro'
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { API_BASE_URL } from '../../config/api'
import CustomButton from '../../components/ui/Button'
import './index.scss'

// 配置marked以支持数学公式和表格
marked.setOptions({
  breaks: true,
  gfm: true
})

// 创建数学公式扩展
const mathExtension = {
  name: 'math',
  level: 'inline' as const,
  start(src: string) {
    return src.indexOf('$')
  },
  tokenizer(src: string) {
    const inlineRule = /^\$([^\$]+)\$/
    const blockRule = /^\$\$([^\$]+)\$\$/

    const inlineMatch = inlineRule.exec(src)
    if (inlineMatch) {
      return {
        type: 'math',
        raw: inlineMatch[0],
        text: inlineMatch[1],
        display: false
      }
    }

    const blockMatch = blockRule.exec(src)
    if (blockMatch) {
      return {
        type: 'math',
        raw: blockMatch[0],
        text: blockMatch[1],
        display: true
      }
    }
  },
  renderer(token: { text: string; display: boolean }) {
    try {
      return katex.renderToString(token.text, { displayMode: token.display })
    } catch (e) {
      console.error('KaTeX error:', e)
      return token.text
    }
  }
}

// 使用扩展
marked.use({ extensions: [mathExtension] })

// 修复图片链接的函数
const fixImageLinks = (html: string): string => {
  // 处理多种图片链接路径
  let processedHtml = html
    // 将绝对路径的图片链接替换为占位图
    .replace(/src="(\/Users\/[^"]+)"/g, 'src="https://via.placeholder.com/600x300?text=Figure+Image"')
    // 将相对路径替换为可访问的网络图片（在微信小程序中，只有网络图片或本地资源文件可用）
    .replace(/src="(\.\.\/[^"]+)"/g, 'src="https://via.placeholder.com/600x300?text=Figure"')
    // 特别处理 frontend/assets 路径的图片
    .replace(/src="(\.\.\\frontend\\assets\\figure[0-9]+\.png)"/g, (match, path) => {
      // 提取图片文件名（例如figure1.png）
      const filename = path.split('\\').pop();
      return `src="https://via.placeholder.com/600x300?text=${filename}"`;
    });

  // 保留原始的 Pixabay 图片链接，不进行替换
  // 但添加大小限制和居中样式
  processedHtml = processedHtml.replace(/src="(https:\/\/cdn\.pixabay\.com\/photo\/[^"]+)"/g, 
    'src="$1" style="width:100%; display:block; margin-left:auto; margin-right:auto;"');

  // 为所有图片标签添加宽度和样式属性，直接在HTML中控制图片大小
  processedHtml = processedHtml.replace(/<img([^>]*)(\/?)>/g, (match, attributes, selfClose) => {
    // 检查是否已有style属性
    if (attributes.includes('style="')) {
      // 已有style属性，确保有宽度和居中样式
      if (!attributes.includes('width:100%')) {
        // 删除可能存在的结束引号，添加全宽和居中样式，然后重新添加引号
        const newAttributes = attributes.replace(/style="([^"]*)"/g, 
          'style="$1; width:100%; display:block; margin-left:auto; margin-right:auto;"');
        return `<img${newAttributes}${selfClose}>`;
      }
      return match; // 已有完整的样式，保持不变
    } else if (attributes.includes('width')) {
      // 有width属性但没有style，添加style
      return `<img${attributes} style="width:100%; display:block; margin-left:auto; margin-right:auto;"${selfClose}>`;
    }
    // 没有任何样式，添加完整样式
    return `<img${attributes} style="width:100%; display:block; margin-left:auto; margin-right:auto; margin-top:10px; margin-bottom:10px;"${selfClose}>`;
  });

  return processedHtml;
};

// 简单的HTML清理函数，针对小程序环境
const simpleSanitizeHtml = (html: string): string => {
  // 移除可能有害的脚本和事件处理器
  const sanitized = html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/on\w+="[^"]*"/g, '')
    .replace(/on\w+='[^']*'/g, '');
  
  return sanitized;
};

const PaperDetail = () => {
  const dispatch = useAppDispatch()
  const [parsedHtml, setParsedHtml] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(true)
  const [liked, setLiked] = useState<boolean>(false)
  const [disliked, setDisliked] = useState<boolean>(false)
  const [blogFeedbackLoading, setBlogFeedbackLoading] = useState<boolean>(false)
  const [activeTab, setActiveTab] = useState<string>('overview')
  const [tableOfContents, setTableOfContents] = useState<Array<{id: string, title: string, level: number}>>([])
  const [showTabContent, setShowTabContent] = useState<boolean>(false)
  const [currentTabContent, setCurrentTabContent] = useState<string>('')
  const { isLoggedIn } = useAppSelector(state => state.user)

  const fetchPaperContent = async (paperId: string) => {
    try {
      setLoading(true)
      
      // 检查用户是否已登录
      if (!isLoggedIn) {
        throw new Error('用户未登录，请先登录')
      }
      
      // 获取论文内容
      const response = await fetch(`${API_BASE_URL}/api/papers/paper_content/${paperId}`)
      if (response.ok) {
        const Content = await response.text()
        const markdownContent = Content.replace(/^"|"$/g, '');
        console.log(markdownContent)
        try {
          // 将字符串中的 \n 转换为实际的换行符
          const processedContent = markdownContent.replace(/\\n/g, '\n')
          // 将Markdown转换为HTML
          const htmlContent = marked.parse(processedContent)
          // 修复图片链接并进行简单清理
          const fixedHtml = fixImageLinks(htmlContent as string)
          const sanitizedHtml = simpleSanitizeHtml(fixedHtml)
          setParsedHtml(sanitizedHtml)
          
          // 生成目录
          generateTableOfContents(sanitizedHtml)
          
          // 获取博客反馈状态
          await fetchBlogFeedback(paperId)
        } catch (parseError) {
          console.error('解析Markdown内容失败', parseError)
          Taro.showToast({
            title: '解析内容失败',
            icon: 'none',
            duration: 2000
          })
        }
      } else {
        const errorMessage = 'Failed to fetch paper content'
        Taro.showToast({
          title: errorMessage,
          icon: 'none',
          duration: 2000
        })
      }
    } catch (err) {
      console.error('获取论文内容失败', err)
      Taro.showToast({
        title: '获取论文内容失败',
        icon: 'none',
        duration: 2000
      })
    } finally {
      setLoading(false)
    }
  }

  const handleBack = () => {
    Taro.navigateBack()
  }

  // 获取当前论文的博客反馈状态
  const fetchBlogFeedback = async (paperId: string) => {
    try {
      const token = localStorage.getItem('token')
      if (!token) {
        console.log('Debug: 获取博客反馈状态时，用户未登录')
        return
      }

      const requestUrl = `${API_BASE_URL}/api/papers/blog-feedback/${paperId}`
      console.log('Debug: 获取博客反馈状态', {
        url: requestUrl,
        paperId
      })

      const response = await fetch(requestUrl, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      })

      console.log('Debug: 获取反馈状态响应', {
        status: response.status,
        ok: response.ok
      })

      if (response.ok) {
        const result = await response.json()
        console.log('Debug: 获取到的反馈状态', result)
        console.log('Debug: blog_liked值类型和内容', {
          value: result.blog_liked,
          type: typeof result.blog_liked,
          isTrue: result.blog_liked === true,
          isFalse: result.blog_liked === false,
          isNull: result.blog_liked === null,
          isUndefined: result.blog_liked === undefined
        })
        
        if (result.blog_liked === true) {
          console.log('Debug: 设置为喜欢状态')
          setLiked(true)
          setDisliked(false)
        } else if (result.blog_liked === false) {
          console.log('Debug: 设置为不喜欢状态')
          setLiked(false)
          setDisliked(true)
        } else {
          console.log('Debug: 设置为未评价状态')
          setLiked(false)
          setDisliked(false)
        }
      } else {
        const errorText = await response.text()
        console.log('Debug: 获取反馈状态错误', errorText)
      }
    } catch (error) {
      console.error('获取博客反馈状态失败:', error)
    }
  }

  // 提交博客反馈
  const submitBlogFeedback = async (paperId: string, liked: boolean) => {
    try {
      setBlogFeedbackLoading(true)
      const token = localStorage.getItem('token')
      if (!token) {
        console.log('Debug: 用户未登录，token为空')
        Taro.showToast({
          title: '请先登录',
          icon: 'none'
        })
        return
      }

      const requestUrl = `${API_BASE_URL}/api/papers/blog-feedback`
      const requestBody = {
        paper_id: paperId,
        liked: liked
      }
      
      console.log('Debug: 提交博客反馈', {
        url: requestUrl,
        paperId,
        liked,
        token: token ? '存在' : '不存在'
      })

      const response = await fetch(requestUrl, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      })

      console.log('Debug: 响应状态', {
        status: response.status,
        statusText: response.statusText,
        ok: response.ok,
        headers: Object.fromEntries(response.headers.entries())
      })

      if (response.ok) {
        const result = await response.json()
        console.log('Debug: 成功响应', result)
        Taro.showToast({
          title: liked ? '谢谢您的喜欢！' : '感谢您的反馈！',
          icon: 'success',
          duration: 1500
        })
      } else {
        const errorText = await response.text()
        console.log('Debug: 错误响应', {
          status: response.status,
          statusText: response.statusText,
          errorText: errorText
        })
        throw new Error(`提交反馈失败: ${response.status} ${errorText}`)
      }
    } catch (error) {
      console.error('提交博客反馈失败:', error)
      Taro.showToast({
        title: '提交失败，请重试',
        icon: 'none'
      })
    } finally {
      setBlogFeedbackLoading(false)
    }
  }

  const handleLike = async () => {
    const paperId = Taro.getCurrentInstance().router?.params?.id
    if (!paperId) return

    if (liked) {
      // 如果已经喜欢了，不做任何操作（或者可以选择取消）
      return
    }

    setLiked(true)
    setDisliked(false)
    await submitBlogFeedback(paperId, true)
  }

  const handleDislike = async () => {
    const paperId = Taro.getCurrentInstance().router?.params?.id
    if (!paperId) return

    if (disliked) {
      // 如果已经不喜欢了，不做任何操作（或者可以选择取消）
      return
    }

    setLiked(false)
    setDisliked(true)
    await submitBlogFeedback(paperId, false)
  }

  const handleTabClick = (tab: string) => {
    // 如果点击的是当前激活的标签，则切换显示/隐藏
    if (activeTab === tab) {
      setShowTabContent(!showTabContent)
      return
    }
    
    // 如果点击的是新标签，则显示内容
    setActiveTab(tab)
    setShowTabContent(true)
    
    // 模拟从数据库读取对应字段的内容
    // 这里使用mock数据，实际应该从数据库读取
    let mockContent = ''
    switch (tab) {
      case 'overview':
        mockContent = `# 论文概览

DINOv3是由Meta AI Research开发的自监督视觉基础模型，在多个视觉任务上达到了最先进的性能。

## 核心特点
- **7B参数规模**：拥有70亿参数的Vision Transformer
- **大规模训练**：在17亿张图像上训练
- **创新技术**：采用新颖的Gram anchoring技术
- **高质量特征**：产生异常清晰和语义连贯的密集特征

## 应用领域
- 图像分类和识别
- 目标检测和分割
- 视觉-语言理解
- 多模态学习`
        break
      case 'problem':
        mockContent = `# 问题陈述

## 传统方法的局限性
现有的自监督视觉模型在处理复杂视觉任务时存在以下问题：

### 1. 特征质量不足
- 特征表示不够清晰
- 语义连贯性较差
- 缺乏细粒度的视觉理解

### 2. 训练效率低下
- 需要大量标注数据
- 训练时间长，计算资源消耗大
- 模型泛化能力有限

### 3. 多任务适应性差
- 单一模型难以适应多种视觉任务
- 任务间知识迁移效果不佳
- 缺乏统一的视觉表示学习框架

## 研究目标
开发一个能够：
- 产生高质量视觉特征的自监督模型
- 在多个视觉任务上表现优异
- 具有良好的泛化能力和可扩展性`
        break
      case 'method':
        mockContent = `# 技术方法

## 整体架构
DINOv3采用Vision Transformer (ViT)作为骨干网络，结合创新的训练策略。

### 1. Vision Transformer架构
- **输入处理**：将图像分割成16×16的patch
- **位置编码**：学习patch之间的空间关系
- **多头注意力**：捕获全局和局部的视觉依赖
- **前馈网络**：非线性特征变换

### 2. Gram Anchoring技术
这是DINOv3的核心创新，通过以下方式提升特征质量：

#### 特征对齐
- 使用Gram矩阵捕获特征间的相关性
- 建立跨层和跨尺度的特征对应关系
- 确保特征的一致性和稳定性

#### 多尺度学习
- 在不同分辨率下学习特征表示
- 通过多尺度对比学习增强鲁棒性
- 实现细粒度和粗粒度的视觉理解

### 3. 训练策略
- **自监督学习**：无需人工标注
- **对比学习**：通过正负样本对比学习特征
- **数据增强**：多种图像变换增强泛化能力
- **渐进式训练**：从简单到复杂的训练过程`
        break
      case 'results':
        mockContent = `# 实验结果

## 性能评估

### 1. 图像分类任务
DINOv3在ImageNet-1K上的表现：

| 模型 | Top-1准确率 | Top-5准确率 | 参数量 |
|------|-------------|-------------|---------|
| DINOv3-Small | 83.2% | 96.8% | 22M |
| DINOv3-Base | 85.1% | 97.3% | 86M |
| DINOv3-Large | 86.2% | 97.8% | 300M |
| DINOv3-Giant | 87.1% | 98.1% | 1.1B |

### 2. 目标检测性能
在COCO数据集上的检测结果：

- **mAP@0.5**: 54.2%
- **mAP@0.75**: 47.8%
- **mAP@0.5:0.95**: 42.1%

### 3. 语义分割效果
在ADE20K数据集上的分割性能：

- **mIoU**: 48.7%
- **像素准确率**: 82.3%

## 消融实验
通过对比实验验证了Gram anchoring技术的有效性：
- 移除Gram anchoring后，性能下降15-20%
- 多尺度训练策略贡献了8-12%的性能提升
- 大规模预训练数据带来了5-8%的改进`
        break
      case 'takeaways':
        mockContent = `# 关键要点

## 主要贡献

### 1. 技术创新
- **Gram Anchoring**：首次提出并验证了Gram矩阵在视觉特征学习中的重要作用
- **多尺度特征学习**：实现了跨尺度的特征对齐和知识迁移
- **大规模自监督训练**：证明了数据规模对视觉模型性能的关键影响

### 2. 性能突破
- 在多个视觉任务上达到SOTA性能
- 证明了自监督学习在大规模视觉模型中的有效性
- 为视觉基础模型的发展提供了新的方向

### 3. 实用价值
- 降低了视觉AI应用的开发门槛
- 提供了高质量的预训练特征
- 支持多种下游任务的快速适配

## 未来展望

### 1. 技术发展方向
- 探索更高效的训练策略
- 研究多模态融合的可能性
- 开发更轻量级的模型变体

### 2. 应用前景
- 自动驾驶和机器人视觉
- 医疗图像分析
- 工业质量检测
- 智能安防监控

### 3. 挑战与机遇
- 计算资源需求仍然较高
- 需要更多领域特定的优化
- 在边缘设备上的部署挑战`
        break
      default:
        mockContent = '# 内容加载中...\n\n请稍候...'
    }
    
    setCurrentTabContent(mockContent)
  }

  const scrollToSection = (id: string) => {
    // 在小程序中，我们需要通过其他方式实现滚动
    // 这里先显示一个提示
    Taro.showToast({
      title: `跳转到: ${id}`,
      icon: 'none',
      duration: 1500
    })
  }

  const generateTableOfContents = (html: string) => {
    const tempDiv = document.createElement('div')
    tempDiv.innerHTML = html
    
    const headings = tempDiv.querySelectorAll('h1, h2, h3, h4, h5, h6')
    const toc: Array<{id: string, title: string, level: number}> = []
    
    headings.forEach((heading, index) => {
      const level = parseInt(heading.tagName.charAt(1))
      const title = heading.textContent || `标题 ${index + 1}`
      const id = `heading-${index}`
      
      toc.push({ id, title, level })
      
      // 为标题添加id属性
      heading.id = id
    })
    
    setTableOfContents(toc)
  }



  useEffect(() => {
    const params = Taro.getCurrentInstance().router?.params
    if (params?.id) {
      fetchPaperContent(params.id as string)
      // 获取博客反馈状态
      fetchBlogFeedback(params.id as string)
    }
    return () => {
      dispatch(clearCurrentPaper())
    }
  }, [])

  if (!isLoggedIn) {
    return (
      <View className='paper-detail-not-login'>
        <Text className='login-prompt'>请先登录</Text>
        <CustomButton 
          type='primary' 
          onClick={() => Taro.navigateTo({ url: '/pages/login/index' })}
        >
          去登录
        </CustomButton>
      </View>
    )
  }

  return (
    <View className='paper-detail-page'>
      <View className='header'>
        <Text className='back' onClick={handleBack}>返回</Text>
      </View>
      
      {loading ? (
        <View className='loading'>
          <Text>正在加载论文内容...</Text>
        </View>
      ) : (
        <View className='content'>
          {/* 导航标签区域 */}
          <View className='navigation-tabs'>
            <View 
              className={`nav-tab ${activeTab === 'overview' && showTabContent ? 'active' : ''}`}
              onClick={() => handleTabClick('overview')}
            >
              <Text className='tab-icon'>📋</Text>
              <Text className='tab-text'>概览</Text>
            </View>
            
            <View 
              className={`nav-tab ${activeTab === 'problem' && showTabContent ? 'active' : ''}`}
              onClick={() => handleTabClick('problem')}
            >
              <Text className='tab-icon'>🎯</Text>
              <Text className='tab-text'>问题</Text>
            </View>
            
            <View 
              className={`nav-tab ${activeTab === 'method' && showTabContent ? 'active' : ''}`}
              onClick={() => handleTabClick('method')}
            >
              <Text className='tab-icon'>🔧</Text>
              <Text className='tab-text'>方法</Text>
            </View>
            
            <View 
              className={`nav-tab ${activeTab === 'results' && showTabContent ? 'active' : ''}`}
              onClick={() => handleTabClick('results')}
            >
              <Text className='tab-icon'>📊</Text>
              <Text className='tab-text'>结果</Text>
            </View>
            
            <View 
              className={`nav-tab ${activeTab === 'takeaways' && showTabContent ? 'active' : ''}`}
              onClick={() => handleTabClick('takeaways')}
            >
              <Text className='tab-icon'>💡</Text>
              <Text className='tab-text'>要点</Text>
            </View>
          </View>

          {/* 标签内容显示区域 */}
          {showTabContent && (
            <View className='tab-content-section'>
              <View className='content-header'>
                <Text className='content-title'>{activeTab === 'overview' ? '论文概览' : 
                  activeTab === 'problem' ? '问题陈述' : 
                  activeTab === 'method' ? '技术方法' : 
                  activeTab === 'results' ? '实验结果' : 
                  activeTab === 'takeaways' ? '关键要点' : '内容显示'}</Text>
                <View className='content-actions'>
                  <Text className='action-btn close-btn' onClick={() => setShowTabContent(false)}>关闭</Text>
                </View>
              </View>
              
              <View className='content-body'>
                <RichText nodes={marked.parse(currentTabContent) as string} />
              </View>
            </View>
          )}

          {/* 目录区域 */}
          <View className='table-of-contents'>
            <Text className='toc-title'>目录</Text>
            <View className='toc-list'>
              {tableOfContents.map((item, index) => (
                <View 
                  key={item.id}
                  className={`toc-item level-${item.level}`}
                  onClick={() => scrollToSection(item.id)}
                >
                  <Text className='toc-text'>{item.title}</Text>
                </View>
              ))}
            </View>
          </View>

          <View className='markdown-content'>
            <RichText nodes={parsedHtml} />
          </View>
          
          {/* 点赞点踩区域 */}
          <View className='feedback-section'>
            <View className='feedback-title'>
              <Text>你喜欢这篇博客吗？</Text>
            </View>
            
            <View className='feedback-buttons'>
              <View 
                className={`feedback-button like-button ${liked ? 'active' : ''} ${blogFeedbackLoading ? 'loading' : ''}`}
                onClick={handleLike}
              >
                <Text className='button-icon'>{liked ? '❤️' : '👍'}</Text>
                <Text className='button-text'>{liked ? '已喜欢' : '喜欢'}</Text>
              </View>
              
              <View 
                className={`feedback-button dislike-button ${disliked ? 'active' : ''} ${blogFeedbackLoading ? 'loading' : ''}`}
                onClick={handleDislike}
              >
                <Text className='button-icon'>{disliked ? '💔' : '👎'}</Text>
                <Text className='button-text'>{disliked ? '已反馈' : '不喜欢'}</Text>
              </View>
            </View>
          </View>
        </View>
      )}
    </View>
  )
}

export default PaperDetail 