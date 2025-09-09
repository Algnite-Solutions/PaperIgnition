// API Configuration
const CONFIG = {
    // API Base URLs - will try in order until one works
    API_BASE_URLS: [
        'http://10.0.1.226:8888',  // Primary server
        'http://127.0.0.1:8888',   // Local fallback
        'http://localhost:8888',   // Alternative local
    ],
    
    // Currently active API URL (will be set dynamically)
    API_BASE_URL: 'http://10.0.1.226:8888',
    
    // API Endpoints (note: backend has /api prefix)
    ENDPOINTS: {
        // Auth endpoints
        LOGIN: '/api/auth/login-email',
        REGISTER: '/api/auth/register-email',
        
        // User endpoints
        USER_PROFILE: '/api/users/me',
        UPDATE_PROFILE: '/api/users/me/profile',
        
        // Paper endpoints
        PAPER_RECOMMENDATIONS: (username) => `/api/papers/recommendations/${username}`,
        PAPER_CONTENT: (paperId) => `/api/papers/paper_content/${paperId}`,
        
        // Favorites endpoints
        FAVORITES_LIST: '/api/favorites/list',
        FAVORITES_ADD: '/api/favorites/add',
        FAVORITES_REMOVE: (paperId) => `/api/favorites/remove/${paperId}`,
        
        // Blog feedback endpoints
        BLOG_FEEDBACK: '/api/papers/blog-feedback',
        BLOG_FEEDBACK_GET: (paperId) => `/api/papers/blog-feedback/${paperId}`,
    },
    
    // Request timeout in milliseconds
    REQUEST_TIMEOUT: 10000,
    
    // Demo credentials for fallback (using real backend users)
    DEMO_USERS: {
        'test@tongji.edu.cn': 'demo123',
        '111@tongji.edu.cn': 'demo123',
        'demo@paperignition.com': 'demo123'
    },
    
    // Test API connectivity
    async testConnection(baseUrl) {
        try {
            const response = await fetch(`${baseUrl}/`, {
                method: 'GET',
                timeout: 3000
            });
            return response.ok;
        } catch (error) {
            console.warn(`Connection test failed for ${baseUrl}:`, error);
            return false;
        }
    },
    
    // Initialize and find working API URL
    async init() {
        console.log('Testing API connections...');
        
        for (const url of this.API_BASE_URLS) {
            console.log(`Testing ${url}...`);
            if (await this.testConnection(url)) {
                this.API_BASE_URL = url;
                console.log(`✅ Using API: ${url}`);
                return url;
            }
        }
        
        console.warn('⚠️ No API server available, using demo mode');
        return null;
    }
};

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
} else {
    window.CONFIG = CONFIG;
}