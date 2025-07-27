import { defineConfig, type UserConfigExport } from '@tarojs/cli'

import devConfig from './dev'
import prodConfig from './prod'

// https://taro-docs.jd.com/docs/next/config#defineconfig-辅助函数
export default defineConfig<'vite'>(async (merge, { command, mode }) => {
  const baseConfig: UserConfigExport<'vite'> = {
    projectName: 'AIgnite',
    date: '2025-5-7',
    designWidth: 750,
    deviceRatio: {
      640: 2.34 / 2,
      750: 1,
      375: 2,
      828: 1.81 / 2
    },
    sourceRoot: 'src',
    outputRoot: 'dist',
    plugins: [],
    defineConstants: {
      // Make environment variables available in the frontend code
      // Vite will load .env files based on mode (NODE_ENV)
      // These values from Node.js process.env are then passed to the client-side process.env
      'process.env.REACT_APP_DEV_API_BASE_URL': JSON.stringify(process.env.REACT_APP_DEV_API_BASE_URL || 'http://127.0.0.1:8000'),//http://10.0.1.226:8080
      'process.env.REACT_APP_PROD_API_BASE_URL': JSON.stringify(process.env.REACT_APP_PROD_API_BASE_URL || 'https://your-production-api.com'),
      'process.env.REACT_APP_STAGING_API_BASE_URL': JSON.stringify(process.env.REACT_APP_STAGING_API_BASE_URL || 'https://your-staging-api.com'),
      'process.env.REACT_APP_USE_STAGING_API': JSON.stringify(process.env.REACT_APP_USE_STAGING_API || 'false'),
      // It's crucial to also pass NODE_ENV itself if your src/config/api.ts relies on it directly for logic
      'process.env.NODE_ENV': JSON.stringify(mode || process.env.NODE_ENV || 'development')
    },
    /* copy: {
      patterns: [
        { from: 'src/assets/icons', to: 'dist/assets/icons' }
      ],
      options: {
      }
    }, */
    framework: 'react',
    compiler: 'vite',
    mini: {
      postcss: {
        pxtransform: {
          enable: true,
          config: {

          }
        },
        cssModules: {
          enable: false, // 默认为 false，如需使用 css modules 功能，则设为 true
          config: {
            namingPattern: 'module', // 转换模式，取值为 global/module
            generateScopedName: '[name]__[local]___[hash:base64:5]'
          }
        }
      },
      // 复制静态资源
      /* copyPlugin: {
        patterns: [
          { from: 'src/assets/icons', to: 'dist/assets/icons' }
        ]
      } */
    },
    h5: {
      publicPath: '/',
      staticDirectory: 'static',

      miniCssExtractPluginOption: {
        ignoreOrder: true,
        filename: 'css/[name].[hash].css',
        chunkFilename: 'css/[name].[chunkhash].css'
      },
      postcss: {
        autoprefixer: {
          enable: true,
          config: {}
        },
        cssModules: {
          enable: false, // 默认为 false，如需使用 css modules 功能，则设为 true
          config: {
            namingPattern: 'module', // 转换模式，取值为 global/module
            generateScopedName: '[name]__[local]___[hash:base64:5]'
          }
        }
      },
    },
    rn: {
      appName: 'taroDemo',
      postcss: {
        cssModules: {
          enable: false, // 默认为 false，如需使用 css modules 功能，则设为 true
        }
      }
    }
  }


  if (process.env.NODE_ENV === 'development') {
    // 本地开发构建配置（不混淆压缩）
    return merge({}, baseConfig, devConfig)
  }
  // 生产构建配置（默认开启压缩混淆等）
  return merge({}, baseConfig, prodConfig)
})
