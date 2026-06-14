import api from './index'

export const getUser = (id) => api.get(`/users/${id}/`)
export const getUserStats = (id) => api.get(`/users/${id}/stats/`)
export const getRank = (params) => api.get('/rank/', { params })
export const updateMe = (data) => api.patch('/auth/me/', data)
export const changePassword = (oldPassword, newPassword) =>
  api.post('/auth/password/', { old_password: oldPassword, new_password: newPassword })
