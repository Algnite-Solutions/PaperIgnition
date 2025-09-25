// Paper data (using the same data from the Taro app)
const samplePapers = [
    {
        id: '1',
        title: 'TigerVector: Bringing High-Performance Vector Search to Graph Databases for Advanced RAG',
        authors: ['Jing Zhang', 'Victor Lee', 'Zhiqi Chen', 'Tianyi Zhang'],
        abstract: 'This paper introduces TigerVector, a novel system that integrates vector search directly into TigerGraph, a distributed graph database. This unified approach aims to overcome the limitations of using separate systems, offering benefits like data consistency, reduced silos, and streamlined hybrid queries for advanced RAG applications.',
        tags: ['Graph Databases', 'Vector Search', 'RAG', 'Performance'],
        submittedDate: '15 May, 2025',
        publishDate: 'May 2025',
        comments: 'Accepted at SIGMOD 2025',
        thumbnail: 'Graph DB'
    },
    {
        id: '2',
        title: 'CLOG-CD: Curriculum Learning based on Oscillating Granularity of Class Decomposed Medical Image Classification',
        authors: ['Asmaa Abbas', 'Mohamed Gaber', 'Mohammed M. Abdelsamea'],
        abstract: 'In this paper, we have also investigated the classification performance of our proposed method based on different acceleration factors and pace function curricula. We used two pre-trained networks, ResNet-50 and DenseNet-121, as the backbone for CLOG-CD. The results with ResNet-50 show that CLOG-CD has the ability to improve classification performance significantly.',
        tags: ['Medical Imaging', 'Curriculum Learning', 'Deep Learning'],
        submittedDate: '3 May, 2025',
        publishDate: 'May 2025',
        comments: 'Published in: IEEE Transactions on Emerging Topics in Computing',
        thumbnail: 'Medical AI'
    },
    {
        id: '3',
        title: 'Attention-Based Feature Fusion for Visual Odometry with Unsupervised Scale Recovery',
        authors: ['Liu Wei', 'Zhang Chen', 'Wang Mei'],
        abstract: 'We present a novel approach for visual odometry that integrates attention mechanisms to fuse features from multiple sources. Our method addresses the scale ambiguity problem in monocular visual odometry through an unsupervised learning framework. Experimental results on KITTI dataset demonstrate superior performance compared to existing methods.',
        tags: ['Visual Odometry', 'Attention Mechanism', 'Unsupervised Learning'],
        submittedDate: '28 April, 2025',
        publishDate: 'April 2025',
        comments: 'To appear in International Conference on Robotics and Automation 2025',
        thumbnail: 'Computer Vision'
    },
    {
        id: '4',
        title: 'FedMix: Adaptive Knowledge Distillation for Personalized Federated Learning',
        authors: ['Sarah Johnson', 'David Chen', 'Michael Brown'],
        abstract: 'This paper introduces FedMix, a novel framework for personalized federated learning that employs adaptive knowledge distillation to balance model personalization and global knowledge sharing. Our approach dynamically adjusts the knowledge transfer between global and local models based on client data distribution characteristics.',
        tags: ['Federated Learning', 'Knowledge Distillation', 'Personalization'],
        submittedDate: '15 April, 2025',
        publishDate: 'April 2025',
        comments: 'Accepted at International Conference on Machine Learning 2025',
        thumbnail: 'Fed Learning'
    }
];

// State management
let currentPapers = [];
let bookmarkedPapers = new Set();
let userFavorites = new Set(); // 新增：存储用户真实的收藏状态
let isLoading = false;
let searchQuery = '';

// DOM elements
const papersContainer = document.getElementById('papersContainer');
const loadingIndicator = document.getElementById('loadingIndicator');
const searchInput = document.getElementById('searchInput');

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    setupAuthNavigation();
});

async function initializeApp() {
    // Load bookmarks from localStorage
    const savedBookmarks = localStorage.getItem('bookmarkedPapers');
    if (savedBookmarks) {
        bookmarkedPapers = new Set(JSON.parse(savedBookmarks));
    }
    
    // Check if user is logged in and load their recommendations
    if (window.AuthService && window.AuthService.isLoggedIn()) {
        // 先加载收藏状态，再加载推荐论文，确保收藏状态正确显示
        console.log('Loading user favorites first...');
        await loadUserFavorites();
        console.log('Loading user recommendations...');
        await loadUserRecommendations();
    } else {
        // Show login prompt or demo papers for non-logged-in users
        showLoginPrompt();
    }
}

