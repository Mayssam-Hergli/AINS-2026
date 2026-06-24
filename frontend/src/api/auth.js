import { request } from './client'

export const authApi = {
  register: (email, password, fullName) =>
    request('/auth/register', {
      method: 'POST',
      // backend users.full_name is NOT NULL — derive a sensible default from
      // the email local-part when the signup form doesn't collect a name.
      body: { email, password, full_name: (fullName && fullName.trim()) || email.split('@')[0] },
    }),

  login: async (email, password) => {
    // OAuth2PasswordRequestForm expects form-encoded data
    const form = new URLSearchParams({ username: email, password })
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form.toString(),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }))
      const e = new Error(err.detail || 'Login failed')
      e.status = res.status
      throw e
    }
    return res.json()
  },

  me: (token) => request('/auth/me', { token }),
}
