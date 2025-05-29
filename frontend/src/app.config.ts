export default defineAppConfig({
  pages: [
    'pages/index/index',
    'pages/register/index',
    'pages/login/index',
    'pages/interests/index',
    'pages/recommendations/index',
    'pages/paper-detail/index',
    'pages/paper-list/index',
    'pages/favorites/index',
    'pages/profile/index',
    'pages/research-interests/index'
  ],
  window: {
    backgroundTextStyle: 'light',
    navigationBarBackgroundColor: '#fff',
    navigationBarTitleText: 'AIgnite - 智能论文推荐',
    navigationBarTextStyle: 'black'
  },
  tabBar: {
    custom: false,
    color: '#888888',
    selectedColor: '#1296db',
    backgroundColor: '#ffffff',
    borderStyle: 'black',
    list: [
      {
        pagePath: 'pages/recommendations/index',
        text: '推荐',
        iconPath: '_assets/icons/paper.png',
        selectedIconPath: '_assets/icons/paper.png'
      },
      {
        pagePath: 'pages/favorites/index',
        text: '收藏',
        iconPath: '_assets/icons/heart.png',
        selectedIconPath: '_assets/icons/heart.png'
      },
      {
        pagePath: 'pages/profile/index',
        text: '个人',
        iconPath: '_assets/icons/person.png',
        selectedIconPath: '_assets/icons/person.png'
      }
    ]
  },
  permission: {
    'scope.userInfo': {
      desc: '你的用户信息将用于个性化推荐服务'
    }
  }
})
