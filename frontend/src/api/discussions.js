import api from './index'

export const getDiscussions = (params) => api.get('/discussions/', { params })
export const getDiscussion = (id) => api.get(`/discussions/${id}/`)
export const createDiscussion = (data) => api.post('/discussions/create/', data)
export const createReply = (id, content) =>
  api.post(`/discussions/${id}/replies/`, { content })
