// API Configuration from config file
const API_BASE_URL = window.CONFIG?.API_BASE_URL || 'http://10.0.1.226:8888';
const API_ENDPOINTS = window.CONFIG?.ENDPOINTS || {};

// Sample papers for fallback when API is not available
// Note: In production, papers are loaded from API which uses real paper IDs
const samplePapers = [
    {
        id: '2506.16692v2', // Use real paper ID that has blog content
        title: 'LegiGPT: Party Politics and Transport Policy with Large Language Model',
        authors: ['Hyunsoo Yun', 'Eun Hak Lee'],
        abstract: 'Given the significant influence of lawmakers\' political ideologies on legislative decision-making, analyzing their impact on transportation-related policymaking is of critical importance. This study introduces a novel framework that integrates a large language model (LLM) with explainable artificial intelligence (XAI) to analyze transportation-related legislative proposals.',
        tags: ['Large Language Model', 'Political Analysis', 'Transportation Policy'],
        submittedDate: '16 June, 2025',
        publishDate: 'June 2025',
        comments: 'Research Paper',
        thumbnail: 'Politics & AI'
    },
    {
        id: '2508.00652v1',
        title: 'The Manipulative Power of Voice Characteristics: Investigating Deceptive Patterns in Mandarin Chinese Female Synthetic Speech',
        authors: ['Shuning Zhang', 'Han Chen', 'Yabo Wang', 'Yiqun Xu', 'Jiaqi Bai', 'Yuanyuan Wu', 'Shixuan Li', 'Xin Yi', 'Chunhui Wang', 'Hewu Li'],
        abstract: 'Pervasive voice interaction enables deceptive patterns through subtle voice characteristics, yet empirical investigation into this manipulation lags behind, especially within major non-English language contexts.',
        tags: ['Voice Synthesis', 'Deception', 'Mandarin Chinese'],
        submittedDate: '1 August, 2025',
        publishDate: 'August 2025',
        comments: 'Research Paper',
        thumbnail: 'Voice AI'
    },
    {
        id: '2507.09018v1',
        title: 'A Critique of Deng\'s "P=NP"',
        authors: ['Isabel Humphreys', 'Matthew Iceland', 'Harry Liuson', 'Dylan McKellips', 'Leo Sciortino'],
        abstract: 'In this paper, we critically examine Deng\'s "P=NP" [Den24]. The paper claims that there is a polynomial-time algorithm that decides 3-coloring for graphs with vertices of degree at most 4, which is known to be an NP-complete problem.',
        tags: ['Theoretical Computer Science', 'Complexity Theory', 'P vs NP'],
        submittedDate: '9 July, 2025',
        publishDate: 'July 2025',
        comments: 'Research Paper',
        thumbnail: 'Theory CS'
    },
    {
        id: 'paper_001',
        title: 'Example Paper on FastAPI',
        authors: ['Alice', 'Bob'],
        abstract: 'This is a demo abstract.',
        tags: ['Demo', 'FastAPI'],
        submittedDate: '1 January, 2025',
        publishDate: 'January 2025',
        comments: 'Demo Paper',
        thumbnail: 'Demo'
    }
];

// State management
let currentPapers = [];
let bookmarkedPapers = new Set();
let isLoading = false;
let searchQuery = '';

// DOM elements
const papersContainer = document.getElementById('papersContainer');
const loadingIndicator = document.getElementById('loadingIndicator');
const searchInput = document.getElementById('searchInput');

// Initialize the application
document.addEventListener('DOMContentLoaded', async () => {
    // Initialize API configuration first
    if (window.CONFIG && window.CONFIG.init) {
        await window.CONFIG.init();
    }
    
    await initializeApp();
    setupEventListeners();
    setupAuthNavigation();
});

