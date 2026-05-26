import api from './index'

export const getUser = (id) => api.get(`/users/${id}/`)
export const getUserStats = (id) => api.get(`/users/${id}/stats/`)
export const getRank = (params) => api.get('/rank/', { params })
