import api from './index'

export const getContests = (params) => api.get('/contests/', { params })
export const getContest = (id) => api.get(`/contests/${id}/`)
export const registerContest = (id) => api.post(`/contests/${id}/register/`)
export const getContestRank = (id) => api.get(`/contests/${id}/rank/`)
export const createContest = (data) => api.post('/contests/create/', data)
export const getProblemPool = (params) => api.get('/contests/problem-pool/', { params })
export const finalizeRating = (id) => api.post(`/contests/${id}/finalize-rating/`)
export const getMyContestProgress = (id) => api.get(`/contests/${id}/my-progress/`)
export const virtualStart = (id) => api.post(`/contests/${id}/virtual-start/`)
export const virtualStatus = (id) => api.get(`/contests/${id}/virtual-status/`)
