import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

// 请求拦截：自动附加 JWT token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：token 过期时尝试刷新（单例 Promise 防止并发 401 的竞态）
let _refreshPromise = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        // 多个并发请求同时收到 401 时，只执行一次 refresh
        if (!_refreshPromise) {
          _refreshPromise = axios.post('/api/auth/refresh/', { refresh })
            .finally(() => { _refreshPromise = null })
        }
        try {
          const { data } = await _refreshPromise
          localStorage.setItem('access_token', data.access)
          original.headers.Authorization = `Bearer ${data.access}`
          return api(original)
        } catch {
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      }
    }
    return Promise.reject(error)
  },
)

export default api
