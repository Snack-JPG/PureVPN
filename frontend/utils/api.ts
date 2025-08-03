import axios from 'axios'

// Get the API base URL from environment variable or fallback to localhost for development
const getApiBaseUrl = (): string => {
  // For client-side (browser), use NEXT_PUBLIC_API_URL
  if (typeof window !== 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  }
  // For server-side, use API_URL or fallback
  return process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
}

// Create axios instance with base configuration
const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  timeout: 30000, // 30 seconds timeout
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add request interceptor for debugging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// API methods
export const api = {
  // Health check
  health: () => apiClient.get('/health'),
  
  // VPN Status
  getStatus: () => apiClient.get('/status'),
  
  // Deployment Status
  getDeploymentStatus: () => apiClient.get('/deployment-status'),
  
  // VPN Operations
  joinVPN: (username: string) => apiClient.post(`/join/${username}`),
  
  disconnectVPN: (username: string) => apiClient.post(`/disconnect/${username}`),
  
  // Configuration
  getUserConfig: (username: string) => apiClient.get(`/config/${username}`),
  
  // QR Code
  getQRCode: (username: string) => apiClient.get(`/qr/${username}`, {
    responseType: 'blob'
  }),
  
  // Server management
  getServerStatus: () => apiClient.get('/server-status'),
  
  testConnection: () => apiClient.get('/test-connection'),
}

// Export the base URL for use in components if needed
export const getBaseApiUrl = getApiBaseUrl

// Export types
export interface VPNStatus {
  status: string
  message?: string
  progress?: number
  server_ip?: string
  connection_type?: string
  estimated_cost?: string
  active_servers?: number
  total_peers?: number
  available_slots?: number
}

export interface ConfigData {
  username: string
  config: string
  filename: string
}

export interface DeploymentStatus {
  status: 'pending' | 'processing' | 'completed' | 'error'
  message: string
  progress?: number
  server_ip?: string
  connection_type?: string
}

export default api