function setupEventListeners() {
    // Search functionality
    searchInput.addEventListener('input', debounce(handleSearch, 300));
    
    // Infinite scroll
    window.addEventListener('scroll', handleScroll);
    
    // Theme toggle (if implemented)
    document.addEventListener('keydown', (e) => {
        if (e.key === 'd' && e.ctrlKey) {
            toggleTheme();
        }
    });
}

async function loadUserRecommendations() {
    if (isLoading) return;
    
    const currentUser = window.AuthService.getCurrentUser();
    if (!currentUser || !currentUser.username) {
        console.error('No user information available');
        showLoginPrompt();
        return;
    }
    
    isLoading = true;
    showLoading();
    
    try {
        // Call the backend recommendations API
        const username = currentUser.username;
        const response = await fetch(`/api/papers/recommendations/${encodeURIComponent(username)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.AuthService.getToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const papers = await response.json();
        
        // Transform backend data to match frontend format
        currentPapers = papers.map(paper => ({
            id: paper.id,
            title: paper.title,
            authors: paper.authors ? paper.authors.split(', ') : [],
            abstract: paper.abstract || '',
            url: paper.url || '',
            tags: ['AI', 'Research'], // Default tags since backend doesn't provide them
            submittedDate: 'Recently',
            publishDate: 'Recent',
            comments: 'Recommended for you',
            thumbnail: 'Paper'
        }));
        
        renderPapers();
        
        // 批量检查并同步当前论文的收藏状态
        await syncCurrentPapersFavoriteStatus();
        
    } catch (error) {
        console.error('Error loading recommendations:', error);
        // Fallback to demo papers on error
        showErrorMessage('Failed to load recommendations. Showing sample papers.');
        await loadSamplePapers();
    } finally {
        isLoading = false;
        hideLoading();
    }
}

function showLoginPrompt() {
    papersContainer.innerHTML = `
        <div class="loading">
            <h2>Welcome to PaperIgnition</h2>
            <p>Please <a href="login.html" style="color: var(--accent-red);">login</a> to see your personalized paper recommendations.</p>
            <br>
            <p>Or view some <button onclick="loadSamplePapers()" style="color: var(--accent-red); background: none; border: none; text-decoration: underline; cursor: pointer;">sample papers</button></p>
        </div>
    `;
}

async function loadSamplePapers() {
    currentPapers = samplePapers;
    renderPapers();
    
    // 如果用户已登录，批量检查并同步当前论文的收藏状态
    await syncCurrentPapersFavoriteStatus();
}

async function loadPapers(append = false) {
    // This function is now used primarily for search functionality
    if (!window.AuthService || !window.AuthService.isLoggedIn()) {
        await loadSamplePapers();
        return;
    }
    
    // For search functionality, filter current papers
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    
    setTimeout(() => {
        const filteredPapers = searchQuery 
            ? currentPapers.filter(paper => 
                paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                paper.abstract.toLowerCase().includes(searchQuery.toLowerCase()) ||
                paper.authors.some(author => author.toLowerCase().includes(searchQuery.toLowerCase()))
            )
            : currentPapers;
        
        if (append) {
            // For infinite scroll - in this case just show same papers
            currentPapers = [...currentPapers, ...filteredPapers.slice(0, 2)];
        } else {
            currentPapers = filteredPapers;
        }
        
        renderPapers();
        isLoading = false;
        hideLoading();
    }, 300);
}

function renderPapers() {
    papersContainer.innerHTML = '';
    
    currentPapers.forEach(paper => {
        const paperElement = createPaperCard(paper);
        papersContainer.appendChild(paperElement);
    });
    
    if (currentPapers.length === 0) {
        papersContainer.innerHTML = '<div class="loading"><p>No papers found matching your search.</p></div>';
    }
}

function createPaperCard(paper) {
    const card = document.createElement('article');
    card.className = 'paper-card';
    card.dataset.paperId = paper.id;
    
    // 移除了收藏状态检查，因为不再显示Save按钮
    
    card.innerHTML = `
        <div class="paper-thumbnail">
            ${paper.thumbnail}
        </div>
        <div class="paper-content">
            <h2 class="paper-title">${paper.title}</h2>
            <p class="paper-authors">${Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors}</p>
            <p class="paper-abstract">${paper.abstract}</p>
            <div class="paper-meta">
                <span>${paper.publishDate}</span>
                <span>•</span>
                <span>${paper.comments}</span>
            </div>
            <div class="paper-tags">
                ${paper.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}
            </div>
        </div>
    `;
    
    // Add click handler for paper details
    card.addEventListener('click', (e) => {
        showPaperDetail(paper);
    });
    
    return card;
}

async function toggleBookmark(paperId, event) {
    event.stopPropagation();
    
    const button = event.target;
    const isLoggedIn = window.AuthService && window.AuthService.isLoggedIn();
    
    if (!isLoggedIn) {
        // 未登录用户使用localStorage
    if (bookmarkedPapers.has(paperId)) {
        bookmarkedPapers.delete(paperId);
    } else {
        bookmarkedPapers.add(paperId);
    }
    
    // Save to localStorage
    localStorage.setItem('bookmarkedPapers', JSON.stringify([...bookmarkedPapers]));
    
    // Update UI
    const isBookmarked = bookmarkedPapers.has(paperId);
    button.className = `bookmark-btn ${isBookmarked ? 'bookmarked' : ''}`;
    button.textContent = isBookmarked ? '★ Saved' : '☆ Save';
        
        return;
    }
    
    // 以下是登录用户的API调用逻辑
    const isCurrentlyFavorited = userFavorites.has(paperId);
    
    // Find the paper data
    const paper = currentPapers.find(p => p.id === paperId);
    if (!paper) {
        console.error('Paper not found:', paperId);
        return;
    }
    
    // Show loading state
    const originalText = button.textContent;
    button.disabled = true;
    button.textContent = isCurrentlyFavorited ? 'Removing...' : 'Adding...';
    button.style.opacity = '0.6';
    
    try {
        const token = window.AuthService.getToken();
        console.log('User logged in:', window.AuthService.isLoggedIn());
        console.log('Token available:', !!token);
        
        if (!token) {
            throw new Error('No authentication token available');
        }
        
        if (isCurrentlyFavorited) {
            // Remove from favorites
            const response = await fetch(`/api/favorites/remove/${encodeURIComponent(paperId)}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            
            // Update local state
            userFavorites.delete(paperId);
            bookmarkedPapers.delete(paperId);
            
            // Update UI
            button.className = 'bookmark-btn';
            button.textContent = '☆ Save';
            
            showSuccessMessage('Removed from favorites');
            
        } else {
            // Add to favorites
            const authorsStr = Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors;
            
            // 清理和验证数据
            const cleanAbstract = (paper.abstract || '')
                .replace(/\r\n/g, '\n')  // 统一换行符
                .replace(/[""]/g, '"')   // 替换特殊引号
                .replace(/['']/g, "'")   // 替换特殊单引号  
                .replace(/…/g, '...')    // 替换省略号
                .trim();
            
            const favoriteData = {
                paper_id: String(paper.id).substring(0, 50), // 确保是字符串并限制长度
                title: String(paper.title).substring(0, 255),
                authors: String(authorsStr).substring(0, 255),
                abstract: cleanAbstract
            };
            // 仅在存在且是有效URL时才发送url字段
            if (paper.url && /^https?:\/\//i.test(String(paper.url))) {
                favoriteData.url = String(paper.url).substring(0, 255);
            }
            
            console.log('Sending favorite data:', favoriteData);
            console.log('JSON body:', JSON.stringify(favoriteData));
            console.log('Token:', token ? 'Token exists' : 'No token');
            
            const response = await fetch(`/api/favorites/add`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(favoriteData)
            });
            
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (!response.ok) {
                let errorMessage = `HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    console.log('Error response data:', errorData);
                    console.log('Error detail array:', errorData.detail);
                    
                    if (response.status === 400 && errorData.detail?.includes('已在收藏')) {
                        // Paper already favorited
                        userFavorites.add(paperId);
                        bookmarkedPapers.add(paperId);
                        button.className = 'bookmark-btn bookmarked';
                        button.textContent = '★ Saved';
                        showSuccessMessage('Already in favorites');
                        return;
                    }
                    
                    // Handle different error response formats
                    if (errorData.detail) {
                        if (Array.isArray(errorData.detail)) {
                            // FastAPI validation errors return an array
                            errorMessage = errorData.detail.map(err => {
                                if (err.loc && err.msg) {
                                    return `${err.loc.join('.')}: ${err.msg}`;
                                }
                                return err.msg || JSON.stringify(err);
                            }).join('; ');
                        } else {
                            errorMessage = errorData.detail;
                        }
                    } else if (errorData.message) {
                        errorMessage = errorData.message;
                    } else if (typeof errorData === 'string') {
                        errorMessage = errorData;
                    } else {
                        errorMessage = JSON.stringify(errorData);
                    }
                } catch (parseError) {
                    console.error('Failed to parse error response:', parseError);
                    const responseText = await response.text();
                    console.log('Raw error response:', responseText);
                    errorMessage = responseText || `HTTP error! status: ${response.status}`;
                }
                
                throw new Error(errorMessage);
            }
            
            // Update local state
            userFavorites.add(paperId);
            bookmarkedPapers.add(paperId);
            
            // Update UI
            button.className = 'bookmark-btn bookmarked';
            button.textContent = '★ Saved';
            
            showSuccessMessage('Added to favorites');
        }
        
        // Update localStorage for backward compatibility
        localStorage.setItem('bookmarkedPapers', JSON.stringify([...bookmarkedPapers]));
        
    } catch (error) {
        console.error('Error toggling favorite:', error);
        console.error('Error type:', typeof error);
        console.error('Error constructor:', error.constructor.name);
        
        // Restore original state
        button.textContent = originalText;
        
        // Show error message with better error handling
        let errorMessage = 'Unknown error';
        if (error instanceof Error) {
            errorMessage = error.message;
        } else if (typeof error === 'string') {
            errorMessage = error;
        } else if (error && error.toString) {
            errorMessage = error.toString();
        } else if (error) {
            errorMessage = JSON.stringify(error);
        }
        
        showErrorMessage(`Failed to ${isCurrentlyFavorited ? 'remove from' : 'add to'} favorites: ${errorMessage}`);
        
    } finally {
        // Restore button state
        button.disabled = false;
        button.style.opacity = '1';
    }
}

async function loadUserFavorites() {
    // Load user's favorites from backend to sync state
    if (!window.AuthService || !window.AuthService.isLoggedIn()) {
        return;
    }
    
    try {
        const token = window.AuthService.getToken();
        const response = await fetch(`/api/favorites/list`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const favorites = await response.json(); // 完整的收藏数据
            
            // Update local favorite state
            userFavorites.clear();
            bookmarkedPapers.clear();
            
            favorites.forEach(fav => {
                userFavorites.add(fav.paper_id);
                bookmarkedPapers.add(fav.paper_id);
            });
            
            // Update localStorage
            localStorage.setItem('bookmarkedPapers', JSON.stringify([...bookmarkedPapers]));
            
            console.log('Favorites loaded:', favorites.length, 'papers');
            console.log('User favorites updated:', [...userFavorites]);
            
            // Re-render papers to update bookmark states
            if (currentPapers.length > 0) {
                console.log('Re-rendering papers with updated favorite states');
                renderPapers();
            }
        } else {
            console.error('Failed to load favorites:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('Error loading user favorites:', error);
    }
}

async function syncCurrentPapersFavoriteStatus() {
    // 由于批量检查接口在服务器上不存在，这里只是一个占位函数
    // 收藏状态同步主要通过loadUserFavorites()函数完成
    console.log('Sync function called, but using loadUserFavorites for actual sync');
}

function showSuccessMessage(message) {
    // Create temporary success message
    const successDiv = document.createElement('div');
    successDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #10b981;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideInRight 0.3s ease;
    `;
    successDiv.textContent = message;
    
    document.body.appendChild(successDiv);
    
    setTimeout(() => {
        successDiv.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            if (document.body.contains(successDiv)) {
                document.body.removeChild(successDiv);
            }
        }, 300);
    }, 2000);
}

