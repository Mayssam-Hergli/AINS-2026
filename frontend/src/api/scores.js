import { request } from './client'

export const scoresApi = {
  compute: (token, profileId) =>
    request(`/scores/compute/${profileId}`, { method: 'POST', token }),

  get: (token, profileId) =>
    request(`/scores/${profileId}`, { token }),
}
