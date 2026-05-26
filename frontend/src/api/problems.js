import api from './index'

export const getProblems = (params) => api.get('/problems/', { params })
export const getProblem = (id) => api.get(`/problems/${id}/`)
export const submitCode = (id, language, code, contest_id) =>
  api.post(`/problems/${id}/submit/`, { language, code, contest_id })
