import api from './index'

// 客观题题库（教师 / 管理员）
export const getQuestions = (params) => api.get('/questions/', { params })
export const getQuestion = (id) => api.get(`/questions/${id}/`)
export const createQuestion = (data) => api.post('/questions/', data)
export const updateQuestion = (id, data) => api.patch(`/questions/${id}/`, data)
export const deleteQuestion = (id) => api.delete(`/questions/${id}/`)
export const checkQuestion = (id, answer) => api.post(`/questions/${id}/check/`, { answer })
