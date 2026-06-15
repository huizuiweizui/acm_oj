import api from './index'

export const getProblems = (params) => api.get('/problems/', { params })
export const getProblem = (id) => api.get(`/problems/${id}/`)
export const submitCode = (id, language, code, contest_id, assignment_id) =>
  api.post(`/problems/${id}/submit/`, { language, code, contest_id, assignment_id })
export const runCode = (id, language, code, input) =>
  api.post(`/problems/${id}/run/`, { language, code, input })

// 题解 / 提交分布 / 每日一题
export const getSolutions = (id) => api.get(`/problems/${id}/solutions/`)
export const postSolution = (id, data) => api.post(`/problems/${id}/solutions/`, data)
export const deleteSolution = (sid) => api.delete(`/solutions/${sid}/`)
export const getDistribution = (id, metric) => api.get(`/problems/${id}/distribution/`, { params: { metric } })
export const getDailyProblem = () => api.get('/daily-problem/')
