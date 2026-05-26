import api from './index'

export const login = (username, password) =>
  api.post('/auth/login/', { username, password })

export const register = (username, password, password2) =>
  api.post('/auth/register/', { username, password, password2 })

export const getMe = () => api.get('/auth/me/')
