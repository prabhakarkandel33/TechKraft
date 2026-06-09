import client from './client'

export const getCandidates = (filters = {}) => {
  // strip out empty values so we don't send ?status=&skill= 
  const params = Object.fromEntries(
    Object.entries(filters).filter(([_, v]) => v !== '' && v !== null && v !== undefined)
  )
  return client.get('/candidates', { params })
}

export const getCandidate = (id) =>
  client.get(`/candidates/${id}`)

export const submitScore = (id, data) =>
  client.post(`/candidates/${id}/scores`, data)

export const triggerSummary = (id) =>
  client.post(`/candidates/${id}/summary`)

export const updateNotes = (id, internal_notes) =>
  client.patch(`/candidates/${id}/notes`, { internal_notes })