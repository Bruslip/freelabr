// Configuração da API
const API_URL = 'http://localhost:8000';  // Mude para sua URL de produção

// Gerenciamento de Token
const TokenManager = {
    get() {
        return localStorage.getItem('freelabr_token');
    },
    
    set(token) {
        localStorage.setItem('freelabr_token', token);
    },
    
    remove() {
        localStorage.removeItem('freelabr_token');
        localStorage.removeItem('freelabr_user');
    },
    
    getUser() {
        const userStr = localStorage.getItem('freelabr_user');
        return userStr ? JSON.parse(userStr) : null;
    },
    
    setUser(user) {
        localStorage.setItem('freelabr_user', JSON.stringify(user));
    }
};

// Classe de Autenticação
class Auth {
    constructor() {
        this.token = TokenManager.get();
        this.user = TokenManager.getUser();
    }
    
    isAuthenticated() {
        return !!this.token;
    }
    
    async register(fullName, email, password) {
        try {
            const response = await fetch(`${API_URL}/api/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    full_name: fullName,
                    email: email,
                    password: password
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Erro ao registrar');
            }
            
            const data = await response.json();
            
            // Salva token e usuário
            TokenManager.set(data.access_token);
            TokenManager.setUser(data.user);
            
            this.token = data.access_token;
            this.user = data.user;
            
            return data;
        } catch (error) {
            console.error('Erro no registro:', error);
            throw error;
        }
    }
    
    async login(email, password) {
        try {
            const response = await fetch(`${API_URL}/api/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Erro ao fazer login');
            }
            
            const data = await response.json();
            
            // Salva token e usuário
            TokenManager.set(data.access_token);
            TokenManager.setUser(data.user);
            
            this.token = data.access_token;
            this.user = data.user;
            
            return data;
        } catch (error) {
            console.error('Erro no login:', error);
            throw error;
        }
    }
    
    async getMe() {
        try {
            const response = await fetch(`${API_URL}/api/auth/me`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });
            
            if (!response.ok) {
                throw new Error('Token inválido');
            }
            
            const user = await response.json();
            TokenManager.setUser(user);
            this.user = user;
            
            return user;
        } catch (error) {
            console.error('Erro ao verificar token:', error);
            this.logout();
            throw error;
        }
    }
    
    logout() {
        TokenManager.remove();
        this.token = null;
        this.user = null;
        window.location.href = '/login.html';
    }
    
    requireAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/login.html';
            return false;
        }
        return true;
    }
    
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    }
}

// Instância global
const auth = new Auth();

// Exportar para uso em outros scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { Auth, auth, TokenManager, API_URL };
}
