import { View, RichText, Text } from '@tarojs/components'
import React, { useEffect, useState } from 'react'
import { useAppDispatch } from '../../store/hooks'
import { clearCurrentPaper } from '../../store/slices/paperSlice'
import Taro from '@tarojs/taro'
import { marked } from 'marked'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { getPaperContent } from '../../services/paperService'
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

  const fetchPaperContent = async (paperId: string) => {
    try {
      setLoading(true)
      
      // 获取论文内容
      const contentResponse = await getPaperContent(paperId)
      if (contentResponse.statusCode === 200 && contentResponse.data) {
        const markdownContent = contentResponse.data.content
        try {
          // 将Markdown转换为HTML
          const htmlContent = marked.parse(markdownContent)
          // 修复图片链接并进行简单清理
          const fixedHtml = fixImageLinks(htmlContent as string)
          const sanitizedHtml = simpleSanitizeHtml(fixedHtml)
          setParsedHtml(sanitizedHtml)
        } catch (parseError) {
          console.error('解析Markdown内容失败', parseError)
          Taro.showToast({
            title: '解析内容失败',
            icon: 'none',
            duration: 2000
          })
        }
      } else {
        const errorMessage = contentResponse.error || 'Failed to fetch paper content'
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

  useEffect(() => {
    const params = Taro.getCurrentInstance().router?.params
    if (params?.id) {
      fetchPaperContent(params.id as string)
    }
    return () => {
      dispatch(clearCurrentPaper())
    }
  }, [])

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
          <View className='markdown-content'>
            <RichText nodes={parsedHtml} />
          </View>
        </View>
      )}
    </View>
  )
}

export default PaperDetail 