async function initializeApp() {
    // Load bookmarks from API or localStorage
    if (window.AuthService?.isLoggedIn()) {
        // User is logged in, load favorites from API
        await favoritesService.loadFavorites();
    } else {
        // Load bookmarks from localStorage for non-logged users
        const savedBookmarks = localStorage.getItem('bookmarkedPapers');
        if (savedBookmarks) {
            bookmarkedPapers = new Set(JSON.parse(savedBookmarks));
        }
    }
    
    // Load initial papers
    loadPapers();
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

async function loadPapers(append = false) {
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    
    try {
        // Get current user info to fetch their recommendations
        const currentUser = window.AuthService?.getCurrentUser();
        const isLoggedIn = window.AuthService?.isLoggedIn();
        
        console.log('Loading papers for user:', currentUser);
        console.log('Is logged in:', isLoggedIn);
        
        let userIdentifier = null;
        if (isLoggedIn && currentUser) {
            // Backend API expects the username (which is actually the email)
            // Use email first, fallback to username
            userIdentifier = currentUser.email || currentUser.username;
            console.log('User logged in. Email:', currentUser.email, 'Username:', currentUser.username);
            console.log('Using user identifier for API:', userIdentifier);
        } else {
            console.log('User not logged in, will show sample papers');
        }
        
        // Fetch papers from API
        const result = await PaperService.getPapers(userIdentifier);
        let allPapers = result.papers || [];
        
        console.log('Fetched papers:', allPapers.length);
        
        // Apply search filter if needed
        const filteredPapers = searchQuery 
            ? allPapers.filter(paper => 
                paper.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                paper.abstract?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                (paper.authors && paper.authors.toLowerCase().includes(searchQuery.toLowerCase()))
            )
            : allPapers;
        
        if (append) {
            currentPapers = [...currentPapers, ...filteredPapers];
        } else {
            currentPapers = filteredPapers;
        }
        
        renderPapers();
        
        // Show appropriate message based on user state
        if (currentPapers.length === 0) {
            if (isLoggedIn) {
                papersContainer.innerHTML = '<div class="loading"><p>暂无推荐论文。请联系管理员为您的账户添加推荐内容。</p></div>';
            } else {
                papersContainer.innerHTML = '<div class="loading"><p>请登录查看个性化推荐论文。</p></div>';
            }
        }
    } catch (error) {
        console.error('Failed to load papers:', error);
        // Show error message to user
        papersContainer.innerHTML = '<div class="loading"><p>Failed to load papers. Please try refreshing the page.</p></div>';
    } finally {
        isLoading = false;
        hideLoading();
    }
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
    
    const isBookmarked = bookmarkedPapers.has(paper.id);
    
    // Handle different data formats from API vs sample data
    // Backend API returns authors as string, sample data uses array
    const authors = Array.isArray(paper.authors) ? 
        paper.authors.join(', ') : 
        (paper.authors || 'Unknown Authors');
    const tags = paper.tags || [];
    const publishDate = paper.publishDate || paper.submittedDate || '';
    const comments = paper.comments || '';
    
    // Create thumbnail from paper title or use default
    const thumbnail = paper.thumbnail || createThumbnail(paper.title || 'Paper');
    const thumbnailVariant = `variant-${(Math.abs(paper.id.split('').reduce((a, b) => (a * 31 + b.charCodeAt(0)) % 5, 0)) + 1)}`;
    
    function createThumbnail(title) {
        const words = title.split(' ').slice(0, 2);
        return words.join(' ') || 'Paper';
    }
    
    card.innerHTML = `
        <div class="paper-thumbnail ${thumbnailVariant}">
            ${thumbnail}
        </div>
        <div class="paper-content">
            <h2 class="paper-title">${paper.title || 'Untitled'}</h2>
            <p class="paper-authors">${authors}</p>
            <p class="paper-abstract">${paper.abstract || 'No abstract available'}</p>
            <div class="paper-meta">
                ${publishDate ? `<span>${publishDate}</span>` : ''}
                ${publishDate && comments ? '<span>•</span>' : ''}
                ${comments ? `<span>${comments}</span>` : ''}
            </div>
            <div class="paper-tags">
                ${Array.isArray(tags) ? tags.map(tag => `<span class="tag">${tag}</span>`).join('') : ''}
            </div>
        </div>
        <div class="paper-actions">
            <button class="bookmark-btn ${isBookmarked ? 'bookmarked' : ''}" 
                    onclick="toggleBookmark('${paper.id}', event)">
                ${isBookmarked ? '★ Saved' : '☆ Save'}
            </button>
        </div>
    `;
    
    // Add click handler for paper details
    card.addEventListener('click', (e) => {
        if (!e.target.classList.contains('bookmark-btn')) {
            showPaperDetail(paper.id);
        }
    });
    
    return card;
}

// Favorites Service for API integration
class FavoritesService {
    constructor() {
        this.authService = window.AuthService;
    }

    // Get user's favorites from API
    async getFavorites() {
        if (!this.authService?.isLoggedIn()) {
            // Return localStorage favorites for non-logged users
            const saved = localStorage.getItem('bookmarkedPapers');
            return saved ? JSON.parse(saved) : [];
        }

        try {
            const response = await fetch(`${API_BASE_URL}${window.CONFIG?.ENDPOINTS?.FAVORITES_LIST || '/api/favorites/list'}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.authService.getToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const favorites = await response.json();
                return favorites.map(fav => fav.paper_id);
            } else {
                console.warn('Failed to fetch favorites from API');
                return [];
            }
        } catch (error) {
            console.error('Error fetching favorites:', error);
            return [];
        }
    }

    // Add paper to favorites
    async addFavorite(paper) {
        if (!this.authService?.isLoggedIn()) {
            // Use localStorage for non-logged users
            bookmarkedPapers.add(paper.id);
            localStorage.setItem('bookmarkedPapers', JSON.stringify([...bookmarkedPapers]));
            return { success: true };
        }

        try {
            const response = await fetch(`${API_BASE_URL}${window.CONFIG?.ENDPOINTS?.FAVORITES_ADD || '/api/favorites/add'}`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.authService.getToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    paper_id: paper.id,
                    title: paper.title,
                    authors: Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors,
                    abstract: paper.abstract,
                    url: paper.url || ''
                })
            });

            if (response.ok) {
                bookmarkedPapers.add(paper.id);
                return { success: true };
            } else {
                const errorData = await response.json();
                return { success: false, error: errorData.detail || 'Failed to add favorite' };
            }
        } catch (error) {
            console.error('Error adding favorite:', error);
            return { success: false, error: 'Network error' };
        }
    }

    // Remove paper from favorites
    async removeFavorite(paperId) {
        if (!this.authService?.isLoggedIn()) {
            // Use localStorage for non-logged users
            bookmarkedPapers.delete(paperId);
            localStorage.setItem('bookmarkedPapers', JSON.stringify([...bookmarkedPapers]));
            return { success: true };
        }

        try {
            const response = await fetch(`${API_BASE_URL}${window.CONFIG?.ENDPOINTS?.FAVORITES_REMOVE?.(paperId) || `/api/favorites/remove/${paperId}`}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.authService.getToken()}`,
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                bookmarkedPapers.delete(paperId);
                return { success: true };
            } else {
                const errorData = await response.json();
                return { success: false, error: errorData.detail || 'Failed to remove favorite' };
            }
        } catch (error) {
            console.error('Error removing favorite:', error);
            return { success: false, error: 'Network error' };
        }
    }

    // Load favorites and update local state
    async loadFavorites() {
        const favorites = await this.getFavorites();
        bookmarkedPapers = new Set(favorites);
        
        // Also save to localStorage as backup
        localStorage.setItem('bookmarkedPapers', JSON.stringify([...bookmarkedPapers]));
    }
}

// Create global favorites service instance
const favoritesService = new FavoritesService();

// Toggle bookmark status with API integration
async function toggleBookmark(paperId, event) {
    event.stopPropagation();
    
    const isCurrentlyBookmarked = bookmarkedPapers.has(paperId);
    const button = event.target;
    
    // Update UI immediately for better UX
    button.disabled = true;
    button.textContent = isCurrentlyBookmarked ? 'Removing...' : 'Saving...';
    
    try {
        let result;
        
        if (isCurrentlyBookmarked) {
            result = await favoritesService.removeFavorite(paperId);
        } else {
            // Find the paper data to send to API
            const paper = currentPapers.find(p => p.id === paperId) || samplePapers.find(p => p.id === paperId);
            if (!paper) {
                throw new Error('Paper not found');
            }
            result = await favoritesService.addFavorite(paper);
        }
        
        if (result.success) {
            // Update UI to reflect the change
            const newIsBookmarked = bookmarkedPapers.has(paperId);
            button.className = `bookmark-btn ${newIsBookmarked ? 'bookmarked' : ''}`;
            button.textContent = newIsBookmarked ? '★ Saved' : '☆ Save';
            
            // Show success message
            showToast(newIsBookmarked ? 'Paper saved!' : 'Paper removed from saved');
        } else {
            // Revert UI on error
            showToast(result.error || 'Failed to update bookmark', 'error');
        }
    } catch (error) {
        console.error('Error toggling bookmark:', error);
        showToast('Failed to update bookmark', 'error');
    } finally {
        button.disabled = false;
        
        // Ensure UI is in correct state
        const finalIsBookmarked = bookmarkedPapers.has(paperId);
        button.className = `bookmark-btn ${finalIsBookmarked ? 'bookmarked' : ''}`;
        button.textContent = finalIsBookmarked ? '★ Saved' : '☆ Save';
    }
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

function showPaperDetail(paperId) {
    // Navigate to paper detail page with the paper ID
    // The paper.html page will handle loading both sample and API data
    window.location.href = `paper.html?id=${paperId}`;
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
    static async getPapers(username = null) {
        try {
            if (!username) {
                // If no username (not logged in), return sample data
                console.log('No user logged in, showing sample papers');
                return {
                    papers: samplePapers,
                    hasMore: false,
                    total: samplePapers.length
                };
            }

            console.log(`Fetching recommendations for user: ${username}`);
            const endpoint = window.CONFIG?.ENDPOINTS?.PAPER_RECOMMENDATIONS(username) || `/api/papers/recommendations/${username}`;
            const url = `${API_BASE_URL}${endpoint}`;
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: window.CONFIG?.REQUEST_TIMEOUT || 10000
            });
            
            if (!response.ok) {
                console.warn(`API returned ${response.status}, falling back to sample data`);
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const papers = await response.json();
            console.log(`Retrieved ${papers.length} papers from API`);
            
            // If API returns empty array, fallback to sample data
            if (!papers || papers.length === 0) {
                console.warn('API returned empty results, showing sample papers');
                return {
                    papers: samplePapers,
                    hasMore: false,
                    total: samplePapers.length
                };
            }
            
            return {
                papers: papers,
                hasMore: false,
                total: papers.length
            };
        } catch (error) {
            console.error('Error fetching papers:', error);
            // Fallback to sample data on error
            return {
                papers: samplePapers,
                hasMore: false,
                total: samplePapers.length
            };
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
            const endpoint = window.CONFIG?.ENDPOINTS?.PAPER_CONTENT(paperId) || `/api/papers/paper_content/${paperId}`;
            const url = `${API_BASE_URL}${endpoint}`;
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                },
                timeout: window.CONFIG?.REQUEST_TIMEOUT || 10000
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const content = await response.text();
            return {
                content: content
            };
        } catch (error) {
            console.error('Error fetching paper content:', error);
            // Fallback to sample content
            return {
                content: `
## Paper Content Not Available

The paper content could not be loaded from the server. This might be due to:

- Network connectivity issues
- Server maintenance
- The paper content not being available in the database

Please try again later or contact support if the problem persists.
                `
            };
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
    window.addEventListener('authStateChanged', updateNavigation);
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

// Simple toast notification function
function showToast(message, type = 'success') {
    // Remove any existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    
    // Style the toast
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? 'var(--error-color, #dc2626)' : 'var(--success-color, #059669)'};
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        z-index: 1000;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        animation: toastSlideIn 0.3s ease-out;
    `;
    
    // Add CSS animation
    if (!document.querySelector('#toast-styles')) {
        const styles = document.createElement('style');
        styles.id = 'toast-styles';
        styles.textContent = `
            @keyframes toastSlideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes toastSlideOut {
                from {
                    transform: translateX(0);
                    opacity: 1;
                }
                to {
                    transform: translateX(100%);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(styles);
    }
    
    // Add to DOM
    document.body.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'toastSlideOut 0.3s ease-in';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 300);
    }, 3000);
}

// Export for potential use in other modules
window.PaperService = PaperService;
window.FavoritesService = favoritesService;