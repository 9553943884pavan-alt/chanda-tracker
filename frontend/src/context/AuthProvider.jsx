import { useMemo, useState } from 'react'
import { AuthContext } from './AuthContext.js'

const TOKEN_KEY = 'chanda_token'
const ROLE_KEY = 'chanda_role'

function decodeToken(token) {
  try {
    const payload = token.split('.')[1]
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      window
        .atob(normalized.padEnd(normalized.length + ((4 - (normalized.length % 4)) % 4), '='))
        .split('')
        .map((character) => `%${`00${character.charCodeAt(0).toString(16)}`.slice(-2)}`)
        .join(''),
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

function isValidToken(token) {
  const payload = decodeToken(token)
  return Boolean(payload?.exp && payload.exp * 1000 > Date.now() && payload.role)
}

export function AuthProvider({ children }) {
  const initialToken = localStorage.getItem(TOKEN_KEY)
  const [token, setToken] = useState(initialToken && isValidToken(initialToken) ? initialToken : null)
  const [role, setRole] = useState(initialToken && isValidToken(initialToken) ? decodeToken(initialToken).role : null)

  const value = useMemo(() => ({
    token,
    role,
    isAuthenticated: Boolean(token && isValidToken(token)),
    login(nextToken) {
      const payload = decodeToken(nextToken)
      if (!payload?.role || !payload?.exp || payload.exp * 1000 <= Date.now()) {
        throw new Error('Received an invalid login token')
      }
      localStorage.setItem(TOKEN_KEY, nextToken)
      localStorage.setItem(ROLE_KEY, payload.role)
      setToken(nextToken)
      setRole(payload.role)
      return payload
    },
    logout() {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(ROLE_KEY)
      setToken(null)
      setRole(null)
    },
  }), [role, token])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
