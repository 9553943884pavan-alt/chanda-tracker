import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'

const initialForm = {
  full_name: '',
  email: '',
  roll_no: '',
  role: 'giver',
  year: '',
  branch: '',
  gender: '',
}

function getErrorMessage(error) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ')
  return detail || 'Unable to complete signup. Check your details and try again.'
}

export default function Signup() {
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [otp, setOtp] = useState('')
  const [password, setPassword] = useState('')
  const [step, setStep] = useState('details')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function requestOtp(event) {
    event.preventDefault()
    setError('')
    setMessage('')
    setLoading(true)
    try {
      await api.post('/auth/signup', {
        ...form,
        year: form.role === 'admin' || !form.year ? null : Number(form.year),
        branch: form.branch || null,
        gender: form.gender || null,
      })
      setStep('verify')
      setMessage('Verification code sent. Check your institute email.')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function verifyAccount(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/verify-otp', { email: form.email, otp, password })
      navigate('/login', { replace: true, state: { message: 'Account created. You can now sign in.' } })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-5 py-10">
      <section className="w-full max-w-2xl rounded-[2rem] border border-stone-200/80 bg-[#fffdf8]/90 p-7 shadow-[0_24px_80px_rgba(56,73,64,0.12)] backdrop-blur sm:p-10">
        <div className="mb-9 flex items-start justify-between gap-5">
          <div>
            <Link to="/login" className="font-display text-2xl font-semibold text-stone-950">chanda<span className="text-teal-700">.</span></Link>
            <p className="mt-8 text-xs font-bold uppercase tracking-[0.24em] text-teal-700">{step === 'details' ? 'Join the circle' : 'Almost there'}</p>
            <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight text-stone-950">{step === 'details' ? 'Create your account.' : 'Verify your email.'}</h1>
          </div>
          <span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-bold text-teal-800">{step === 'details' ? '1 / 2' : '2 / 2'}</span>
        </div>
        {step === 'details' ? (
          <form className="grid gap-5 sm:grid-cols-2" onSubmit={requestOtp}>
            <label className="field-label sm:col-span-2">Full name<input className="field-input" name="full_name" value={form.full_name} onChange={updateField} required /></label>
            <label className="field-label">Institute email<input className="field-input" name="email" type="email" value={form.email} onChange={updateField} placeholder="you@iiita.ac.in" required /></label>
            <label className="field-label">Roll number<input className="field-input" name="roll_no" value={form.roll_no} onChange={updateField} required /></label>
            <label className="field-label">Role<select className="field-input" name="role" value={form.role} onChange={updateField}><option value="giver">Giver</option><option value="collector">Collector</option><option value="admin">Admin</option></select></label>
            <label className="field-label">Year<select className="field-input" name="year" value={form.role === 'admin' ? '' : form.year} onChange={updateField} disabled={form.role === 'admin'}><option value="">Select year</option>{[1, 2, 3, 4].map((year) => <option key={year} value={year}>{year}</option>)}</select></label>
            <label className="field-label">Branch<select className="field-input" name="branch" value={form.branch} onChange={updateField}><option value="">Select branch</option><option value="IT">IT</option><option value="ECE">ECE</option></select></label>
            <label className="field-label">Gender<select className="field-input" name="gender" value={form.gender} onChange={updateField}><option value="">Select gender</option><option value="M">M</option><option value="F">F</option></select></label>
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 sm:col-span-2">{error}</p>}
            <button className="primary-button sm:col-span-2" type="submit" disabled={loading}>{loading ? 'Sending code...' : 'Send verification code'}</button>
          </form>
        ) : (
          <form className="space-y-5" onSubmit={verifyAccount}>
            <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm leading-6 text-teal-900">A six-digit code was sent to <strong>{form.email}</strong>.</p>
            <label className="field-label">Verification code<input className="field-input tracking-[0.35em]" inputMode="numeric" maxLength="6" value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, ''))} required /></label>
            <label className="field-label">
              Create password
              <input className="field-input" type="password" minLength="8" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Minimum 8 characters (letters & numbers)" required />
              <span className="mt-1 text-xs text-stone-500 font-normal">Must be at least 8 characters with a mix of letters and numbers/symbols.</span>
            </label>

            {message && <p className="text-sm text-teal-800">{message}</p>}
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Creating account...' : 'Verify and create account'}</button>
          </form>
        )}
        <p className="mt-7 text-center text-sm text-stone-500">Already registered? <Link className="font-bold text-teal-800 hover:text-teal-950" to="/login">Sign in</Link></p>
      </section>
    </main>
  )
}
