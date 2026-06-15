import api from './index'

// 题单 / 训练计划
export const getProblemLists = (params) => api.get('/problem-lists/', { params })
export const getProblemList = (id) => api.get(`/problem-lists/${id}/`)
export const createProblemList = (data) => api.post('/problem-lists/', data)
export const updateProblemList = (id, data) => api.patch(`/problem-lists/${id}/`, data)
export const deleteProblemList = (id) => api.delete(`/problem-lists/${id}/`)
export const addToProblemList = (id, problem_id) => api.post(`/problem-lists/${id}/add/`, { problem_id })
