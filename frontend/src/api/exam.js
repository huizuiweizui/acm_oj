import api from './index'

// 学生答题流
export const enterExam = (aid) => api.post(`/assignments/${aid}/enter/`)
export const getPaper = (aid) => api.get(`/assignments/${aid}/paper/`)
export const submitAnswer = (aid, question_id, answer) =>
  api.post(`/assignments/${aid}/answer/`, { question_id, answer })
export const submitExam = (aid) => api.post(`/assignments/${aid}/submit/`)
export const reportFocusLoss = (aid) => api.post(`/assignments/${aid}/focus-loss/`)

// 成绩单（教师）
export const getGradebook = (aid) => api.get(`/assignments/${aid}/gradebook/`)
export const exportGradebook = (aid) =>
  api.get(`/assignments/${aid}/gradebook/export/`, { responseType: 'blob' })
export const getStudentResult = (aid, uid) =>
  api.get(`/assignments/${aid}/students/${uid}/result/`)

// 代码查重（教师）
export const getPlagiarism = (aid, threshold) =>
  api.get(`/assignments/${aid}/plagiarism/`, { params: { threshold } })
export const getPlagiarismPair = (aid, a, b) =>
  api.get(`/assignments/${aid}/plagiarism/pair/`, { params: { a, b } })
