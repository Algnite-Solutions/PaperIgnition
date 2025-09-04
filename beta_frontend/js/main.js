// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';

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

function initializeApp() {
    // Load bookmarks from localStorage
    const savedBookmarks = localStorage.getItem('bookmarkedPapers');
    if (savedBookmarks) {
        bookmarkedPapers = new Set(JSON.parse(savedBookmarks));
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

function loadPapers(append = false) {
    if (isLoading) return;
    
    isLoading = true;
    showLoading();
    
    // Simulate API call delay
    setTimeout(() => {
        const filteredPapers = searchQuery 
            ? samplePapers.filter(paper => 
                paper.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                paper.abstract.toLowerCase().includes(searchQuery.toLowerCase()) ||
                paper.authors.some(author => author.toLowerCase().includes(searchQuery.toLowerCase())) ||
                paper.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
            )
            : samplePapers;
        
        if (append) {
            currentPapers = [...currentPapers, ...filteredPapers];
        } else {
            currentPapers = filteredPapers;
        }
        
        renderPapers();
        isLoading = false;
        hideLoading();
    }, 500);
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
    
    card.innerHTML = `
        <div class="paper-thumbnail">
            ${paper.thumbnail}
        </div>
        <div class="paper-content">
            <h2 class="paper-title">${paper.title}</h2>
            <p class="paper-authors">${paper.authors.join(', ')}</p>
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

function toggleBookmark(paperId, event) {
    event.stopPropagation();
    
    if (bookmarkedPapers.has(paperId)) {
        bookmarkedPapers.delete(paperId);
    } else {
        bookmarkedPapers.add(paperId);
    }
    
    // Save to localStorage
    localStorage.setItem('bookmarkedPapers', JSON.stringify([...bookmarkedPapers]));
    
    // Update UI
    const button = event.target;
    const isBookmarked = bookmarkedPapers.has(paperId);
    button.className = `bookmark-btn ${isBookmarked ? 'bookmarked' : ''}`;
    button.textContent = isBookmarked ? '★ Saved' : '☆ Save';
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
    const paper = samplePapers.find(p => p.id === paperId);
    if (!paper) return;
    
    // Navigate to paper detail page
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

// Export for potential use in other modules
window.PaperService = PaperService;