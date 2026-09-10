import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../context/useAuth'

function getErrorMessage(error) {
  return error.response?.data?.detail || 'Unable to sign in. Check your details and try again.'
}

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [message] = useState(location.state?.message || '')

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', form)
      const payload = login(data.access_token)
      const destination = {
        collector: '/collector-dashboard',
        giver: '/giver-dashboard',
        admin: '/admin-dashboard',
      }[payload.role]
      if (!destination) throw new Error('Unknown account role')
      navigate(destination, { replace: true })
    } catch (requestError) {
      setError(requestError.message === 'Unknown account role' ? requestError.message : getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-5 py-10">
      <section className="w-full max-w-md rounded-[2rem] border border-stone-200/80 bg-[#fffdf8]/90 p-7 shadow-[0_24px_80px_rgba(56,73,64,0.12)] backdrop-blur sm:p-10">
        <div className="mb-10">
          <p className="font-display text-2xl font-semibold text-stone-950">chanda<span className="text-teal-700">.</span></p>
          <p className="mt-8 text-xs font-bold uppercase tracking-[0.24em] text-teal-700">Welcome back</p>
          <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight text-stone-950">Sign in to continue.</h1>
          <p className="mt-3 leading-7 text-stone-500">Keep every contribution moving with clarity.</p>
        </div>
        <form className="space-y-5" onSubmit={handleSubmit}>
          <label className="field-label">Institute email<input className="field-input" name="email" type="email" value={form.email} onChange={updateField} placeholder="you@iiita.ac.in" required /></label>
          <label className="field-label">Password<input className="field-input" name="password" type="password" value={form.password} onChange={updateField} required /></label>
          {message && <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-teal-800">{message}</p>}
          {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
          <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Signing in...' : 'Sign in'}</button>
        </form>
        <p className="mt-3 text-center text-sm text-stone-500"><Link className="font-bold text-teal-800 hover:text-teal-950" to="/forgot-password">Forgot password?</Link></p>
        <p className="mt-4 text-center text-sm text-stone-500">New to Chanda? <Link className="font-bold text-teal-800 hover:text-teal-950" to="/signup">Create an account</Link></p>
      </section>
    </main>
  )
}
