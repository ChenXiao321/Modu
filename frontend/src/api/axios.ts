import axios from 'axios'
import { API_BASE_URL } from '../config'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor
api.interceptors.request.use((config) => {
  // TODO: Add JWT token when auth is implemented
  config.headers['X-Tenant-ID'] = '1'
  return config
})

// Response interceptor: snake_case -> camelCase conversion is handled by FastAPI alias_generator
// but we keep this hook for future extension
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg = error.response?.data?.error?.message || '请求失败'
    return Promise.reject(new Error(msg))
  }
)

export default api