function showErrorMessage(message) {
    // Create temporary error message
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #ef4444;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        animation: slideInRight 0.3s ease;
    `;
    errorDiv.textContent = message;
    
    document.body.appendChild(errorDiv);
    
    setTimeout(() => {
        errorDiv.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => {
            if (document.body.contains(errorDiv)) {
                document.body.removeChild(errorDiv);
            }
        }, 300);
    }, 3000);
}

function handleSearch(event) {
    searchQuery = event.target.value.trim();
    loadPapers(false);
}

function handleScroll() {
    if (isLoading) return;
    
    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    if (scrollTop + clientHeight >= scrollHeight - 5) {
        // Load more papers (in a real app, this would fetch the next page)
        // For demo purposes, we'll just show the same papers
        if (currentPapers.length > 0 && currentPapers.length < 20) {
            loadPapers(true);
        }
    }
}

function showPaperDetail(paper) {
    if (!paper) return;
    
    // Store paper information in sessionStorage for the detail page
    sessionStorage.setItem(`paper_${paper.id}`, JSON.stringify(paper));
    
    // Navigate to paper detail page
    window.location.href = `paper.html?id=${paper.id}`;
}

function showLoading() {
    loadingIndicator.style.display = 'block';
}

function hideLoading() {
    loadingIndicator.style.display = 'none';
}

function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Utility function for debouncing
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// API service functions (similar to the original services)
class PaperService {
    static async getPapers(page = 1, search = '') {
        try {
            // In a real implementation, this would make an HTTP request
            // const response = await fetch(`${API_BASE_URL}/papers?page=${page}&search=${search}`);
            // return await response.json();
            
            // For demo, return sample data
            return {
                papers: samplePapers,
                hasMore: false,
                total: samplePapers.length
            };
        } catch (error) {
            console.error('Error fetching papers:', error);
            throw error;
        }
    }
    
    static async getPaperDetail(paperId) {
        try {
            // const response = await fetch(`${API_BASE_URL}/papers/${paperId}`);
            // return await response.json();
            
            return samplePapers.find(p => p.id === paperId);
        } catch (error) {
            console.error('Error fetching paper detail:', error);
            throw error;
        }
    }
    
    static async getPaperContent(paperId) {
        try {
            // const response = await fetch(`${API_BASE_URL}/papers/${paperId}/content`);
            // return await response.json();
            
            // Return sample content (TigerVector content from the original service)
            return {
                content: `
## TigerVector: Bringing High-Performance Vector Search to Graph Databases for Advanced RAG

Retrieval-Augmented Generation (RAG) has become a cornerstone for grounding Large Language Models (LLMs) with external data. While traditional RAG often relies on vector databases storing semantic embeddings, this approach can struggle with complex queries that require understanding relationships between data points – a strength of graph databases.

Enter VectorGraphRAG, a promising hybrid approach that combines the power of vector search for semantic similarity with graph traversal for structural context. The paper "TigerVector: Supporting Vector Search in Graph Databases for Advanced RAGs" introduces TigerVector, a novel system that integrates vector search directly into TigerGraph, a distributed graph database.

### Key Innovations

**A Unified Data Model:** TigerVector introduces a new \`embedding\` attribute type for vertices. This isn't just a list of floats; it explicitly manages crucial metadata like dimensionality, the model used, index type, and similarity metric.

**Decoupled Storage:** Recognizing that vector embeddings are often much larger than other attributes, TigerVector stores vectors separately in "embedding segments." These segments mirror the vertex partitioning of the graph, ensuring related vector and graph data reside together for efficient processing.

**Leveraging MPP Architecture:** Built within TigerGraph's Massively Parallel Processing (MPP) architecture, TigerVector distributes vector data and processing across multiple machines. Vector indexes (currently supporting HNSW) are built per segment, and queries are parallelized, with results merged by a coordinator.
                `
            };
        } catch (error) {
            console.error('Error fetching paper content:', error);
            throw error;
        }
    }
}

