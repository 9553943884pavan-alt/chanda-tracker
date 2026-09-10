import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'

function getErrorMessage(error) {
  const detail = error.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ')
  return detail || 'Unable to reset password. Check your details and try again.'
}

function validatePasswordRules(password) {
  return password.length >= 8 && /[a-zA-Z]/.test(password) && /[^a-zA-Z]/.test(password)
}

export default function ForgotPassword() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [step, setStep] = useState('email')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function requestReset(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.post('/auth/forgot-password', { email })
      setStep('reset')
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  async function resetPassword(event) {
    event.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    if (!validatePasswordRules(newPassword)) {
      setError('Password must be at least 8 characters with a mix of letters and numbers/symbols')
      return
    }
    setLoading(true)
    try {
      await api.post('/auth/reset-password', {
        email,
        otp,
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      navigate('/login', { replace: true, state: { message: 'Password reset successfully. Sign in with your new password.' } })
    } catch (requestError) {
      setError(getErrorMessage(requestError))
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center px-5 py-10">
      <section className="w-full max-w-md rounded-[2rem] border border-stone-200/80 bg-[#fffdf8]/90 p-7 shadow-[0_24px_80px_rgba(56,73,64,0.12)] backdrop-blur sm:p-10">
        <div className="mb-9">
          <Link to="/login" className="font-display text-2xl font-semibold text-stone-950">chanda<span className="text-teal-700">.</span></Link>
          <p className="mt-8 text-xs font-bold uppercase tracking-[0.24em] text-teal-700">{step === 'email' ? 'Trouble signing in' : 'Almost there'}</p>
          <h1 className="mt-3 font-display text-4xl font-semibold tracking-tight text-stone-950">{step === 'email' ? 'Reset your password.' : 'Verify and reset.'}</h1>
          <p className="mt-3 leading-7 text-stone-500">{step === 'email' ? 'Enter your registered institute email and we will send you a reset code.' : 'Enter the code sent to your email and choose a new password.'}</p>
        </div>

        {step === 'email' ? (
          <form className="space-y-5" onSubmit={requestReset}>
            <label className="field-label">Institute email<input className="field-input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@iiita.ac.in" required /></label>
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Sending code...' : 'Send reset code'}</button>
          </form>
        ) : (
          <form className="space-y-5" onSubmit={resetPassword}>
            <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm leading-6 text-teal-900">A six-digit reset code was sent to <strong>{email}</strong>.</p>
            <label className="field-label">Reset code<input className="field-input tracking-[0.35em]" inputMode="numeric" maxLength="6" value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, ''))} required /></label>
            <label className="field-label">
              New password
              <input className="field-input" type="password" minLength="8" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} placeholder="Minimum 8 characters (letters & numbers)" required />
              <span className="mt-1 text-xs text-stone-500 font-normal">Must be at least 8 characters with a mix of letters and numbers/symbols.</span>
            </label>
            <label className="field-label">Confirm new password<input className="field-input" type="password" minLength="8" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} placeholder="Re-enter your new password" required /></label>
            {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
            <button className="primary-button" type="submit" disabled={loading}>{loading ? 'Resetting...' : 'Reset password'}</button>
          </form>
        )}

        <p className="mt-7 text-center text-sm text-stone-500">Remembered it? <Link className="font-bold text-teal-800 hover:text-teal-950" to="/login">Back to sign in</Link></p>
      </section>
    </main>
  )
}
