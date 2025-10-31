// Paper data (using the same data from the Taro app)
const sampledigests = [
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
];

// State management
let alldigests = []; // Store all fetched digests
let currentdigests = []; // Currently displayed digests
let displayeddigestsCount = 0; // Track how many digests are currently displayed
const digests_PER_PAGE = 10; // K digests to load at a time (configurable)
let bookmarkeddigests = new Set();
let userFavorites = new Set(); // 新增：存储用户真实的收藏状态
let isLoading = false;
let searchQuery = '';
let hasMoredigests = true; // Track if there are more digests to load

// DOM elements
const digestsContainer = document.getElementById('digestsContainer');
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
    const savedBookmarks = localStorage.getItem('bookmarkeddigests');
    if (savedBookmarks) {
        bookmarkeddigests = new Set(JSON.parse(savedBookmarks));
    }

    // Check if user is logged in and load their recommendations
    if (window.AuthService && window.AuthService.isLoggedIn()) {
        // 先加载收藏状态，再加载推荐论文，确保收藏状态正确显示
        console.log('Loading user favorites first...');
        await loadUserFavorites();
        console.log('Loading user recommendations...');
        await loadUserRecommendations();
    } else {
        // Load default user recommendations with login suggestion
        await loadDefaultUserRecommendations();
        // Show login suggestion banner AFTER digests are rendered
        if (!window.AuthService || !window.AuthService.isLoggedIn()) {
            showLoginSuggestion();
        }
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
        const response = await fetch(`/api/digests/recommendations/${encodeURIComponent(username)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${window.AuthService.getToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const digests = await response.json();

        // Transform backend data to match frontend format
        const transformeddigests = digests.map(paper => ({
            id: paper.id,
            title: paper.title,
            authors: paper.authors ? paper.authors.split(', ') : [],
            abstract: paper.abstract || '',
            url: paper.url || '',
            publishDate: paper.submitted,
            thumbnail: 'Paper',
            viewed: paper.viewed || false,
            recommendationDate: paper.recommendation_date,
            blog_liked: paper.blog_liked ?? null, // true = liked, false = disliked, null = no feedback
        }));

        // Deduplicate digests by ID (keep the most recent recommendation)
        const paperMap = new Map();
        transformeddigests.forEach(paper => {
            if (!paperMap.has(paper.id) ||
                new Date(paper.recommendationDate) > new Date(paperMap.get(paper.id).recommendationDate)) {
                paperMap.set(paper.id, paper);
            }
        });
        alldigests = Array.from(paperMap.values());
        currentdigests = []; // Clear displayed digests
        displayeddigestsCount = 0;
        hasMoredigests = alldigests.length > 0;

        renderdigests();

        // 批量检查并同步当前论文的收藏状态
        await syncCurrentdigestsFavoriteStatus();
        
    } catch (error) {
        console.error('Error loading recommendations:', error);
        // Fallback to demo digests on error
        showErrorMessage('Failed to load recommendations. Showing sample digests.');
    } finally {
        if (currentdigests.length === 0) {
            console.log('No paper to display, loading default recommendations as fallback');
            await loadDefaultUserRecommendations();
            return; // loadDefaultUserRecommendations handles rendering
        }
        isLoading = false;
        hideLoading();
    }
}

async function loadDefaultUserRecommendations() {
    const defaultUsername = 'BlogBot@gmail.com'; // Default user

    isLoading = true;
    showLoading();

    try {
        const response = await fetch(`/api/digests/recommendations/${encodeURIComponent(defaultUsername)}?limit=10`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const digests = await response.json();

        const transformeddigests = digests.map(paper => ({
            id: paper.id,
            title: paper.title,
            authors: paper.authors ? paper.authors.split(', ') : [],
            abstract: paper.abstract || '',
            url: paper.url || '',
            publishDate: paper.submitted,
            thumbnail: 'Paper',
            viewed: paper.viewed || false,
            recommendationDate: paper.recommendation_date,
            blog_liked: paper.blog_liked ?? null, // true = liked, false = disliked, null = no feedback
        }));

        // Deduplicate digests by ID (keep the most recent recommendation)
        const paperMap = new Map();
        transformeddigests.forEach(paper => {
            if (!paperMap.has(paper.id) ||
                new Date(paper.recommendationDate) > new Date(paperMap.get(paper.id).recommendationDate)) {
                paperMap.set(paper.id, paper);
            }
        });
        alldigests = Array.from(paperMap.values());
        currentdigests = []; // Clear displayed digests
        displayeddigestsCount = 0;
        hasMoredigests = alldigests.length > 0;

        renderdigests();

    } catch (error) {
        console.error('Error loading default recommendations:', error);
        showErrorMessage('Failed to load recommendations. Showing sample digests.');
        await loadSampledigests();
    } finally {
        isLoading = false;
        hideLoading();
    }
}

function showLoginSuggestion() {
    // Check if banner already exists to prevent duplicates
    if (document.getElementById('loginSuggestionBanner')) {
        return;
    }

    // Add a login suggestion banner at the top of digests container
    const banner = document.createElement('div');
    banner.id = 'loginSuggestionBanner';
    banner.style.cssText = `
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 16px 24px;
        margin-bottom: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    `;
    banner.innerHTML = `
        <p style="margin: 0; font-size: 16px;">
            📚 You're viewing sample recommendations.
            <a href="login.html" style="color: #ffd700; font-weight: bold; text-decoration: underline;">Login</a>
            to see personalized paper recommendations tailored for you!
        </p>
    `;

    digestsContainer.insertBefore(banner, digestsContainer.firstChild);
}

function showLoginPrompt() {
    digestsContainer.innerHTML = `
        <div class="loading">
            <h2>Welcome to PaperIgnition</h2>
            <p>Please <a href="login.html" style="color: var(--accent-red);">login</a> to see your personalized paper recommendations.</p>
            <br>
            <p>Or view some <button onclick="loadSampledigests()" style="color: var(--accent-red); background: none; border: none; text-decoration: underline; cursor: pointer;">sample digests</button></p>
        </div>
    `;
}

async function loadSampledigests() {
    currentdigests = sampledigests;
    renderdigests();

    // 如果用户已登录，批量检查并同步当前论文的收藏状l态
    await syncCurrentdigestsFavoriteStatus();
}

async function searchdigestsAPI(query) {
    /**
     * Call the backend /find_similar/ API to search for digests
     */
    try {
        const response = await fetch('/api/find_similar/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                query: query,
                search_strategies: [['tf-idf', 0.8]],  // Format: [[strategy, threshold]]
                top_k: 5,
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const results = await response.json();
        console.log('Search API results:', results);

        // Transform API results to match frontend format
        return results.map(result => ({
            id: result.doc_id || result.id,
            title: result.metadata?.title || 'Untitled',
            authors: result.metadata?.authors || [],
            abstract: result.metadata?.abstract || '',
            url: result.metadata?.url || '',
            publishDate: result.metadata?.published_date || '',
            thumbnail: 'Paper',
            viewed: false,
            recommendationDate: null,
            relevanceScore: result.similarity_score || result.score
        }));
    } catch (error) {
        console.error('Error calling search API:', error);
        throw error;
    }
}

async function loaddigests(append = false) {
    // This function is now used primarily for search functionality
    if (!window.AuthService || !window.AuthService.isLoggedIn()) {
        await loadSampledigests();
        return;
    }

    // For logged-in users: use search API
    if (isLoading) return;

    isLoading = true;
    showLoading();
    console.log('Search input:', searchQuery);

    try {
        if (searchQuery && searchQuery.trim().length > 0) {
            // Call backend search API
            const searchResults = await searchdigestsAPI(searchQuery);
            alldigests = searchResults;
            currentdigests = []; // Clear displayed digests
            displayeddigestsCount = 0;
            hasMoredigests = alldigests.length > 0;
            console.log(`Search query: "${searchQuery}", digests found: ${alldigests.length}`);
            if (!alldigests || alldigests.length === 0) {
                console.log('No paper to display');
            }
        } else {
            // No search query - reload original recommendations
            console.log('No search query, reloading user recommendations');
            isLoading = false; // Reset loading to allow loadUserRecommendations to proceed
            await loadUserRecommendations();
            return; // loadUserRecommendations handles rendering and hasMoredigests
        }

        renderdigests();

    } catch (error) {
        console.error('Error in loaddigests:', error);
        showErrorMessage('Search failed');
    } finally {
        isLoading = false;
        hideLoading();
    }
}

function loadMoredigests() {
    const startIdx = displayeddigestsCount;
    const endIdx = Math.min(startIdx + digests_PER_PAGE, alldigests.length);

    // Get next batch of digests
    const newdigests = alldigests.slice(startIdx, endIdx);
    currentdigests = [...currentdigests, ...newdigests];
    displayeddigestsCount = endIdx;

    // Check if there are more digests to load
    hasMoredigests = displayeddigestsCount < alldigests.length;

    return newdigests;
}

function renderdigests(append = false) {
    if (!append) {
        digestsContainer.innerHTML = '';
        currentdigests = [];
        displayeddigestsCount = 0;
    }

    // Load next batch of digests
    const newdigests = loadMoredigests();

    // Add search results header (only on initial render)
    if (!append && searchQuery && searchQuery.trim().length > 0) {
        const resultsHeader = document.createElement('div');
        resultsHeader.className = 'search-results-header';
        resultsHeader.innerHTML = `
            <p>Showing <strong>${alldigests.length}</strong> results for: "<strong>${searchQuery}</strong>"</p>
        `;
        digestsContainer.appendChild(resultsHeader);
    }

    // Render new digests
    newdigests.forEach(paper => {
        const paperElement = createPaperCard(paper);
        digestsContainer.appendChild(paperElement);
    });

    // Handle empty states
    if (alldigests.length === 0 && searchQuery && searchQuery.trim().length > 0) {
        const noResultsDiv = document.createElement('div');
        noResultsDiv.className = 'loading';
        noResultsDiv.innerHTML = '<p>No digests found matching your search.</p>';
        digestsContainer.appendChild(noResultsDiv);
    } else if (alldigests.length === 0) {
        digestsContainer.innerHTML = '<div class="loading"><p>No digests found.</p></div>';
    } else if (!hasMoredigests && currentdigests.length > 0) {
        const noMoreDiv = document.createElement('div');
        noMoreDiv.className = 'no-more-digests';
        noMoreDiv.innerHTML = '<p>No more digests</p>';
        digestsContainer.appendChild(noMoreDiv);
    }
}

function createPaperCard(paper) {
    const card = document.createElement('article');
    card.className = 'paper-card';
    card.dataset.paperId = paper.id;

    const viewedIndicator = paper.viewed ? '<span class="viewed-indicator">👁️ Viewed</span>' : '<span class="unviewed-indicator">📄 New</span>';

    // Check if paper is liked/disliked/favorited (from paper data or localStorage)
    // For non-logged-in users, check localStorage first
    const isLoggedIn = window.AuthService && window.AuthService.isLoggedIn();
    let isLiked, isDisliked;

    if (!isLoggedIn) {
        const likeState = localStorage.getItem(`paper_${paper.id}_liked`);
        isLiked = likeState === 'true';
        isDisliked = likeState === 'false';
    } else {
        isLiked = paper.blog_liked === true;
        isDisliked = paper.blog_liked === false;
    }

    const isFavorited = bookmarkeddigests.has(paper.id);

    // Check if we're in search mode (only show favorite button in search)
    const isSearchMode = searchQuery && searchQuery.trim().length > 0;

    // Helper function to create button HTML
    const createButton = (className, isActive, title, svgPath, fillColor = 'none') => `
        <button class="action-btn ${className} ${isActive ? 'active' : ''}" data-action="${className.replace('-btn', '')}" title="${title}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="${fillColor}" stroke="currentColor" stroke-width="2">
                <path d="${svgPath}"/>
            </svg>
        </button>
    `;

    // SVG paths for buttons
    const likePath = "M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3";
    const dislikePath = "M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17";
    const favoritePath = "M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z";

    // Build action buttons based on mode
    const favoriteBtnHTML = createButton('favorite-btn', isFavorited, isFavorited ? 'Remove from favorites' : 'Add to favorites', favoritePath, isFavorited ? 'currentColor' : 'none');

    let actionButtons = '';
    if (isSearchMode) {
        // Search mode: only show favorite button
        actionButtons = favoriteBtnHTML;
    } else {
        // Explore mode: show all buttons (like, dislike, favorite)
        const likeBtnHTML = createButton('like-btn', isLiked, 'Like this paper', likePath);
        const dislikeBtnHTML = createButton('dislike-btn', isDisliked, 'Dislike this paper', dislikePath);
        actionButtons = likeBtnHTML + dislikeBtnHTML + favoriteBtnHTML;
    }

    card.innerHTML = `
        <div class="paper-content">
            <div class="paper-header">
                <h2 class="paper-title">${paper.title}</h2>
                <div class="paper-header-actions">
                    ${viewedIndicator}
                </div>
            </div>
            <p class="paper-authors">${Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors}</p>
            <p class="paper-abstract">${paper.abstract}</p>
            <div class="paper-meta">
                <span>Publish Time: ${paper.publishDate ? new Date(paper.publishDate).toLocaleDateString() : "Recent"}</span>
                <span>•</span>
                <span>Recommend Time: ${paper.recommendationDate ? new Date(paper.recommendationDate).toLocaleDateString() : "Recent"}</span>
                ${paper.url ? `<span>•</span><a href="${paper.url}" target="_blank" class="paper-link" onclick="event.stopPropagation()">Paper Link</a>` : ''}
            </div>
        </div>
        <div class="paper-actions">
            ${actionButtons}
        </div>
    `;

    // Add click handler for paper details
    card.addEventListener('click', (e) => {
        // Don't open details if clicking on action buttons
        if (e.target.closest('.action-btn') || e.target.closest('.paper-link')) {
            return;
        }
        showPaperDetail(paper);
    });

    // Add handlers for action buttons
    const likeBtn = card.querySelector('.like-btn');
    const dislikeBtn = card.querySelector('.dislike-btn');
    const favoriteBtn = card.querySelector('.favorite-btn');

    if (likeBtn) {
        likeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handlePaperAction(paper.id, 'like', likeBtn, dislikeBtn);
        });
    }

    if (dislikeBtn) {
        dislikeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handlePaperAction(paper.id, 'dislike', dislikeBtn, likeBtn);
        });
    }

    if (favoriteBtn) {
        favoriteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            handleFavoriteAction(paper.id, favoriteBtn);
        });
    }

    return card;
}

// Handle like/dislike actions
async function handlePaperAction(paperId, action, activeBtn, oppositeBtn) {
    const isLoggedIn = window.AuthService && window.AuthService.isLoggedIn();

    if (!isLoggedIn) {
        // For non-logged in users, use localStorage
        const currentLikeState = localStorage.getItem(`paper_${paperId}_liked`);
        const actionValue = action === 'like' ? 'true' : 'false';
        const newState = (currentLikeState === actionValue) ? null : actionValue;

        if (newState === null) {
            localStorage.removeItem(`paper_${paperId}_liked`);
            activeBtn.classList.remove('active');
        } else {
            localStorage.setItem(`paper_${paperId}_liked`, newState);
            activeBtn.classList.add('active');
            oppositeBtn.classList.remove('active');
        }
        return;
    }

    // For logged in users, call backend API
    try {
        const token = window.AuthService.getToken();
        if (!token) {
            throw new Error('No authentication token available');
        }

        const currentUser = window.AuthService.getCurrentUser();
        if (!currentUser || !currentUser.username) {
            throw new Error('Username not available');
        }
        const username = currentUser.username;

        // Determine new blog_liked value: true=like, false=dislike, null=neutral
        const currentState = activeBtn.classList.contains('active');
        const actionValue = action === 'like' ? true : false;
        const blogLiked = currentState ? null : actionValue;

        const response = await fetch(`/api/digests/recommendations/${encodeURIComponent(paperId)}/feedback`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                blog_liked: blogLiked
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }

        // Update UI
        if (blogLiked === null) {
            activeBtn.classList.remove('active');
        } else {
            activeBtn.classList.add('active');
            oppositeBtn.classList.remove('active');
        }

        // Update paper data in currentdigests
        const paper = currentdigests.find(p => p.id === paperId);
        if (paper) {
            paper.blog_liked = blogLiked;
        }

    } catch (error) {
        console.error('Error updating paper feedback:', error);
        showErrorMessage('Failed to update feedback: ' + error.message);
    }
}

// Handle favorite action
async function handleFavoriteAction(paperId, btn) {
    const isLoggedIn = window.AuthService && window.AuthService.isLoggedIn();

    if (!isLoggedIn) {
        // For non-logged in users, use localStorage
        if (bookmarkeddigests.has(paperId)) {
            bookmarkeddigests.delete(paperId);
            btn.classList.remove('active');
            btn.querySelector('svg').setAttribute('fill', 'none');
            btn.setAttribute('title', 'Add to favorites');
        } else {
            bookmarkeddigests.add(paperId);
            btn.classList.add('active');
            btn.querySelector('svg').setAttribute('fill', 'currentColor');
            btn.setAttribute('title', 'Remove from favorites');
        }

        // Save to localStorage
        localStorage.setItem('bookmarkeddigests', JSON.stringify([...bookmarkeddigests]));
        return;
    }

    // For logged in users, use toggleBookmark functionality
    // Find the paper data
    const paper = currentdigests.find(p => p.id === paperId);
    if (!paper) {
        console.error('Paper not found:', paperId);
        return;
    }

    const isCurrentlyFavorited = userFavorites.has(paperId);

    // Show loading state
    const originalHtml = btn.innerHTML;
    btn.disabled = true;
    btn.style.opacity = '0.6';
    btn.innerHTML = isCurrentlyFavorited ? 'Removing...' : 'Adding...';

    try {
        const token = window.AuthService.getToken();
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
            bookmarkeddigests.delete(paperId);

            // Restore original HTML first, then update UI
            btn.innerHTML = originalHtml;
            btn.classList.remove('active');
            const svg = btn.querySelector('svg');
            if (svg) svg.setAttribute('fill', 'none');
            btn.setAttribute('title', 'Add to favorites');

            showSuccessMessage('Removed from favorites');

        } else {
            // Add to favorites
            const authorsStr = Array.isArray(paper.authors) ? paper.authors.join(', ') : paper.authors;

            const cleanAbstract = (paper.abstract || '')
                .replace(/\r\n/g, '\n')
                .replace(/[""]/g, '"')
                .replace(/['']/g, "'")
                .replace(/…/g, '...')
                .trim();

            const favoriteData = {
                paper_id: String(paper.id).substring(0, 50),
                title: String(paper.title).substring(0, 255),
                authors: String(authorsStr).substring(0, 255),
                abstract: cleanAbstract
            };

            if (paper.url && /^https?:\/\//i.test(String(paper.url))) {
                favoriteData.url = String(paper.url).substring(0, 255);
            }

            const response = await fetch('/api/favorites/add', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(favoriteData)
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }

            // Update local state
            userFavorites.add(paperId);
            bookmarkeddigests.add(paperId);

            // Restore original HTML first, then update UI
            btn.innerHTML = originalHtml;
            btn.classList.add('active');
            const svg = btn.querySelector('svg');
            if (svg) svg.setAttribute('fill', 'currentColor');
            btn.setAttribute('title', 'Remove from favorites');

            showSuccessMessage('Added to favorites');
        }

    } catch (error) {
        console.error('Error toggling favorite:', error);
        showErrorMessage('Failed to update favorites: ' + error.message);
        // Restore original state
        btn.innerHTML = originalHtml;
    } finally {
        btn.disabled = false;
        btn.style.opacity = '1';
    }
}

async function toggleBookmark(paperId, event) {
    event.stopPropagation();
    
    const button = event.target;
    const isLoggedIn = window.AuthService && window.AuthService.isLoggedIn();
    
    if (!isLoggedIn) {
        // 未登录用户使用localStorage
    if (bookmarkeddigests.has(paperId)) {
        bookmarkeddigests.delete(paperId);
    } else {
        bookmarkeddigests.add(paperId);
    }
    
    // Save to localStorage
    localStorage.setItem('bookmarkeddigests', JSON.stringify([...bookmarkeddigests]));
    
    // Update UI
    const isBookmarked = bookmarkeddigests.has(paperId);
    button.className = `bookmark-btn ${isBookmarked ? 'bookmarked' : ''}`;
    button.textContent = isBookmarked ? '★ Saved' : '☆ Save';
        
        return;
    }
    
    // 以下是登录用户的API调用逻辑
    const isCurrentlyFavorited = userFavorites.has(paperId);
    
    // Find the paper data
    const paper = currentdigests.find(p => p.id === paperId);
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
            bookmarkeddigests.delete(paperId);
            
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
                        bookmarkeddigests.add(paperId);
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
            bookmarkeddigests.add(paperId);
            
            // Update UI
            button.className = 'bookmark-btn bookmarked';
            button.textContent = '★ Saved';
            
            showSuccessMessage('Added to favorites');
        }
        
        // Update localStorage for backward compatibility
        localStorage.setItem('bookmarkeddigests', JSON.stringify([...bookmarkeddigests]));
        
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
            bookmarkeddigests.clear();
            
            favorites.forEach(fav => {
                userFavorites.add(fav.paper_id);
                bookmarkeddigests.add(fav.paper_id);
            });
            
            // Update localStorage
            localStorage.setItem('bookmarkeddigests', JSON.stringify([...bookmarkeddigests]));
            
            console.log('Favorites loaded:', favorites.length, 'digests');
            console.log('User favorites updated:', [...userFavorites]);
            
            // Re-render digests to update bookmark states
            if (currentdigests.length > 0) {
                console.log('Re-rendering digests with updated favorite states');
                renderdigests();
            }
        } else {
            console.error('Failed to load favorites:', response.status, response.statusText);
        }
    } catch (error) {
        console.error('Error loading user favorites:', error);
    }
}

async function syncCurrentdigestsFavoriteStatus() {
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
    loaddigests(false);
}

function handleScroll() {
    if (isLoading) return;

    // Don't trigger infinite scroll for non-logged-in users (they see default BlogBot digests)
    if (!window.AuthService || !window.AuthService.isLoggedIn()) {
        return;
    }

    // Don't load more if we've reached the end
    if (!hasMoredigests) {
        return;
    }

    const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
    if (scrollTop + clientHeight >= scrollHeight - 5) {
        // Load next K digests
        if (hasMoredigests) {
            renderdigests(true);
        }
    }
}

async function showPaperDetail(paper) {
    if (!paper) return;

    // Mark paper as viewed if user is logged in
    if (window.AuthService && window.AuthService.isLoggedIn()) {
        try {
            const token = window.AuthService.getToken();
            // Call API in background, don't wait for response
            fetch(`/api/digests/${encodeURIComponent(paper.id)}/mark-viewed`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            }).catch(err => console.log('Failed to mark paper as viewed:', err));
        } catch (error) {
            console.log('Error marking paper as viewed:', error);
        }
    }

    // Store paper information in sessionStorage for the detail page
    sessionStorage.setItem(`paper_${paper.id}`, JSON.stringify(paper));

    // Get current username for recommended papers
    const currentUser = window.AuthService?.getCurrentUser();
    const username = currentUser?.username;

    // Open paper detail page in new tab
    // If username exists, it's a recommended paper (blog_content)
    // If no username, it's a searched paper (paper_content)
    const url = username
        ? `paper.html?id=${paper.id}&username=${encodeURIComponent(username)}`
        : `paper.html?id=${paper.id}`;
    window.open(url, '_blank');
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
class digestservice {
    static async getdigests(page = 1, search = '') {
        try {
            // In a real implementation, this would make an HTTP request
            // const response = await fetch(`${API_BASE_URL}/digests?page=${page}&search=${search}`);
            // return await response.json();
            
            // For demo, return sample data
            return {
                digests: sampledigests,
                hasMore: false,
                total: sampledigests.length
            };
        } catch (error) {
            console.error('Error fetching digests:', error);
            throw error;
        }
    }
    
    static async getPaperDetail(paperId) {
        try {
            // const response = await fetch(`${API_BASE_URL}/digests/${paperId}`);
            // return await response.json();
            
            return sampledigests.find(p => p.id === paperId);
        } catch (error) {
            console.error('Error fetching paper detail:', error);
            throw error;
        }
    }
    
    static async getPaperContent(paperId) {
        try {
            // const response = await fetch(`${API_BASE_URL}/digests/${paperId}/content`);
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
        
        // Reload digests when auth state changes
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
