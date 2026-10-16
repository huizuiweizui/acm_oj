import api from './index'

export const login = (username, password) =>
  api.post('/auth/login/', { username, password })

export const register = (username, password, password2) =>
  api.post('/auth/register/', { username, password, password2 })

export const getMe = () => api.get('/auth/me/')

// 显式带上 access token：调用方随后会清空 localStorage，拦截器届时已读不到
export const logout = (refresh, access) =>
  api.post('/auth/logout/', { refresh }, { headers: { Authorization: `Bearer ${access}` } })
