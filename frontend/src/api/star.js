import api from './index'

// 大模型生成要跑"生成-校验-修复"最多 3 轮，单次请求可能超过默认的 15 秒
const LONG = { timeout: 180000 }
// 排序题会在评测机上真的运行代码
const RUN = { timeout: 60000 }

// ── 学生端 ──────────────────────────────────────────────
export const getStarMe = () => api.get('/star/me/')
export const submitSurvey = (answers) => api.post('/star/survey/', { answers })
export const answerDialogue = (answer, via) => api.post('/star/dialogue/', { answer, via }, LONG)
export const getMyTasks = () => api.get('/star/tasks/')
export const getMyTask = (id) => api.get(`/star/tasks/${id}/`)
export const getHint = (id, step, level) => api.post(`/star/tasks/${id}/hint/`, { step, level })
export const submitAttempt = (id, payload) => api.post(`/star/tasks/${id}/attempt/`, payload, RUN)
export const chatWithStar = (payload) => api.post('/star/chat/', payload, { timeout: 60000 })

// ── 教师端 ──────────────────────────────────────────────
export const getLearners = () => api.get('/star/teacher/learners/')
export const getLearner = (uid) => api.get(`/star/teacher/learners/${uid}/`)
export const updateLearner = (uid, data) => api.patch(`/star/teacher/learners/${uid}/`, data)
export const regenerateProfile = (uid) => api.post(`/star/teacher/learners/${uid}/profile/`, {}, LONG)
export const createTask = (uid, material, mode) =>
  api.post(`/star/teacher/learners/${uid}/tasks/`, { material, mode }, LONG)
export const getLearnerReport = (uid, audience) =>
  api.post(`/star/teacher/learners/${uid}/report/`, { audience }, LONG)
export const getMaterials = () => api.get('/star/teacher/materials/')
// 批量布置：一组任务 × 一组学生，用默认版本（payload: { learners, materials, approve }）
export const getAssignData = () => api.get('/star/teacher/assign/')
export const assignTasks = (payload) => api.post('/star/teacher/assign/', payload, LONG)
export const getTaskForReview = (id) => api.get(`/star/teacher/tasks/${id}/`)
export const updateTaskContent = (id, content) => api.patch(`/star/teacher/tasks/${id}/`, { content })
export const deleteTask = (id) => api.delete(`/star/teacher/tasks/${id}/`)
export const approveTask = (id) => api.post(`/star/teacher/tasks/${id}/approve/`)
export const regenerateTask = (id, mode) => api.post(`/star/teacher/tasks/${id}/regenerate/`, { mode }, LONG)
