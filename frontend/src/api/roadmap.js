import { request } from './client'

export const roadmapApi = {
  // MS3 — generate a roadmap from the computed scores (RAG over the KB)
  generate: (token, profileId) =>
    request(`/roadmap/generate/${profileId}`, { method: 'POST', token }),

  // cached roadmap (steps grouped by time_horizon, KB-referenced resources)
  get: (token, profileId) =>
    request(`/roadmap/${profileId}`, { token }),

  // contextual assistant chat anchored on the profile's diagnostic + scores
  chat: (token, { sessionId, profileId, component, message }) =>
    request('/roadmap/chat', {
      method: 'POST',
      body: {
        session_id: sessionId,
        profile_id: profileId,
        clicked_component: component,
        new_message: message,
      },
      token,
    }),
    evaluateProgress: (token, { profileId, latestUpdate }) =>
    request('/roadmap/evaluate-progress', {
      method: 'POST',
      body: {
        profile_id: profileId,
        latest_update: latestUpdate,
      },
      token,
    }),
    askLLM: (token, { profileId, question }) =>
    request('/roadmap/ask-llm', {
      method: 'POST',
      body: {
        profile_id: profileId,
        question: question,
      },
      token,
    }),
}
