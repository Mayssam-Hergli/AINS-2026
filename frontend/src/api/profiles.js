import { request } from './client'

export const profilesApi = {
  list: (token) =>
    request('/profiles', { token }),

  create: (token, name) =>
    request('/profiles', { method: 'POST', body: { name }, token }),

  get: (token, profileId) =>
    request(`/profiles/${profileId}`, { token }),

  setAnswers: (token, profileId, answers) =>
    request(`/profiles/${profileId}/answers`, {
      method: 'PATCH',
      body: { diagnostic_answers: answers },
      token,
    }),
}
