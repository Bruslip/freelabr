// Configuração da API - detecta automaticamente o ambiente
const API_CONFIG = {
    // Em produção: usa o backend do Render
    // Em desenvolvimento: usa localhost
    BASE_URL: window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
        ? 'http://localhost:8000'
        : 'https://freelabr-backend.onrender.com'
};

// Função auxiliar para fazer requisições à API
async function apiRequest(endpoint, options = {}) {
    const url = `${API_CONFIG.BASE_URL}${endpoint}`;

    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };

    // Adiciona token se existir
    const token = getToken();
    if (token) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }

    const finalOptions = { ...defaultOptions, ...options };

    // Merge headers se options.headers existir
    if (options.headers) {
        finalOptions.headers = { ...defaultOptions.headers, ...options.headers };
    }

    const response = await fetch(url, finalOptions);

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Erro na requisição' }));
        throw new Error(error.detail || 'Erro na requisição');
    }

    return response.json();
}

// Função de login
async function login(email, password) {
    try {
        // FormData para enviar como application/x-www-form-urlencoded
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);

        const data = await apiRequest('/api/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });

        // Salva o token
        localStorage.setItem('access_token', data.access_token);

        return { success: true, data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// Função de registro
async function register(email, password, fullName) {
    try {
        const data = await apiRequest('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({
                email,
                password,
                full_name: fullName,
            }),
        });

        // Após registro bem-sucedido, faz login automaticamente
        const loginResult = await login(email, password);

        return loginResult;
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// Função para obter dados do usuário
async function getCurrentUser() {
    try {
        const data = await apiRequest('/api/auth/me');
        return { success: true, data };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

// Função de logout
function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login.html';
}

// Função para obter o token
function getToken() {
    return localStorage.getItem('access_token');
}

// Função para verificar se está autenticado
function isAuthenticated() {
    return !!getToken();
}

// Função para redirecionar se não estiver autenticado
function redirectIfNotAuthenticated() {
    if (!isAuthenticated()) {
        window.location.href = '/login.html';
    }
}

// Função para redirecionar se já estiver autenticado
function redirectIfAuthenticated() {
    if (isAuthenticated()) {
        window.location.href = '/index.html';
    }
}

// Função para exibir nome do usuário
async function displayUserName() {
    const userNameElement = document.getElementById('userName');
    if (!userNameElement) return;

    const result = await getCurrentUser();
    if (result.success) {
        userNameElement.textContent = result.data.full_name;
    } else {
        // Se falhar ao obter usuário, faz logout
        logout();
    }
}

// Função para calcular valores
async function calculateValues(data) {
    try {
        const result = await apiRequest('/api/calculator/calculate', {
            method: 'POST',
            body: JSON.stringify(data),
        });
        return { success: true, data: result };
    } catch (error) {
        return { success: false, error: error.message };
    }
}