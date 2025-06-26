/**
 * Authentication Service - Frontend
 * Handles JWT tokens, session validation, and API calls
 */

class AuthService {
    constructor() {
        this.apiBase = '/api';
        this.token = localStorage.getItem('authToken') || localStorage.getItem('access_token');
        this.user = this.getStoredUser();
        this.refreshTimer = null;
        
        // Don't auto-check session on initialization to avoid redirects
        // Only check session when explicitly called
    }

    /**
     * Login user
     */
    async login(email, password) {
        try {
            const response = await fetch(`${this.apiBase}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Erro no login');
            }

            const data = await response.json();
            
            // Store token and user data
            this.token = data.access_token;
            this.user = data.user;
            
            localStorage.setItem('access_token', this.token);
            localStorage.setItem('user', JSON.stringify(this.user));
            
            // Remove old token name if exists
            localStorage.removeItem('authToken');
            
            // Setup token refresh
            this.setupTokenRefresh();
            
            return data;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    /**
     * Logout user
     */
    async logout() {
        try {
            // Call logout API
            await fetch(`${this.apiBase}/auth/logout`, {
                method: 'POST',
                headers: this.getHeaders()
            });
        } catch (error) {
            console.warn('Logout API call failed:', error);
        } finally {
            // Clear local data regardless of API call result
            this.clearAuthData();
            this.redirectToLogin();
        }
    }

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.token && !!this.user;
    }

    /**
     * Get current user
     */
    getCurrentUser() {
        return this.user;
    }

    /**
     * Get auth headers for API calls
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };
        
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }
        
        return headers;
    }

    /**
     * Make authenticated API call
     */
    async apiCall(url, options = {}) {
        const config = {
            ...options,
            headers: {
                ...this.getHeaders(),
                ...(options.headers || {})
            }
        };

        try {
            const response = await fetch(url, config);
            
            // Handle unauthorized
            if (response.status === 401) {
                this.handleUnauthorized();
                throw new Error('Sessão expirada');
            }
            
            // Handle other errors
            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API call error:', error);
            throw error;
        }
    }

    /**
     * Check session validity
     */
    async checkSession() {
        if (!this.isAuthenticated()) {
            return false;
        }

        try {
            const userData = await this.apiCall(`${this.apiBase}/auth/me`);
            this.user = userData;
            localStorage.setItem('user', JSON.stringify(this.user));
            return true;
        } catch (error) {
            console.warn('Session check failed:', error);
            // Don't clear auth data here - let the caller decide what to do
            return false;
        }
    }

    /**
     * Refresh token
     */
    async refreshToken() {
        try {
            const response = await fetch(`${this.apiBase}/auth/refresh`, {
                method: 'POST',
                headers: this.getHeaders()
            });

            if (!response.ok) {
                throw new Error('Token refresh failed');
            }

            const data = await response.json();
            this.token = data.access_token;
            localStorage.setItem('access_token', this.token);
            
            return data;
        } catch (error) {
            console.error('Token refresh error:', error);
            this.handleUnauthorized();
            throw error;
        }
    }

    /**
     * Setup automatic token refresh
     */
    setupTokenRefresh() {
        // Clear existing timer
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
        }

        // Refresh token every 25 minutes (tokens usually expire in 30 minutes)
        this.refreshTimer = setInterval(() => {
            this.refreshToken().catch(() => {
                console.warn('Auto token refresh failed');
            });
        }, 25 * 60 * 1000);
    }

    /**
     * Handle unauthorized response
     */
    handleUnauthorized() {
        this.clearAuthData();
        this.showNotification('Sessão expirada. Faça login novamente.', 'warning');
        setTimeout(() => {
            this.redirectToLogin();
        }, 2000);
    }

    /**
     * Clear authentication data
     */
    clearAuthData() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('access_token');
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
        localStorage.removeItem('refresh_token');
        
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }

    /**
     * Redirect to login page
     */
    redirectToLogin() {
        // Don't redirect if already on login page
        if (window.location.pathname !== '/login') {
            window.location.href = '/login';
        }
    }

    /**
     * Get stored user data
     */
    getStoredUser() {
        try {
            const userData = localStorage.getItem('user');
            return userData ? JSON.parse(userData) : null;
        } catch (error) {
            console.warn('Failed to parse stored user data:', error);
            return null;
        }
    }

    /**
     * Show notification (if available)
     */
    showNotification(message, type = 'info') {
        // Try to use global notification function if available
        if (typeof window.showNotification === 'function') {
            window.showNotification(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    /**
     * Require authentication - call this on protected pages
     * Returns true if authenticated, false otherwise
     */
    requireAuth() {
        if (!this.isAuthenticated()) {
            return false;
        }
        return true;
    }

    /**
     * Require admin role
     */
    requireAdmin() {
        if (!this.requireAuth()) {
            return false;
        }

        if (this.user?.tipo_usuario !== 'admin') {
            this.showNotification('Acesso negado. Privilégios de administrador necessários.', 'error');
            return false;
        }

        return true;
    }
}

// Create global auth service instance
window.authService = new AuthService();

// Global helper functions
window.showNotification = function(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.notification');
    existingNotifications.forEach(n => n.remove());

    // Create notification
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <div class="notification-content">
            <i class="fas fa-${getNotificationIcon(type)}"></i>
            <span>${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;

    document.body.appendChild(notification);

    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
};

function getNotificationIcon(type) {
    const icons = {
        'success': 'check-circle',
        'error': 'exclamation-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Auto-check authentication on page load
document.addEventListener('DOMContentLoaded', async function() {
    // Skip auth check on login page
    if (window.location.pathname === '/login') {
        return;
    }
    
    // Check if user has basic authentication
    if (!authService.requireAuth()) {
        // No token found, redirect to login
        authService.redirectToLogin();
        return;
    }
    
    // Token exists, verify if it's valid (non-blocking)
    try {
        const isValidSession = await authService.checkSession();
        
        if (!isValidSession) {
            // Session is invalid, clear data and redirect
            authService.clearAuthData();
            authService.redirectToLogin();
            return;
        }
        
        // Session is valid, update UI
        updateUserInfoInUI();
        
    } catch (error) {
        console.warn('Session validation failed:', error);
        authService.clearAuthData();
        authService.redirectToLogin();
        return;
    }
});

function updateUserInfoInUI() {
    // Update user info in UI if available
    const userNameElements = document.querySelectorAll('.user-name');
    const userAvatarElements = document.querySelectorAll('.user-avatar');
    
    if (authService.user) {
        userNameElements.forEach(el => {
            el.textContent = authService.user.nome || authService.user.email;
        });
        
        userAvatarElements.forEach(el => {
            if (el.tagName === 'IMG') {
                el.src = authService.user.avatar || `https://ui-avatars.com/api/?name=${encodeURIComponent(authService.user.nome || authService.user.email)}&background=6c5ce7&color=fff`;
            } else {
                el.textContent = (authService.user.nome || authService.user.email).substring(0, 2).toUpperCase();
            }
        });
    }
}
