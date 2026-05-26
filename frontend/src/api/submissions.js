import api from './index'

export const getSubmissions = (params) => api.get('/submissions/', { params })
export const getSubmission = (id) => api.get(`/submissions/${id}/`)
