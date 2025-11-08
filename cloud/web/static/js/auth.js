/**
 * AuthManager - JWT authentication helper for Visant Dashboard
 *
 * Handles:
 * - Login/signup API calls
 * - Token storage in sessionStorage (secure against XSS)
 * - Auth headers for API requests
 * - Logout and session management
 */

class AuthManager {
    constructor() {
        // sessionStorage keys
        this.TOKEN_KEY = 'visant_access_token';
        this.USER_KEY = 'visant_user';

        // API base URL (can be overridden for production)
        this.API_URL = window.location.origin;
    }

    /**
     * Login user with email and password
     * @param {string} email - User email
     * @param {string} password - User password
     * @returns {Promise<Object>} User data with organization info
     */
    async login(email, password) {
        try {
            const response = await fetch(`${this.API_URL}/v1/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login failed');
            }

            const data = await response.json();

            // Store tokens and user data in sessionStorage
            sessionStorage.setItem(this.TOKEN_KEY, data.access_token);
            sessionStorage.setItem(this.USER_KEY, JSON.stringify(data.user));

            return data;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    /**
     * Sign up new user (organization auto-created)
     * @param {string} email - User email
     * @param {string} password - User password
     * @returns {Promise<Object>} User data
     */
    async signup(email, password) {
        try {
            const response = await fetch(`${this.API_URL}/v1/auth/signup`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email,
                    password
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Signup failed');
            }

            const data = await response.json();

            // Auto-login: store tokens and user data
            sessionStorage.setItem(this.TOKEN_KEY, data.access_token);
            sessionStorage.setItem(this.USER_KEY, JSON.stringify(data.user));

            return data;
        } catch (error) {
            console.error('Signup error:', error);
            throw error;
        }
    }

    /**
     * Get current access token
     * @returns {string|null} Access token or null if not authenticated
     */
    getToken() {
        return sessionStorage.getItem(this.TOKEN_KEY);
    }

    /**
     * Get current user data
     * @returns {Object|null} User object or null if not authenticated
     */
    getUser() {
        const userData = sessionStorage.getItem(this.USER_KEY);
        return userData ? JSON.parse(userData) : null;
    }

    /**
     * Get authorization headers for API requests
     * @returns {Object} Headers object with Authorization and Content-Type
     */
    getAuthHeaders() {
        const token = this.getToken();
        if (!token) {
            throw new Error('Not authenticated');
        }

        return {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        };
    }

    /**
     * Logout user and clear session
     */
    logout() {
        sessionStorage.clear();
        window.location.href = '/login';
    }

    /**
     * Check if user is authenticated
     * @returns {boolean} True if user has valid token
     */
    isAuthenticated() {
        return !!this.getToken();
    }

    /**
     * Verify current session is valid
     * Calls /v1/auth/me to check if token is still valid
     * @returns {Promise<Object>} User data if valid
     */
    async verifySession() {
        try {
            const response = await fetch(`${this.API_URL}/v1/auth/me`, {
                method: 'GET',
                headers: this.getAuthHeaders()
            });

            if (!response.ok) {
                // Token invalid or expired
                this.logout();
                throw new Error('Session expired');
            }

            const data = await response.json();

            // Update stored user data (organization info available in response if needed)
            sessionStorage.setItem(this.USER_KEY, JSON.stringify({
                id: data.id,
                email: data.email,
                role: data.role
            }));

            return data;
        } catch (error) {
            console.error('Session verification error:', error);
            throw error;
        }
    }

    /**
     * Require authentication - redirect to login if not authenticated
     * Use this on protected pages
     */
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/login';
            return false;
        }
        return true;
    }
}

// Create global auth instance
const auth = new AuthManager();
