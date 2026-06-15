import api from './index'

// 团队列表 / 创建
export const getTeams = () => api.get('/teams/')
export const createTeam = (data) => api.post('/teams/', data)

// 团队详情 / 编辑
export const getTeam = (id) => api.get(`/teams/${id}/`)
export const updateTeam = (id, data) => api.patch(`/teams/${id}/`, data)
export const resetInviteCode = (id) => api.post(`/teams/${id}/reset-code/`)

// 预览 & 加入 & 退出
export const previewTeam = (code) => api.get('/teams/preview/', { params: { code } })
export const joinTeam = (data) => api.post('/teams/join/', data)
export const leaveTeam = (id) => api.delete(`/teams/${id}/leave/`)

// 成员管理
export const getMembers = (id) => api.get(`/teams/${id}/members/`)
export const updateMember = (teamId, userId, data) => api.patch(`/teams/${teamId}/members/${userId}/`, data)
export const removeMember = (teamId, userId) => api.delete(`/teams/${teamId}/members/${userId}/`)

// 申请审核
export const getRequests = (id, status = 'pending') => api.get(`/teams/${id}/requests/`, { params: { status } })
export const approveRequest = (teamId, reqId) => api.post(`/teams/${teamId}/requests/${reqId}/approve/`)
export const rejectRequest = (teamId, reqId, reason = '') => api.post(`/teams/${teamId}/requests/${reqId}/reject/`, { reason })
export const batchApprove = (teamId, ids) => api.post(`/teams/${teamId}/requests/batch-approve/`, { ids })

// 学生：我的申请状态
export const getMyRequests = () => api.get('/my-requests/')

// 比赛创建权限
export const setContestPerm = (userId, can) =>
  api.patch(`/users/${userId}/contest-perm/`, { can_create_contest: can })

// 搜索 / 直接添加学生
export const searchStudent = (teamId, q) =>
  api.get(`/teams/${teamId}/search-student/`, { params: { q } })
export const addStudent = (teamId, data) =>
  api.post(`/teams/${teamId}/add-student/`, data)

// Excel 导入模板 & 导入
export const importTemplate = (teamId) =>
  api.get(`/teams/${teamId}/import-template/`, { responseType: 'blob' })
export const importStudents = (teamId, formData) =>
  api.post(`/teams/${teamId}/import-students/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

// Dashboard
export const getTeamDashboard = (teamId) => api.get(`/teams/${teamId}/dashboard/`)
export const exportDashboard = (teamId) =>
  api.get(`/teams/${teamId}/dashboard/export/`, { responseType: 'blob' })

// 学生详情
export const getStudentDetail = (teamId, userId) =>
  api.get(`/teams/${teamId}/students/${userId}/`)

// 公告
export const getAnnouncements = (teamId) => api.get(`/teams/${teamId}/announcements/`)
export const createAnnouncement = (teamId, data) => api.post(`/teams/${teamId}/announcements/`, data)
export const updateAnnouncement = (teamId, aid, data) => api.patch(`/teams/${teamId}/announcements/${aid}/`, data)
export const deleteAnnouncement = (teamId, aid) => api.delete(`/teams/${teamId}/announcements/${aid}/`)

// 作业
export const getAssignments = (teamId) => api.get(`/teams/${teamId}/assignments/`)
export const createAssignment = (teamId, data) => api.post(`/teams/${teamId}/assignments/`, data)
export const updateAssignment = (teamId, aid, data) => api.patch(`/teams/${teamId}/assignments/${aid}/`, data)
export const deleteAssignment = (teamId, aid) => api.delete(`/teams/${teamId}/assignments/${aid}/`)

// 团队比赛
export const getTeamContests = (teamId) => api.get(`/teams/${teamId}/contests/`)
export const createTeamContest = (teamId, data) => api.post(`/teams/${teamId}/contests/`, data)