// Setup authentication-based navigation
function setupAuthNavigation() {
    const profileLink = document.getElementById('profileLink');
    
    if (profileLink) {
        profileLink.addEventListener('click', (e) => {
            e.preventDefault();
            handleProfileNavigation();
        });
    }
    
    // Update navigation based on auth state
    updateNavigation();
    
    // Listen for auth state changes
    window.addEventListener('authStateChanged', (event) => {
        updateNavigation();
        
        // Reload papers when auth state changes
        if (event.detail.isLoggedIn) {
            loadUserRecommendations();
            loadUserFavorites(); // 用户登录时加载收藏
        } else {
            showLoginPrompt();
        }
    });
}

function handleProfileNavigation() {
    if (window.AuthService && window.AuthService.isLoggedIn()) {
        window.location.href = 'profile.html';
    } else {
        window.location.href = 'login.html';
    }
}

function updateNavigation() {
    const profileLink = document.getElementById('profileLink');
    if (!profileLink) return;
    
    if (window.AuthService && window.AuthService.isLoggedIn()) {
        const user = window.AuthService.getCurrentUser();
        profileLink.textContent = user?.username || 'Profile';
        profileLink.href = 'profile.html';
    } else {
        profileLink.textContent = 'Login';
        profileLink.href = 'login.html';
    }
}
